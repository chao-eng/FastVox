import asyncio
import time
import logging
from typing import Dict, Optional, Set
from dataclasses import dataclass
from app.core.worker_pool import InferenceTask, WorkerPool
from config.settings import get_settings

logger = logging.getLogger("FastVox")
settings = get_settings()

@dataclass
class SlotInfo:
    slot_id: int
    request_id: Optional[str] = None
    acquired_at: float = 0.0
    status: str = "IDLE" # IDLE, BUSY, ERROR
    last_size: int = 0   # 最后一次推理产生的实际字节数

class SlotManager:
    """
    管理 Slot 分配、排队与超时熔断 (Watchdog)
    
    使用 asyncio.Semaphore 限制物理并发 (SLOT_COUNT)
    """
    
    SLOT_TTL = 120 # 秒，单个 Slot 推理最大时长 (增加到 120s 以适应长假和 CPU 推理)
    
    def __init__(self, worker_pool: WorkerPool):
        self._worker_pool = worker_pool
        self._slot_count = settings.slot_count
        # 基于信号量的排队机制
        self._semaphore = asyncio.Semaphore(self._slot_count)
        # slot_id -> SlotInfo
        self._slots: Dict[int, SlotInfo] = {
            i: SlotInfo(slot_id=i) for i in range(self._slot_count)
        }
        # 记录空闲 slot 集合
        self._free_slots: Set[int] = set(range(self._slot_count))
        # 任务完成标识 (用于协作式等待)
        self._events: Dict[int, asyncio.Event] = {
            i: asyncio.Event() for i in range(self._slot_count)
        }
        
    async def acquire(self, request_id: str) -> int:
        """获取空闲 Slot，无空闲时排队 await"""
        logger.debug(f"Request {request_id} queuing for slot...")
        await self._semaphore.acquire()
        
        # 选出一个空闲 slot_id
        slot_id = self._free_slots.pop()
        
        slot = self._slots[slot_id]
        slot.request_id = request_id
        slot.acquired_at = time.time()
        slot.status = "BUSY"
        slot.last_size = 0 # 重置 size
        
        # 重置同步事件
        self._events[slot_id].clear()
        
        logger.info(f"Slot {slot_id} assigned to request {request_id}")
        return slot_id

    def reset_event(self, slot_id: int):
        """重置 Slot 事件状态，用于流式分片推理"""
        if slot_id in self._events:
            self._events[slot_id].clear()
            if slot_id in self._slots:
                self._slots[slot_id].last_size = 0
            logger.debug(f"Slot {slot_id} event reset for next segment")

    def release(self, slot_id: int):
        """释放 Slot 并唤醒等待队列"""
        if slot_id not in self._slots:
            return
            
        slot = self._slots[slot_id]
        if slot.status == "IDLE":
            return
            
        request_id = slot.request_id
        slot.request_id = None
        slot.status = "IDLE"
        slot.acquired_at = 0.0
        slot.last_size = 0
        
        self._free_slots.add(slot_id)
        self._semaphore.release()
        
        logger.info(f"Slot {slot_id} released from request {request_id}")

    async def submit_task(self, slot_id: int, task: InferenceTask):
        """将任务发放给 Worker"""
        # 这里由 SlotManager 充当任务分发中专，保证任务与 slot_id 绑定
        task.slot_id = slot_id
        self._worker_pool.submit_task(task)

    def mark_ready(self, slot_id: int, size: int = 0):
        """UDS Server 收到 Ready 信令后调用"""
        if slot_id in self._events:
            if slot_id in self._slots:
                self._slots[slot_id].last_size = size
            self._events[slot_id].set()

    def get_last_size(self, slot_id: int) -> int:
        """获取 Slot 中最后一次产生的数据长度"""
        return self._slots[slot_id].last_size if slot_id in self._slots else 0

    async def wait_for_ready(self, slot_id: int, timeout: float = 30.0):
        """等待推理完成事件"""
        try:
            await asyncio.wait_for(self._events[slot_id].wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Slot {slot_id} timed out waiting for ready signal")
            return False

    async def watchdog(self):
        """后台协程: 检查超时 Slot 并强制释放 (熔断)"""
        logger.info("Slot Watchdog started")
        while True:
            await asyncio.sleep(5)
            now = time.time()
            for slot_id, slot in self._slots.items():
                if slot.status == "BUSY" and (now - slot.acquired_at) > self.SLOT_TTL:
                    logger.error(f"Watchdog: Slot {slot_id} (Req: {slot.request_id}) leaked or timed out. Force releasing.")
                    # 强制触发 Event 避免前端挂死
                    self._events[slot_id].set() 
                    self.release(slot_id)

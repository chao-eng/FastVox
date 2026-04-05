import os
import signal
import logging
from dataclasses import dataclass
from multiprocessing import Process, Queue, set_start_method
from typing import List, Dict, Optional
from app.core.platform_compat import platform
from config.settings import get_settings

logger = logging.getLogger("FastVox")
settings = get_settings()

@dataclass
class InferenceTask:
    """TTS 推理任务数据结构"""
    task_id: str
    slot_id: int
    text: str
    prompt_audio_path: Optional[str] = None
    prompt_text: Optional[str] = None
    prompt_audio_samples: Optional[bytes] = None # 新增：支持直接传递 PCM 字节作为前文 Prompt
    speed: float = 1.0

def worker_main(
    worker_id: int,
    shm_name: str,
    uds_gateway_addr: str,
    model_dir: str,
    task_queue: Queue,
    num_threads: int,
    num_steps: int
):
    """Worker 子进程入口点"""
    # 重新在子进程内导入以避免序列化问题
    import os
    import signal
    from app.core.shm_manager import SHMManager
    from app.core.uds_protocol import UDSClient, SignalStatus
    from app.inference.tts_engine import TTSEngine

    logger.info(f"Worker-{worker_id} (PID: {os.getpid()}) starting...")
    
    # 1. 附加共享内存
    shm = SHMManager()
    shm.shm_name = shm_name # 继承主进程分配的名字
    shm.attach()
    
    # 2. 连接 UDS Gateway
    uds = UDSClient(uds_gateway_addr)
    
    # 3. 初始化推理引擎
    engine = TTSEngine(model_dir, num_threads, num_steps)
    engine.warmup()
    
    # 4. 主循环监视任务队列
    try:
        while True:
            # 阻塞式接收任务
            task: InferenceTask = task_queue.get()
            if task is None: # 表示终止信号
                break
                
            slot_id = task.slot_id
            
            # 发送正在写入状态
            uds.send_signal(slot_id, 0, 0, SignalStatus.WRITING)
            
            try:
                logger.info(f"Worker-{worker_id} picked up task {task.task_id} (Slot: {slot_id})")
                # 执行推理 (同步阻塞)
                pcm_data, sample_rate = engine.synthesize(
                    text=task.text,
                    speed=task.speed,
                    prompt_audio=task.prompt_audio_path,
                    prompt_text=task.prompt_text,
                    prompt_samples=task.prompt_audio_samples # 传递上一段的音频语境
                )
                
                # 将 PCM 写入共享内存 Slot
                shm.write_to_slot(slot_id, pcm_data)
                logger.debug(f"Worker-{worker_id} wrote {len(pcm_data)} bytes to Slot-{slot_id}")
                
                # 发送就绪信令 (offset=0, size=pcm_data_len, status=READY)
                uds.send_signal(slot_id, 0, len(pcm_data), SignalStatus.READY)
                logger.info(f"Worker-{worker_id} signaled READY for Task-{task.task_id}")
                
            except Exception as e:
                logger.error(f"Worker-{worker_id} error processing task {task.task_id}: {e}")
                uds.send_signal(slot_id, 0, 0, SignalStatus.ERROR)

    finally:
        uds.close()
        logger.info(f"Worker-{worker_id} terminating...")

class WorkerPool:
    """管理推理工作进程生命周期"""
    
    def __init__(self):
        self._processes: Dict[int, Process] = {}
        self._task_queue = Queue()
        self.num_workers = settings.num_workers

    def start(self):
        """启动所有 Worker"""
        # 设置启动方式 (macOS/Windows=spawn, Linux=forkserver)
        method = platform.process_start_method
        try:
            set_start_method(method, force=True)
        except RuntimeError:
            pass # 已经设置过

        for i in range(self.num_workers):
            self.spawn_worker(i)

    def spawn_worker(self, worker_id: int):
        """生成独立 Worker 进程"""
        args = (
            worker_id,
            settings.shm_name,
            settings.uds_gateway_addr,
            settings.model_dir,
            self._task_queue,
            settings.intra_op_threads,
            settings.zipvoice_num_steps
        )
        p = Process(target=worker_main, args=args, name=f"FastVox-Worker-{worker_id}")
        p.daemon = True # 随主进程一同退出
        p.start()
        self._processes[worker_id] = p
        logger.info(f"Spawned Worker-{worker_id} (PID: {p.pid})")

    def submit_task(self, task: InferenceTask):
        """向进程池提交任务"""
        self._task_queue.put(task)

    def stop(self):
        """温和停止所有 Worker"""
        for _ in range(len(self._processes)):
            self._task_queue.put(None) # 告知 worker 退出
        
        for i, p in self._processes.items():
            p.join(timeout=3)
            if p.is_alive():
                p.terminate()
            logger.info(f"Worker-{i} stopped")
        
        self._processes.clear()

    def health_check(self) -> Dict:
        """返回 Worker 状态摘要"""
        stats = {}
        for i, p in self._processes.items():
            stats[i] = "alive" if p.is_alive() else "dead"
        return stats

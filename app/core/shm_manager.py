import logging
from multiprocessing import shared_memory
from typing import Optional, Dict
from app.core.platform_compat import platform
from config.settings import get_settings

logger = logging.getLogger("FastVox")
settings = get_settings()

class SHMManager:
    """
    共享内存管理 (Ring Buffer 模式)
    
    物理结构: [Slot 0 (2MB)][Slot 1 (2MB)]...[Slot N (2MB)]
    总大小: SLOT_COUNT * SLOT_SIZE
    """
    
    def __init__(self):
        self.shm_name = settings.shm_name
        self.slot_count = settings.slot_count
        self.slot_size = settings.slot_size_mb * 1024 * 1024 # 2MB
        self.total_size = self.slot_count * self.slot_size
        self.shm: Optional[shared_memory.SharedMemory] = None

    def create(self):
        """主进程调用: 清理旧内存并创建新块"""
        platform.cleanup_stale_shm()
        try:
            # 尝试先清理以防意外残留
            try:
                old_shm = shared_memory.SharedMemory(name=self.shm_name)
                old_shm.close()
                old_shm.unlink()
                logger.info(f"Cleaned up stale SHM before creation: {self.shm_name}")
            except FileNotFoundError:
                pass

            self.shm = shared_memory.SharedMemory(
                name=self.shm_name, 
                create=True, 
                size=self.total_size
            )
            logger.info(f"Created SHM '{self.shm_name}' (Total: {self.total_size / 1024 / 1024:.1f}MB)")
        except Exception as e:
            logger.error(f"Failed to create SHM: {e}")
            raise

    def attach(self):
        """Worker 进程调用: 附加到现有内存"""
        try:
            self.shm = shared_memory.SharedMemory(name=self.shm_name, create=False)
            logger.info(f"Attached to SHM '{self.shm_name}'")
        except Exception as e:
            logger.error(f"Worker failed to attach to SHM: {e}")
            raise

    def get_slot_view(self, slot_id: int) -> memoryview:
        """获取指定 Slot 的内存视图 (零拷贝)"""
        if not 0 <= slot_id < self.slot_count:
            raise ValueError(f"Invalid slot_id: {slot_id}")
        
        offset = slot_id * self.slot_size
        return self.shm.buf[offset : offset + self.slot_size]

    def write_to_slot(self, slot_id: int, data: bytes, offset_in_slot: int = 0):
        """写入数据到 Slot"""
        view = self.get_slot_view(slot_id)
        size = len(data)
        if offset_in_slot + size > self.slot_size:
            raise ValueError(f"Data too large for slot_id {slot_id}: {size} bytes at offset {offset_in_slot}")
        
        view[offset_in_slot : offset_in_slot + size] = data

    def read_from_slot(self, slot_id: int, offset_in_slot: int, size: int) -> bytes:
        """从 Slot 读取数据"""
        view = self.get_slot_view(slot_id)
        if offset_in_slot + size > self.slot_size:
            raise ValueError(f"Read range out of bounds for slot_id {slot_id}")
        
        return bytes(view[offset_in_slot : offset_in_slot + size])

    def destroy(self):
        """释放并清理"""
        if self.shm:
            try:
                name = self.shm.name
                self.shm.close()
                self.shm.unlink()
                logger.info(f"Destroyed SHM '{name}'")
            except Exception as e:
                logger.warning(f"Error while destroying SHM: {e}")

# 全局单例管理器
shm_manager = SHMManager()

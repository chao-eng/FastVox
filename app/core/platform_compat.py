import os
import sys
import glob
import logging
from typing import List, Optional
from multiprocessing import cpu_count

logger = logging.getLogger("FastVox")

class PlatformConfig:
    """抽象平台差异 (macOS, Linux, Windows)"""

    def __init__(self):
        self.platform = sys.platform
        
        # 共享内存名前缀
        self.shm_prefix = "fastvox_"
        
        # UDS 路径
        if self.platform == "darwin":
            self.uds_dir = "/tmp/fastvox/"
            self.process_start_method = "spawn"
            self.recommended_workers = 2
        elif self.platform == "win32":
            # Windows 的 UDS 目前支持 10 1809+，可以使用 local 临时目录
            self.uds_dir = os.path.join(os.environ.get("TEMP", r"C:\data\fastvox"), "fastvox")
            self.process_start_method = "spawn"
            self.recommended_workers = min(cpu_count() or 2, 4)
        else: # Linux
            self.uds_dir = "/run/fastvox/"
            self.process_start_method = "forkserver"
            self.recommended_workers = min(cpu_count() or 2, 4)

    def ensure_uds_dir(self):
        """确保 UDS 目录存在并有权限"""
        if not os.path.exists(self.uds_dir):
            try:
                os.makedirs(self.uds_dir, mode=0o755, exist_ok=True)
                # Windows 上 os.chmod 可能不完全生效，但在 Unix 是必须的
                if self.platform != "win32":
                    os.chmod(self.uds_dir, 0o755)
            except Exception as e:
                logger.error(f"Failed to create UDS directory {self.uds_dir}: {e}")

    def cleanup_stale_shm(self):
        """清理过期的共享内存残留"""
        if self.platform == "linux":
            # Linux 直接删除 /dev/shm 下的残留文件
            pattern = "/dev/shm/fastvox_*"
            for f in glob.glob(pattern):
                try:
                    os.unlink(f)
                    logger.info(f"Cleaned up stale SHM: {f}")
                except Exception as e:
                    logger.warning(f"Could not unlink SHM file {f}: {e}")
        elif self.platform in ("darwin", "win32"):
            # macOS 和 Windows 需借助 multiprocessing.shared_memory.SharedMemory 尝试 attach 并 unlink
            from multiprocessing import shared_memory
            # 我们假定名字为我们的 main shm 名字，尝试附加并销毁
            # TODO: 获取实际名字，暂时以 shm_manager 中定义为准
            pass

    def get_uds_path(self, name: str) -> str:
        """获取特定 worker 的 UDS 路径"""
        # 注意: macOS UDS 路径长度限制 104 字节
        path = os.path.join(self.uds_dir, f"{name}.sock")
        if self.platform == "win32":
            # Windows 10+ AF_UNIX 路径需要处理或映射，保持原样即可
            pass
        return path

# 全局单例
platform = PlatformConfig()
platform.ensure_uds_dir()

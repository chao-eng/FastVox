import struct
import socket
import logging
import asyncio
import os
from enum import IntEnum
from typing import Callable, Optional
from app.core.platform_compat import platform

logger = logging.getLogger("FastVox")

# 信令帧格式 (16 字节): slot_id (I), offset (I), size (I), status (I)
SIGNAL_FORMAT = 'IIII'
SIGNAL_SIZE = struct.calcsize(SIGNAL_FORMAT)

class SignalStatus(IntEnum):
    IDLE = 0
    WRITING = 1
    READY = 2       # 数据就绪
    ERROR = 3       # 推理发生错误
    HEARTBEAT = 4   # Worker 心跳
    COMPLETE = 5    # 整句推理完成

class UDSServer:
    """主进程端 - 监听子进程信令 (Gateway Side)"""
    
    def __init__(self, uds_path: str):
        self.uds_path = uds_path
        self.sock: Optional[socket.socket] = None
        self.on_signal: Optional[Callable[[int, int, int, int], None]] = None

    def start(self):
        """同步初始化 Socket，随后注册到 asyncio 并进行读"""
        if os.path.exists(self.uds_path):
            try:
                os.unlink(self.uds_path)
            except Exception as e:
                logger.error(f"Failed to unlink old UDS socket: {e}")

        # 注意: Windows 10+ 实际上也支持 AF_UNIX
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.sock.bind(self.uds_path)
            # 在 Linux 下可能需要 chmod
            if platform.platform != "win32":
                os.chmod(self.uds_path, 0o777)
            self.sock.setblocking(False)
            
            logger.info(f"UDSServer listening on {self.uds_path}")
            
            # 这里的读由外部启动的协程负责
            return self.sock
        except Exception as e:
            logger.error(f"Failed to start UDSServer: {e}")
            raise

    def stop(self):
        """停止并清理"""
        if self.sock:
            self.sock.close()
            if os.path.exists(self.uds_path):
                try:
                    os.unlink(self.uds_path)
                except:
                    pass
            logger.info("UDSServer stopped")

class UDSClient:
    """Worker 端 - 向主进程发送信令 (Worker Side)"""
    
    def __init__(self, gateway_uds_path: str):
        self.gateway_uds_path = gateway_uds_path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    def send_signal(self, slot_id: int, offset: int, size: int, status: int):
        """发送定长信令"""
        try:
            packet = struct.pack(SIGNAL_FORMAT, slot_id, offset, size, status)
            self.sock.sendto(packet, self.gateway_uds_path)
        except Exception as e:
            logger.error(f"Worker failed to send UDS signal: {e}")

    def close(self):
        self.sock.close()

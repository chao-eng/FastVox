import struct
import socket
import logging
import asyncio
import os
from enum import IntEnum
from typing import Callable, Optional, Union, Tuple
from app.core.platform_compat import platform

logger = logging.getLogger("FastVox")

# 信令帧格式 (16 字节): slot_id (I), offset (I), size (I), status (I)
SIGNAL_FORMAT = 'IIII'
SIGNAL_SIZE = struct.calcsize(SIGNAL_FORMAT)

# 后备方案兼容
try:
    _AF_UNIX = socket.AF_UNIX
except AttributeError:
    _AF_UNIX = None

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

    def start(self):
        """同步初始化 Socket，随后注册到 asyncio 并进行读"""
        
        if platform.use_udp_signaling:
            # --- Windows / Fallback: 使用 UDP Loopback ---
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(('127.0.0.1', platform.signal_port))
            logger.info(f"SignalServer (UDP) listening on 127.0.0.1:{platform.signal_port}")
        else:
            # --- Unix: 使用 UDS ---
            if os.path.exists(self.uds_path):
                try:
                    os.unlink(self.uds_path)
                except Exception as e:
                    logger.error(f"Failed to unlink old UDS socket: {e}")

            if _AF_UNIX is None:
               raise RuntimeError("AF_UNIX NOT SUPPORTED ON THIS SYSTEM")

            self.sock = socket.socket(_AF_UNIX, socket.SOCK_DGRAM)
            self.sock.bind(self.uds_path)
            if platform.platform != "win32":
                os.chmod(self.uds_path, 0o777)
            logger.info(f"SignalServer (UDS) listening on {self.uds_path}")
        
        # 优化缓冲区及非阻塞设置
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024) # 1MB 缓冲
        except:
            pass
        self.sock.setblocking(False)
        return self.sock

    def stop(self):
        """停止并清理"""
        if self.sock:
            self.sock.close()
            if not platform.use_udp_signaling and os.path.exists(self.uds_path):
                try:
                    os.unlink(self.uds_path)
                except:
                    pass
            logger.info("SignalServer stopped")

class UDSClient:
    """Worker 端 - 向主进程发送信令 (Worker Side)"""
    
    def __init__(self, gateway_addr: Union[str, Tuple[str, int]]):
        self.gateway_addr = gateway_addr
        
        if platform.use_udp_signaling:
             self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
             # 对于 Windows/UDP 模式，如果传入的是字符串(路径)，强制修正为元组
             if isinstance(self.gateway_addr, str):
                 self.gateway_addr = ('127.0.0.1', platform.signal_port)
        else:
             if _AF_UNIX is None:
                 raise RuntimeError("AF_UNIX NOT SUPPORTED ON THIS SYSTEM")
             self.sock = socket.socket(_AF_UNIX, socket.SOCK_DGRAM)

    def send_signal(self, slot_id: int, offset: int, size: int, status: int):
        """发送定长信令 (带重试机制)"""
        packet = struct.pack(SIGNAL_FORMAT, slot_id, offset, size, status)
        # 对于关键信号 (READY/ERROR)，尝试发送两次以应对 UDP 丢包
        tries = 2 if status in (SignalStatus.READY, SignalStatus.ERROR) else 1
        
        for _ in range(tries):
            try:
                self.sock.sendto(packet, self.gateway_addr)
            except Exception as e:
                logger.error(f"Worker failed to send signal: {e}")

    def close(self):
        self.sock.close()

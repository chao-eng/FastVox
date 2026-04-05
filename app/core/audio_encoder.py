import io
import av
import numpy as np
import logging
from typing import Iterator

logger = logging.getLogger("FastVox")

class AudioEncoder:
    """基于 PyAV 的内存级音频编码器 (PCM -> Opus/Ogg)"""
    
    def __init__(self, sample_rate: int = 24000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.bitrate = "64k"

    def encode_opus(self, pcm: bytes) -> bytes:
        """同步编码: 完整 PCM -> 完整 Ogg/Opus 容器字节流"""
        if not pcm:
            return b""
            
        output_buf = io.BytesIO()
        try:
            # 打开内存容器
            output_container = av.open(output_buf, mode='w', format='ogg')
            
            # 添加 Opus 编码流 (libopus)
            stream = output_container.add_stream('libopus', rate=self.sample_rate)
            stream.bitrate = int(self.bitrate[:-1]) * 1000
            stream.channels = self.channels
            stream.layout = 'mono' if self.channels == 1 else 'stereo'
            
            # 将 int16 字节流转换为 numpy 数组并注入 av.AudioFrame
            data = np.frombuffer(pcm, dtype=np.int16).reshape(1, -1)
            frame = av.AudioFrame.from_ndarray(
                data, 
                format='s16', 
                layout='mono' if self.channels == 1 else 'stereo'
            )
            frame.sample_rate = self.sample_rate
            
            # 编码并混流
            for packet in stream.encode(frame):
                output_container.mux(packet)
            
            # Flush 编码器
            for packet in stream.encode(None):
                output_container.mux(packet)
            
            output_container.close()
            return output_buf.getvalue()
        except Exception as e:
            logger.error(f"Sync audio encoding failed: {e}")
            return b""

    def encode_opus_streaming(self, pcm_chunks: Iterator[bytes]) -> Iterator[bytes]:
        """生成器模式: 接收 PCM 分片流，产生 Ogg/Opus 容器分片流"""
        output_buf = io.BytesIO()
        
        try:
            output_container = av.open(output_buf, mode='w', format='ogg')
            stream = output_container.add_stream('libopus', rate=self.sample_rate)
            stream.bitrate = int(self.bitrate[:-1]) * 1000
            stream.channels = self.channels
            
            pointer = 0
            for pcm in pcm_chunks:
                if not pcm: continue
                
                # 构造 frame
                data = np.frombuffer(pcm, dtype=np.int16).reshape(1, -1)
                frame = av.AudioFrame.from_ndarray(data, format='s16', layout='mono')
                frame.sample_rate = self.sample_rate
                
                # 编码
                for packet in stream.encode(frame):
                    output_container.mux(packet)
                
                # 读取新增的容器字节
                res = output_buf.getvalue()
                chunk = res[pointer:]
                pointer = len(res)
                if chunk:
                    yield chunk
            
            # 最后一个分片
            for packet in stream.encode(None):
                output_container.mux(packet)
            
            output_container.close()
            res = output_buf.getvalue()
            chunk = res[pointer:]
            if chunk:
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming audio encoding failed: {e}")

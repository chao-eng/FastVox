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
            output_container = av.open(output_buf, mode='w', format='webm')
            
            # 添加 Opus 编码流 (libopus)
            stream = output_container.add_stream('libopus', rate=self.sample_rate)
            
            # 使用更健壮的方式设置比特率和声道布局
            bitrate_val = int(self.bitrate.replace('k', '')) * 1000
            stream.codec_context.bit_rate = bitrate_val
            stream.codec_context.layout = 'mono' if self.channels == 1 else 'stereo'
            stream.codec_context.sample_rate = self.sample_rate
            
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

    def encode_opus_streaming(self, pcm_iterator: Iterator[bytes]) -> Iterator[bytes]:
        """
        持久化流式编码: 接受一个 PCM 字节流迭代器，产生单一 Ogg 容器的字节流。
        确保整个过程只有一个 Ogg Header。
        """
        output_buf = io.BytesIO()
        pointer = 0
        
        try:
            # 1. 初始化容器与流 (一次性)
            output_container = av.open(output_buf, mode='w', format='webm')
            stream = output_container.add_stream('libopus', rate=self.sample_rate)
            
            bitrate_val = int(self.bitrate.replace('k', '')) * 1000
            stream.codec_context.bit_rate = bitrate_val
            stream.codec_context.layout = 'mono' if self.channels == 1 else 'stereo'
            stream.codec_context.sample_rate = self.sample_rate
            
            # 2. 迭代处理分片
            for pcm in pcm_iterator:
                if not pcm: continue
                
                # 构造 frame
                data = np.frombuffer(pcm, dtype=np.int16).reshape(1, -1)
                frame = av.AudioFrame.from_ndarray(data, format='s16', layout='mono')
                frame.sample_rate = self.sample_rate
                
                # 编码并混流
                for packet in stream.encode(frame):
                    output_container.mux(packet)
                
                # 读取并返回新增的字节块
                res = output_buf.getvalue()
                chunk = res[pointer:]
                pointer = len(res)
                if chunk:
                    yield chunk
            
            # 3. 结束编码 (Flush)
            for packet in stream.encode(None):
                output_container.mux(packet)
            
            output_container.close()
            
            # 返回最后的字节 (包括 Ogg Footer)
            res = output_buf.getvalue()
            chunk = res[pointer:]
            if chunk:
                yield chunk
                
        except Exception as e:
            logger.error(f"Stateful streaming audio encoding failed: {e}")

class PcmTempoProcessor:
    """
    在 PCM 层面进行无音高扭曲变速处理。
    原理：利用 FFmpeg 的 atempo 滤镜对原始 PCM 数据进行时间拉伸/压缩，
    输出变速后的 PCM 字节流。与编码器完全解耦。
    """
    def __init__(self, sample_rate: int = 24000, speed: float = 1.0):
        self.sample_rate = sample_rate
        self.speed = speed
        self.graph = av.filter.Graph()
        self.src = self.graph.add_abuffer(
            sample_rate=sample_rate,
            format='s16',
            layout='mono',
        )
        self.sink = self.graph.add("abuffersink")
        atempo_node = self.graph.add("atempo", str(speed))
        # 关键：atempo 内部使用 dblp (双精度浮点) 格式，必须用 aformat 转回 s16
        aformat_node = self.graph.add("aformat", "sample_fmts=s16:channel_layouts=mono")
        self.src.link_to(atempo_node)
        atempo_node.link_to(aformat_node)
        aformat_node.link_to(self.sink)
        self.graph.configure()

    def process(self, pcm: bytes) -> bytes:
        """处理一个 PCM 分片，返回变速后的 PCM 字节"""
        if not pcm:
            return b""
        data = np.frombuffer(pcm, dtype=np.int16).reshape(1, -1)
        frame = av.AudioFrame.from_ndarray(data, format='s16', layout='mono')
        frame.sample_rate = self.sample_rate

        self.src.push(frame)

        parts = []
        while True:
            try:
                out_frame = self.sink.pull()
                # aformat 已经保证输出是 s16 格式，直接转换即可
                out_data = out_frame.to_ndarray().flatten()
                parts.append(out_data.astype(np.int16).tobytes())
            except av.FFmpegError:
                break
        return b''.join(parts)

    def flush(self) -> bytes:
        """刷出滤镜中残留的音频数据"""
        try:
            self.src.push(None)
            parts = []
            while True:
                try:
                    out_frame = self.sink.pull()
                    out_data = out_frame.to_ndarray().flatten()
                    parts.append(out_data.astype(np.int16).tobytes())
                except av.FFmpegError:
                    break
            return b''.join(parts)
        except Exception:
            return b''



class StreamingEncoder:
    """有状态的流式编码器，适合在异步循环中分段调用 (纯编码，不含变速逻辑)"""
    def __init__(self, sample_rate: int = 24000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.output_buf = io.BytesIO()
        self.pointer = 0
        
        # 初始化 PyAV 容器
        self.container = av.open(self.output_buf, mode='w', format='webm')
        self.stream = self.container.add_stream('libopus', rate=self.sample_rate)
        self.stream.codec_context.bit_rate = 64000
        self.stream.codec_context.layout = 'mono' if channels == 1 else 'stereo'
        self.stream.codec_context.sample_rate = sample_rate

    def encode_chunk(self, pcm: bytes) -> bytes:
        """编码一个 PCM 分片并返回当前新增的容器字节"""
        if not pcm: return b""
        
        try:
            data = np.frombuffer(pcm, dtype=np.int16).reshape(1, -1)
            frame = av.AudioFrame.from_ndarray(data, format='s16', layout='mono' if self.channels == 1 else 'stereo')
            frame.sample_rate = self.sample_rate
            
            for packet in self.stream.encode(frame):
                self.container.mux(packet)
            
            res = self.output_buf.getvalue()
            chunk = res[self.pointer:]
            self.pointer = len(res)
            return chunk
        except Exception as e:
            logger.error(f"StreamingEncoder chunk encoding failed: {e}")
            return b""

    def close(self) -> bytes:
        """关闭容器并返回最后的 Footer 字节"""
        try:
            for packet in self.stream.encode(None):
                self.container.mux(packet)
            self.container.close()
            
            res = self.output_buf.getvalue()
            chunk = res[self.pointer:]
            self.pointer = len(res)
            return chunk
        except Exception as e:
            logger.error(f"StreamingEncoder close failed: {e}")
            return b""

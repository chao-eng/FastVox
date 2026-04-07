import os
import uuid
import logging
import av
import numpy as np
from typing import Tuple

logger = logging.getLogger("FastVox")

def process_voice_audio(input_path: str, output_path: str) -> Tuple[float, int]:
    """
    处理音频文件：重采样到 24000Hz, 单声道, s16 格式。
    返回: (时长_秒, 采样点总数)
    """
    container = av.open(input_path)
    if not container.streams.audio:
        container.close()
        raise ValueError("音频文件中未发现音频流")
    
    stream = container.streams.audio[0]
    stream.thread_type = 'AUTO'
    
    resampler = av.AudioResampler(
        format='s16', 
        layout='mono', 
        rate=24000
    )
    
    output_container = av.open(output_path, mode='w', format='wav')
    output_stream = output_container.add_stream('pcm_s16le', rate=24000)
    output_stream.layout = 'mono'
    
    total_samples = 0
    input_rate = stream.rate
    
    try:
        for frame in container.decode(audio=0):
            total_samples += frame.samples
            resampled_frames = resampler.resample(frame)
            for rf in resampled_frames:
                for packet in output_stream.encode(rf):
                    output_container.mux(packet)
        
        # 刷出
        for rf in resampler.resample(None):
            for packet in output_stream.encode(rf):
                output_container.mux(packet)
        
        for packet in output_stream.encode(None):
            output_container.mux(packet)
            
    finally:
        output_container.close()
        container.close()
        
    duration = total_samples / input_rate
    return duration, total_samples

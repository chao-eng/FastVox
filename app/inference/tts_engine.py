import numpy as np
import logging
import os
from typing import Tuple, Optional
from config.settings import get_settings

logger = logging.getLogger("FastVox")
settings = get_settings()

try:
    import sherpa_onnx
except ImportError:
    logger.error("sherpa-onnx not installed, please run 'pip install sherpa-onnx'")

class TTSInferenceError(Exception):
    """自定义推理异常"""
    pass

class TTSEngine:
    """
    封装 sherpa-onnx 的 OfflineTts (ZipVoice 模式)
    支持 In-context Learning (Speech Infilling)
    """
    
    def __init__(self, model_dir: str, num_threads: int = 1, num_steps: int = 4):
        self.model_dir = model_dir
        self.num_threads = num_threads
        self.num_steps = num_steps
        self.tts: Optional[sherpa_onnx.OfflineTts] = None
        
        self._initialize_engine()

    def _initialize_engine(self):
        """初始化推理引擎"""
        try:
            # 校验核心模型文件及其路径
            # ZipVoice 关键模型文件清单: encoder.onnx, decoder.onnx, vocos_24khz.onnx
            # tokens.txt, lexicon.txt, espeak-ng-data/
            
            # 构造配置
            tts_config = sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                    zipvoice=sherpa_onnx.OfflineTtsZipvoiceModelConfig(
                        encoder=os.path.join(self.model_dir, "encoder.int8.onnx"),
                        decoder=os.path.join(self.model_dir, "decoder.int8.onnx"),
                        vocoder=os.path.join(self.model_dir, "vocos_24khz.onnx"),
                        tokens=os.path.join(self.model_dir, "tokens.txt"),
                        lexicon=os.path.join(self.model_dir, "lexicon.txt"),
                        data_dir=os.path.join(self.model_dir, "espeak-ng-data"),
                    ),
                    num_threads=self.num_threads,
                    debug=False,
                    provider="cpu" # 默认 CPU 推理以兼容所有平台
                ),
                max_num_sentences=1,
            )
            
            self.tts = sherpa_onnx.OfflineTts(tts_config)
            logger.info(f"TTSEngine initialized from {self.model_dir}")
            
        except Exception as e:
            logger.error(f"Failed to initialize sherpa-onnx engine: {e}")
            raise TTSInferenceError(f"Engine initialization failed: {e}")

    def synthesize(self, 
                  text: str, 
                  speed: float = 1.0,
                  prompt_audio: Optional[str] = None, 
                  prompt_text: Optional[str] = None
                  ) -> Tuple[bytes, int]:
        """
        进行流匹配语音合成 (Zero-shot Voice Cloning)
        """
        if not self.tts:
            raise TTSInferenceError("Engine not initialized")

        try:
            # 执行推理 (同步阻塞调用)
            # 对于 ZipVoice，必须提供参考音色信息
            if prompt_audio and prompt_text:
                audio = self.tts.generate(
                    text=text,
                    sid=0,
                    speed=speed,
                    # 注意: 确保使用关键字参数以匹配 ZipVoice 模式下的 generate 签名
                    speaker_audio=prompt_audio,
                    speaker_text=prompt_text
                )
            else:
                # ZipVoice 强制要求参考，若未提供则无法模拟合成
                raise TTSInferenceError("ZipVoice requires prompt_audio and prompt_text for in-context learning")

            # 将 float 格式的 audio samples 转换为 int16 PCM (mono)
            pcm = (np.array(audio.samples) * 32767).astype(np.int16)
            return pcm.tobytes(), audio.sample_rate
            
        except Exception as e:
            logger.error(f"TTS Synthesis failed: {e}")
            raise TTSInferenceError(f"Synthesis failed: {e}")

    def warmup(self):
        """预热推理 (ZipVoice 模式下仅进行模型状态确认)"""
        logger.info("TTSEngine is initialized and ready (Warmup bypassed for context-based model)")

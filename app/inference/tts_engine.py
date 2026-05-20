import numpy as np
import logging
import os
import re
import unicodedata
from typing import Tuple, Optional
from config.settings import get_settings

logger = logging.getLogger("FastVox")
settings = get_settings()

try:
    import mlx.core as mx
    from mlx_audio.tts.utils import load as load_mlx_model
except ImportError:
    logger.error("Required libraries (mlx or mlx_audio) not installed.")

class TTSInferenceError(Exception):
    """自定义推理异常"""
    pass

class TTSEngine:
    """
    封装 mlx_audio + k2-fsa/OmniVoice 模型的 TTS 引擎
    支持 In-context Learning (Speech Infilling) 和零样本声纹克隆
    """
    
    def __init__(self, model_name: str, num_threads: int = 1, num_steps: int = 32):
        self.model_name = model_name
        self.num_threads = num_threads
        self.num_steps = num_steps
        self.model = None
        
        self._initialize_engine()

    def _initialize_engine(self):
        """初始化推理引擎"""
        try:
            logger.info(f"Loading mlx_audio model: {self.model_name}...")
            # 使用 mlx_audio 标准高层加载函数
            self.model = load_mlx_model(self.model_name)
            logger.info(f"TTSEngine successfully initialized from {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize mlx-audio engine: {e}")
            raise TTSInferenceError(f"Engine initialization failed: {e}")

    def _has_chinese(self, text: str) -> bool:
        """判断文本中是否包含中文字符"""
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def _number_to_chinese(self, text: str) -> str:
        """将阿拉伯数字转换为中文念法"""
        units = ['', '十', '百', '千', '万', '十', '百', '千', '亿']
        digits = '零一二三四五六七八九'
        
        def _to_cn(num_str):
            if not num_str.isdigit(): return num_str
            n = int(num_str)
            if n == 0: return digits[0]
            res = ""
            # 简单处理：如果是超长数字（如电话），逐个念
            if len(num_str) > 5:
                return "".join(digits[int(d)] for d in num_str)
            # 正常处理：位权转换
            for i, d in enumerate(num_str[::-1]):
                if d != '0':
                    res = digits[int(d)] + units[i] + res
                else:
                    if not res.startswith(digits[0]):
                        res = digits[0] + res
            res = res.rstrip('零')
            if res.startswith('一十'): res = res[1:]
            return res

        import re
        return re.sub(r'\d+', lambda x: _to_cn(x.group()), text)

    def _normalize_text(self, text: str) -> str:
        """强化文本清理：去不可见字符 + 全角转半角 + 数字转中文 + 标点映射 + OOV过滤"""
        
        # --- 第 0 步：去除不可见 / 控制 Unicode 字符 ---
        invisible_pattern = re.compile(
            r'[\u200b\u200c\u200d\u200e\u200f'
            r'\u00ad\ufeff\u2028\u2029'
            r'\u202a-\u202e\u2060-\u2069]+'
        )
        text = invisible_pattern.sub('', text)
        
        # 去除 Unicode 控制字符 (Cc 类别)，保留换行和空格
        text = ''.join(
            ch for ch in text
            if ch in ('\n', '\t', ' ') or unicodedata.category(ch) != 'Cc'
        )
        
        # --- 第 1 步：全角英文字母 / 数字转半角 ---
        result = []
        for ch in text:
            cp = ord(ch)
            if 0xFF01 <= cp <= 0xFF5E:
                result.append(chr(cp - 0xFEE0))
            elif cp == 0x3000:
                result.append(' ')
            else:
                result.append(ch)
        text = ''.join(result)
        
        # --- 第 2 步：数字转中文 ---
        text = self._number_to_chinese(text)
        
        # --- 第 3 步：中文标点全面映射 ---
        replacements = {
            '\u201c': ' ', '\u201d': ' ',
            '\u2018': ' ', '\u2019': ' ',
            '\u300a': ',', '\u300b': ',',
            '\uff08': '(', '\uff09': ')',
            '\u3010': '[', '\u3011': ']',
            '\u3008': ',', '\u3009': ',',
            '\u300c': ',', '\u300d': ',',
            '\u300e': ',', '\u300f': ',',
            '\u2014': ',', '\u2013': ',',
            '\uff5e': ',', '\u2026': ',',
            '\u3001': ',',
            '\u00b7': ' ', '\u2022': ' ',
            '\u3002': '.',
            '\uff01': '!', '\uff1f': '?',
            '\uff0c': ',', '\uff1b': ';',
            '\uff1a': ':',
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        
        # --- 第 4 步：清除 OOV 字符 ---
        # 仅保留：CJK 基本区 + 扩展A、拉丁字母、空白、标点以及允许非言语标签的方括号 []
        allowed_pattern = re.compile(
            r'[\u4e00-\u9fff\u3400-\u4dbf'
            r'a-zA-Z0-9\s'
            r",.!?;:\-'()\[\]]"
        )
        text = ''.join(ch for ch in text if allowed_pattern.match(ch))
        
        # --- 第 5 步：压缩多余空格 ---
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def synthesize(self, 
                  text: str, 
                  speed: float = 1.0,
                  prompt_audio: Optional[str] = None, 
                  prompt_text: Optional[str] = None,
                  prompt_samples: Optional[bytes] = None
                  ) -> Tuple[bytes, int]:
        """
        进行零样本声音克隆与流式上下文语音合成
        """
        if not self.model:
            raise TTSInferenceError("Engine not initialized")

        # 文本预处理
        text = self._normalize_text(text)
        if prompt_text:
            prompt_text = self._normalize_text(prompt_text)

        logger.info(f"Begin synthesis for text: {text[:30]}...")

        try:
            # 自动进行语言推断
            lang_code = "zh" if self._has_chinese(text) else "en"
            
            ref_audio_input = None
            ref_text_input = prompt_text

            if prompt_samples:
                # 将 int16 字节流转换为 float32 采样并归一化到 [-1.0, 1.0]
                float_samples = np.frombuffer(prompt_samples, dtype=np.int16).astype(np.float32) / 32767.0
                float_samples = np.clip(float_samples, -1.0, 1.0)
                # 包装为 mlx 数组格式
                ref_audio_input = mx.array(float_samples)
                logger.debug(f"Using {len(float_samples)} samples from PCM bytes for infilling context")
            elif prompt_audio:
                # 直接传递音频文件路径
                ref_audio_input = prompt_audio
                logger.debug(f"Using audio file path: {prompt_audio} for voice profile cloning")

            # 调用 OmniVoice 的 generate 接口 (返回一个生成 GenerationResult 的 generator)
            if ref_audio_input is not None and ref_text_input:
                results = self.model.generate(
                    text=text,
                    ref_audio=ref_audio_input,
                    ref_text=ref_text_input,
                    lang_code=lang_code,
                    num_steps=self.num_steps,
                    speed=speed
                )
            else:
                results = self.model.generate(
                    text=text,
                    lang_code=lang_code,
                    num_steps=self.num_steps,
                    speed=speed
                )

            # 获取合成结果
            result = next(results)
            
            # 将 mx.array 类型的 result.audio 转换为 np.ndarray
            audio_samples = np.array(result.audio)
            
            # 将 float32 格式的音频采样转换为 int16 PCM (mono)
            pcm = (audio_samples * 32767).astype(np.int16)
            pcm_bytes = pcm.tobytes()
            
            logger.info(f"Synthesis success: {len(audio_samples)} samples generated ({len(pcm_bytes)} bytes)")
            return pcm_bytes, result.sample_rate
            
        except Exception as e:
            logger.error(f"TTS Engine internal error: {e}")
            raise TTSInferenceError(f"Internal synthesis failure: {e}")

    def warmup(self):
        """预热推理 (进行基础状态确认)"""
        logger.info("TTSEngine is initialized and ready")

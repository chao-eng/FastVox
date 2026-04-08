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
    import sherpa_onnx
    import av
except ImportError:
    logger.error("Required libraries (sherpa-onnx or av) not installed.")

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
        # 零宽空格 (U+200B)、BOM (U+FEFF)、零宽连接符 / 非连接符、软连字等
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
        # 仅保留：CJK 基本区 + 扩展A、拉丁字母、空白、tokens.txt 中存在的标点
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
                  prompt_samples: Optional[bytes] = None # 新增：支持直接传入 PCM 字节流作为 Prompt
                  ) -> Tuple[bytes, int]:
        """
        进行流匹配语音合成 (Zero-shot Voice Cloning)
        """
        if not self.tts:
            raise TTSInferenceError("Engine not initialized")

        # 文本预处理 (去除 OOV 字符警告)
        text = self._normalize_text(text)
        if prompt_text:
            prompt_text = self._normalize_text(prompt_text)

        logger.info(f"Begin synthesis for text: {text[:30]}...")

        try:
            # 执行推理 (同步阻塞调用)
            # 对于 ZipVoice，必须提供参考音色信息 (可以是文件路径，也可以是上一段生成的采样)
            if (prompt_audio or prompt_samples) and prompt_text:
                final_prompt_samples = []
                
                # 优先使用实时传入的采样 (Segment Context)
                if prompt_samples:
                    # 将 int16 字节流转换为 float32 常规采样，使用与生成端对称的量化系数 (32767)
                    final_prompt_samples = np.frombuffer(prompt_samples, dtype=np.int16).astype(np.float32) / 32767.0
                    # 裁剪限幅，防止计算过程中的溢出
                    final_prompt_samples = np.clip(final_prompt_samples, -1.0, 1.0)
                    logger.debug(f"Using {len(final_prompt_samples)} samples for context prompt (Normalization: 32767)")
                
                # 其次使用文件路径 (Profile Mode)
                elif prompt_audio:
                    prompt_container = av.open(prompt_audio)
                    for frame in prompt_container.decode(audio=0):
                        s = frame.to_ndarray().flatten().astype(np.float32)
                        if frame.format.name == 's16':
                            s = s / 32768.0
                        final_prompt_samples.extend(s)
                    prompt_container.close()

                # 调用符合 ZipVoice 签名的 generate 方法
                audio = self.tts.generate(
                    text=text,
                    prompt_text=prompt_text,
                    prompt_samples=final_prompt_samples,
                    sample_rate=24000, 
                    speed=speed,
                    num_steps=self.num_steps
                )
            else:
                raise TTSInferenceError("ZipVoice requires prompt_audio/samples and prompt_text")

            # 将 float 格式的 audio samples 转换为 int16 PCM (mono)
            pcm = (np.array(audio.samples) * 32767).astype(np.int16)
            pcm_bytes = pcm.tobytes()
            logger.info(f"Synthesis success: {len(audio.samples)} samples generated ({len(pcm_bytes)} bytes)")
            return pcm_bytes, audio.sample_rate
            
        except Exception as e:
            logger.error(f"TTS Engine internal error: {e}")
            raise TTSInferenceError(f"Internal synthesis failure: {e}")

    def warmup(self):
        """预热推理 (ZipVoice 模式下仅进行模型状态确认)"""
        logger.info("TTSEngine is initialized and ready (Warmup bypassed for context-based model)")

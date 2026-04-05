import re
import logging
from typing import List

logger = logging.getLogger("FastVox")

class TextSplitter:
    """智能长文本切分 (基于正则表达式断句)"""
    
    # 单片段最大字数 (ZipVoice 建议单次推理不超过 200 字以保持稳定性能)
    MAX_CHUNK_LENGTH: int = 200
    
    # 标点符号映射 (中文 + 英文)
    # 第一级: 终结符
    TERMINATORS = "。！？!?；; \n"
    # 第二级: 辅助断句 (逗号等)
    SOFT_PUNCS = "，, "

    def __init__(self, max_length: int = 200):
        self.max_length = max_length

    def split(self, text: str) -> List[str]:
        """按优先级智能切分长文本"""
        if not text:
            return []
            
        # 0. 预处理
        text = text.strip()
        if len(text) <= self.max_length:
            return [text]

        # 1. 第一步: 根据硬分句符 (。！？) 初步切分
        # 正则捕获组保留分隔符
        pattern = f'([{self.TERMINATORS}])'
        raw_chunks = re.split(pattern, text)
        
        # 重新组合：将分隔符合并回前一个句子
        chunks = []
        current_chunk = ""
        for i in range(0, len(raw_chunks) - 1, 2):
            s, p = raw_chunks[i], raw_chunks[i+1]
            if len(current_chunk) + len(s + p) <= self.max_length:
                current_chunk += s + p
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = s + p
        
        # 处理最后一截
        if len(raw_chunks) % 2 == 1:
            last = raw_chunks[-1]
            if len(current_chunk) + len(last) <= self.max_length:
                current_chunk += last
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = last
        
        if current_chunk:
            chunks.append(current_chunk.strip())

        # 2. 第二步: 对依然超过 max_length 的片段根据软分句符 (，) 二次切分
        final_chunks = []
        for c in chunks:
            if len(c) <= self.max_length:
                final_chunks.append(c)
            else:
                # 二次切分
                soft_pattern = f'([{self.SOFT_PUNCS}])'
                sub_raw = re.split(soft_pattern, c)
                sub_current = ""
                for j in range(0, len(sub_raw) - 1, 2):
                    s, p = sub_raw[j], sub_raw[j+1]
                    if len(sub_current) + len(s + p) <= self.max_length:
                        sub_current += s + p
                    else:
                        if sub_current:
                            final_chunks.append(sub_current.strip())
                        sub_current = s + p
                
                if len(sub_raw) % 2 == 1:
                    last_sub = sub_raw[-1]
                    if len(sub_current) + len(last_sub) <= self.max_length:
                        sub_current += last_sub
                    else:
                        if sub_current:
                            final_chunks.append(sub_current.strip())
                        sub_current = last_sub
                
                if sub_current:
                    final_chunks.append(sub_current.strip())

        # 3. 三级校验: 过滤空片段并暴力处理依然超长内容 (兜底)
        safe_chunks = []
        for fc in final_chunks:
            fc = fc.strip()
            if not fc:
                continue
            if len(fc) > self.max_length:
                # 极端情况 (无标点符号长句): 暴力按字数截断
                for k in range(0, len(fc), self.max_length):
                    safe_chunks.append(fc[k: k + self.max_length])
            else:
                safe_chunks.append(fc)

        logger.debug(f"Split text ({len(text)} chars) into {len(safe_chunks)} segments.")
        return safe_chunks

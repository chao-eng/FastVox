# FastVox 极速语音合成系统

FastVox 是一款基于 `sherpa-onnx` 的高性能、低延迟流式语音合成系统。它专为极致速度而设计，支持中英文混报、实时音频流输出、全自动使用量统计以及声纹克隆管理。

## 🚀 核心特性

- **极致延迟**：基于 ZipVoice 模型与流式编码，实现“毫秒级”首字响应。
- **现代 UI**：精美的飞书/Lark 风格极简设计，完美支持**暗黑模式**。
- **全栈统计**：实时监控推理吞吐量 (Requests/min)、合成字数与平均时延。
- **声纹管理**：支持上传自定义小段音频快速提取声纹，实现个性化语音合成。
- **流式架构**：后端 Python FastAPI + 前端 Vue 3，配合 WebSocket 实时流式传输。

---

## 🛠️ 环境准备与模型下载

运行本项目需要下载以下核心模型文件：

### 1. 核心 TTS 模型 (ZipVoice)
本项目使用 ZipVoice 蒸馏量化版模型，兼顾速度与质量。
- **下载地址**：[sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2](https://mirror.ghproxy.com/https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2)
- **说明**：解压后请将 `.onnx` 模型放置于 `app/models/zipvoice/` 目录下。

### 2. 声学解析器 (Vocoder)
用于将推理特征转化为 24khz 高质量音频。
- **下载地址**：[vocos_24khz.onnx](https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/vocos_24khz.onnx)
- **说明**：解压后请将 `.onnx` 解析器放置于 `app/models/zipvoice/` 目录下。

### 3. 说明与推荐声纹数据 (示例)
如果你需要高质量的中文声纹参考素材，可以参考以下公开数据集：
- **中文音源推荐**：[Genshin-Voice (simon3000)](https://huggingface.co/datasets/simon3000/genshin-voice/viewer/default/train?f%5Blanguage%5D%5Bvalue%5D=%27Chinese%27)
- **提示**：在该数据集中挑选 5s-10s 的清晰录音作为声纹上传，效果最佳。

---

## 📦 快速启动

### 系统初始化
1.  **后端安装**：
    ```bash
    pip install -r requirements.txt
    ```
2.  **前端安装**：
    ```bash
    cd web
    npm install
    ```

### 启动服务
1.  **运行后端**：
    ```bash
    python -m app.main
    ```
2.  **开发环境前端**：
    ```bash
    npm run dev
    ```

---

## 📸 界面预览

- **语音合成**：实时流式预览，支持语速调节。
- **使用统计**：动态图表，每分钟吞吐量实时可见。
- **声纹管理**：胶囊风格卡片管理，支持在线试听与删除。
- **系统设置**：支持全局暗黑模式一键切换。

---
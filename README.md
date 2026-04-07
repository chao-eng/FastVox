# FastVox 极速语音合成系统

FastVox 是一款基于 `sherpa-onnx` 的高性能、低延迟流式语音合成系统。它专为极致速度而设计，支持中英文混报、实时音频流输出、全自动使用量统计以及声纹克隆管理。

## 🚀 核心特性

- **极致延迟**：基于 ZipVoice 模型与流式编码，实现“毫秒级”首字响应。
- **共享声纹**：支持“公开”声纹属性。管理员可上传并共享声纹，普通用户可直接选用。
- **角色管理**：支持管理员与普通用户角色。普通用户界面极简（仅保留语音合成功能）。
- **批量导入**：支持通过 ZIP 压缩包 (metadata.json + 音频文件) 一键批量导入复杂声纹库。
- **全栈统计**：实时监控推理吞吐量 (Requests/min)、合成字数与平均时延。
- **现代 UI**：精美的飞书/Lark 风格极简设计，完美支持**暗黑模式**。

---

## 🛠️ 环境准备与模型下载

运行本项目需要下载以下核心模型文件：

### 1. 核心 TTS 模型 (ZipVoice)
本项目使用 ZipVoice 蒸馏量化版模型，兼顾速度与质量。
- **下载地址**：[sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2](https://mirror.ghproxy.com/https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2)
- **说明**：解压后请将 `.onnx` 模型放置于 `models/zipvoice/` 目录下。

### 2. 声学解析器 (Vocoder)
用于将推理特征转化为 24khz 高质量音频。
- **下载地址**：[vocos_24khz.onnx](https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/vocos_24khz.onnx)
- **说明**：解压后请将 `.onnx` 解析器放置于 `models/zipvoice/` 目录下。

---

## 📦 快速启动 (Conda 环境)

为了确保环境隔离，建议使用 Conda 启动脚本。

### 1. 初始化环境
该脚本将创建名为 `fastvox` 的隔离环境并安装所有 Python 依赖：
```bash
# 赋予执行权限并安装
chmod +x scripts/setup_conda.sh
./scripts/setup_conda.sh
```

### 2. 启动服务 (仅后端)
该脚本将自动执行前端构建 (`npm build`) 并启动后端服务器：
```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

### 3. 重启服务
如果代码发生变动，直接重启后端：
```bash
./scripts/restart.sh
```

---

## 📸 界面预览

- **语音合成**：实时流式预览，支持语速调节。
- **用户管理 (管理员)**：管理员可创建普通账号，分配系统资源。
- **声纹管理 (管理员)**：胶囊风格卡片管理，支持公开/私有属性切换、批量导入。
- **使用统计**：动态图表，每分钟吞吐量实时可见。

---

## 📝 许可条款 (License)

本项目采用 **自定义非商业性许可**。

1.  **开源不等于免费商用**：本软件仅供个人学习、科研、教学或非营利性目的使用。严禁将其用于任何形式的商业盈利行为。
2.  **署名要求**：在任何展示或二次分发中，必须在显著位置标明项目出处：**"Powered by FastVox (https://github.com/guojc/FastVox)"**。

详情请参阅项目根目录下的 [LICENSE](LICENSE) 文件。
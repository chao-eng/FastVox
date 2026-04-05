# 使用 Python 3.10 slim 镜像以减小体积
FROM python:3.10-slim-bookworm

# 安装系统依赖 (ffmpeg 为 PyAV 所需)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavcodec-dev \
    libswresample-dev \
    libswscale-dev \
    libavutil-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖项并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY . .

# 创建数据与模型目录挂载点
RUN mkdir -p data/voices models/zipvoice

# 暴露端口
EXPOSE 8000

# 环境变量
ENV FASTVOX_HOST=0.0.0.0
ENV FASTVOX_PORT=8000

# 启动 (需使用 --ipc host 运行)
CMD ["python", "-m", "app.main"]

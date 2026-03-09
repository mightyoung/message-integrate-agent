# ============================================================
# BettaFish - 舆情分析服务 Dockerfile
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖 (使用预编译 wheel)
RUN pip install --no-cache-dir --only-binary=:all: \
    flask==3.0.0 \
    requests==2.31.0 \
    openai==1.12.0 \
    python-dotenv==1.0.0 \
    loguru==0.7.2 \
    httpx==0.27.0 \
    beautifulsoup4==4.12.3 \
    lxml==5.1.0

# 复制应用代码
COPY app.py /app/

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=app.py

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "/app/app.py"]

# ============================================================
# BettaFish - 舆情分析服务 Dockerfile
# ============================================================
#
# 功能: 舆情爬虫 + 多智能体分析
# 端口: 5000 (API), 5001 (Web UI)
#
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt || true

# 克隆 BettaFish
RUN git clone https://github.com/666ghj/BettaFish.git /app/bettafish || \
    (echo "Failed to clone BettaFish, using placeholder" && mkdir -p /app)

# 如果克隆成功，安装依赖
RUN if [ -f /app/bettafish/requirements.txt ]; then \
        pip install --no-cache-dir -r /app/bettafish/requirements.txt; \
    fi

# 复制配置
COPY config.yaml /app/bettafish/config.yaml || true

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 暴露端口
EXPOSE 5000 5001

# 启动命令 (需要根据实际项目调整)
CMD ["bash", "-c", "cd /app/bettafish && pip install -e . 2>/dev/null || true && python app.py"]

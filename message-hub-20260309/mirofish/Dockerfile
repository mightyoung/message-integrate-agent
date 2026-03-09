# ============================================================
# MiroFish - 预测分析服务 Dockerfile
# ============================================================
#
# 功能: AI 预测引擎 + 群体仿真
# 端口: 5001 (API), 3000 (Web UI)
#
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 克隆 MiroFish
RUN git clone https://github.com/666ghj/MiroFish.git /app/mirofish || \
    (echo "Failed to clone MiroFish, using placeholder" && mkdir -p /app)

# 安装依赖
RUN if [ -f /app/mirofish/requirements.txt ]; then \
        pip install --no-cache-dir -r /app/mirofish/requirements.txt; \
    fi

# 复制配置
COPY config.yaml /app/mirofish/config.yaml || true

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 暴露端口
EXPOSE 5001 3000

# 启动命令 (需要根据实际项目调整)
CMD ["bash", "-c", "cd /app/mirofish && pip install -e . 2>/dev/null || true && python app.py"]

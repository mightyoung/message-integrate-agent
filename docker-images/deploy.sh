# ============================================================
# Message Integrate Agent - 一键部署脚本
# ============================================================
#
# 使用方式:
#   1. 将整个 docker-images 目录复制到 NAS
#   2. cd docker-images
#   3. chmod +x deploy.sh && ./deploy.sh
#
# ============================================================

set -e

echo "=== Message Hub 部署脚本 ==="
echo ""

# 检查 docker 和 docker-compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

echo "✓ Docker 环境检查通过"
echo ""

# 检查镜像文件
echo "=== 检查镜像文件 ==="
if [ -f "message-integrate-agent-prod.tar" ]; then
    echo "✓ message-integrate-agent-prod.tar 存在"
else
    echo "❌ message-integrate-agent-prod.tar 缺失"
    exit 1
fi

if [ -f "clash-latest.tar" ]; then
    echo "✓ clash-latest.tar 存在"
else
    echo "❌ clash-latest.tar 缺失"
fi

if [ -f "bettafish-latest.tar" ]; then
    echo "✓ bettafish-latest.tar 存在"
else
    echo "❌ bettafish-latest.tar 缺失"
fi

if [ -f "mirofish-latest.tar" ]; then
    echo "✓ mirofish-latest.tar 存在"
else
    echo "❌ mirofish-latest.tar 缺失"
fi

echo ""

# 加载镜像
echo "=== 加载 Docker 镜像 ==="
echo "加载 message-integrate-agent:prod..."
docker load -i message-integrate-agent-prod.tar

echo "加载 dreamacro/clash:latest..."
docker load -i clash-latest.tar

echo "加载 bettafish:latest..."
docker load -i bettafish-latest.tar

echo "加载 mirofish:latest..."
docker load -i mirofish-latest.tar

echo ""

# 启动服务
echo "=== 启动服务 ==="
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "=== 部署完成 ==="
echo ""
echo "服务状态:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo "停止服务: docker-compose -f docker-compose.prod.yml down"

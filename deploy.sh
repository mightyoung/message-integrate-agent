#!/bin/bash
# ============================================================
# Message Integrate Agent - 一键部署脚本
# ============================================================
#
# 使用方法:
#   1. 将本目录所有文件上传到 NAS
#   2. 修改 .env.prod 中的配置
#   3. 运行: chmod +x deploy.sh && ./deploy.sh
#
# ============================================================

set -e

echo "=========================================="
echo "Message Integrate Agent - 一键部署"
echo "=========================================="

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

# 检查环境变量文件
if [ ! -f .env.prod ]; then
    echo "⚠️ .env.prod 不存在，复制模板..."
    cp .env.prod.example .env.prod
    echo "⚠️ 请修改 .env.prod 中的配置后重新运行"
    exit 1
fi

echo "✅ 环境检查通过"

# 停止旧容器
echo "停止旧容器..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# 构建镜像
echo "构建镜像..."
docker-compose -f docker-compose.prod.yml build

# 启动服务
echo "启动服务..."
docker-compose -f docker-compose.prod.yml up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查状态
echo "检查服务状态..."
docker-compose -f docker-compose.prod.yml ps

# 检查健康状态
echo "检查健康状态..."
sleep 5
curl -sf http://localhost:8080/health > /dev/null 2>&1 && echo "✅ Gateway 健康检查通过" || echo "⚠️ Gateway 健康检查失败"

echo ""
echo "=========================================="
echo "部署完成!"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  - HTTP:  http://localhost:8080"
echo "  - WebSocket: ws://localhost:8081"
echo ""
echo "常用命令:"
echo "  - 查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo "  - 停止服务: docker-compose -f docker-compose.prod.yml down"
echo "  - 重启服务: docker-compose -f docker-compose.prod.yml restart"
echo ""

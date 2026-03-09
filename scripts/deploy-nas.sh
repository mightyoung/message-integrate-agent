#!/bin/bash
# ============================================================
# Message Integrate Agent - 快速部署脚本
# 用于 NAS Docker 环境
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_DIR="/volume1/docker/message-integrate-agent"
CONTAINER_NAME="message-hub-gateway"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Message Integrate Agent - 部署脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}提示: 建议使用 root 或 sudo 运行${NC}"
fi

# 检查目录
echo -e "${YELLOW}[1/6] 检查项目目录...${NC}"
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}错误: 项目目录不存在: $PROJECT_DIR${NC}"
    echo "请先创建目录并放入项目文件"
    exit 1
fi
cd "$PROJECT_DIR"
echo -e "${GREEN}✓ 项目目录: $PROJECT_DIR${NC}"

# 检查 .env 文件
echo -e "${YELLOW}[2/6] 检查配置文件...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "复制 .env.example 到 .env"
        cp .env.example .env
        echo -e "${RED}请先编辑 .env 文件配置必要的环境变量${NC}"
        exit 1
    else
        echo -e "${RED}错误: 缺少 .env 配置文件${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ 配置文件已存在${NC}"

# 检查 Docker
echo -e "${YELLOW}[3/6] 检查 Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    exit 1
fi
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: docker-compose 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 环境正常${NC}"

# 检查 NAS 服务
echo -e "${YELLOW}[4/6] 检查 NAS 服务...${NC}"
NAS_HOST="192.168.1.2"
SERVICES_OK=true

check_service() {
    local host=$1
    local port=$2
    local name=$3
    if nc -z -w3 "$host" "$port" 2>/dev/null; then
        echo -e "${GREEN}✓ $name ($host:$port)${NC}"
    else
        echo -e "${RED}✗ $name ($host:$port) - 无法连接${NC}"
        SERVICES_OK=false
    fi
}

check_service "$NAS_HOST" 45041 "PostgreSQL"
check_service "$NAS_HOST" 40967 "Redis"
check_service "$NAS_HOST" 37163 "S3 Storage"
check_service "$NAS_HOST" 7890  "mihomo (代理)"

if [ "$SERVICES_OK" = false ]; then
    echo -e "${YELLOW}警告: 部分 NAS 服务不可用，是否继续? (y/n)${NC}"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

# 构建镜像
echo -e "${YELLOW}[5/6] 构建 Docker 镜像...${NC}"
docker-compose build --no-cache

# 启动服务
echo -e "${YELLOW}[6/6] 启动服务...${NC}"
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查状态
if docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${GREEN}✓ 服务启动成功${NC}"

    # 健康检查
    echo "执行健康检查..."
    sleep 5
    if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 健康检查通过${NC}"
    else
        echo -e "${YELLOW}⚠ 健康检查未通过，查看日志:${NC}"
        docker-compose logs --tail=20
    fi
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    docker-compose logs --tail=50
    exit 1
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  部署完成!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "访问地址:"
echo "  - Gateway: http://<NAS-IP>:8080"
echo "  - WebSocket: ws://<NAS-IP>:8081"
echo "  - Health: http://<NAS-IP>:8080/health"
echo ""
echo "常用命令:"
echo "  查看日志: docker-compose logs -f"
echo "  重启服务: docker-compose restart"
echo "  停止服务: docker-compose down"
echo ""

#!/bin/bash
# ============================================================
# Message Integrate Agent - 一键启动脚本
# 用法: ./scripts/start.sh
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Message Integrate Agent 启动器${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}警告: .env 文件不存在，正在创建...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}请编辑 .env 文件并配置 NGROK_AUTHTOKEN${NC}"
        exit 1
    else
        echo -e "${RED}错误: 缺少 .env 文件${NC}"
        exit 1
    fi
fi

# 检查 NGROK_AUTHTOKEN
if [ -z "$NGROK_AUTHTOKEN" ]; then
    # 尝试从 .env 加载
    export $(grep -v '^#' .env | xargs) 2>/dev/null || true
fi

if [ -z "$NGROK_AUTHTOKEN" ]; then
    echo -e "${RED}错误: 请在 .env 中配置 NGROK_AUTHTOKEN${NC}"
    exit 1
fi

# ============================================================
# 修复权限问题
# ============================================================
echo -e "${GREEN}[修复权限] 创建日志目录...${NC}"

# 创建必要的目录
mkdir -p logs
mkdir -p .learnings

# 创建 app.log 文件并设置权限
touch logs/app.log
touch logs/webhook.log

# 设置权限为 777 (容器内 appuser 用户需要写入)
chmod -R 777 logs 2>/dev/null || true
chmod -R 777 .learnings 2>/dev/null || true

echo -e "${GREEN}[1/3] 构建 Docker 镜像...${NC}"
docker-compose build

echo -e "${GREEN}[2/3] 启动服务 (Gateway + ngrok)...${NC}"
docker-compose up -d

echo -e "${GREEN}[3/3] 等待服务启动...${NC}"
sleep 10

# 获取 ngrok URL
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  服务状态${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 gateway
if docker-compose ps gateway | grep -q "Up"; then
    echo -e "${GREEN}✓ Gateway 运行中 (本地: localhost:8080)${NC}"
else
    echo -e "${RED}✗ Gateway 未运行${NC}"
    echo -e "${YELLOW}查看日志: docker-compose logs gateway${NC}"
fi

# 检查 ngrok
if docker-compose ps ngrok | grep -q "Up"; then
    echo -e "${GREEN}✓ ngrok 运行中${NC}"

    # 等待隧道建立
    echo -e "${YELLOW}等待隧道建立...${NC}"
    for i in {1..30}; do
        TUNNEL_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4 || echo "")
        if [ -n "$TUNNEL_URL" ]; then
            break
        fi
        sleep 2
    done

    if [ -n "$TUNNEL_URL" ]; then
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  公网 URL (用于飞书配置)${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}Webhook URL: ${YELLOW}${TUNNEL_URL}/webhook/feishu${NC}"
        echo -e "${GREEN}ngrok Dashboard: ${YELLOW}http://<你的NAS-IP>:4040${NC}"
        echo ""
    else
        echo -e "${YELLOW}⚠ 隧道建立中，请稍后查看: docker-compose logs ngrok${NC}"
    fi
else
    echo -e "${RED}✗ ngrok 未运行"
    echo -e "${YELLOW}查看日志: docker-compose logs ngrok${NC}"
fi

echo ""
echo -e "${GREEN}常用命令:${NC}"
echo "  查看日志:   docker-compose logs -f"
echo "  停止服务:   docker-compose down"
echo "  重启服务:   docker-compose restart"
echo "  查看状态:   docker-compose ps"

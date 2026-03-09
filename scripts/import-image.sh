#!/bin/bash
# ============================================================
# Docker Image Import Script
# 从 tar 文件导入 Docker 镜像
# ============================================================
#
# 使用方法:
#   ./scripts/import-image.sh [tar_file]
#
# 示例:
#   ./scripts/import-image.sh
#   ./scripts/import-image.sh ./message-hub-prod.tar
#
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TAR_FILE="${1:-.}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Docker Image Import${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 如果没有指定文件，查找最新的 tar 文件
if [ "$TAR_FILE" = "." ]; then
    TAR_FILE=$(ls -t message-hub*.tar 2>/dev/null | head -1)
    if [ -z "$TAR_FILE" ]; then
        echo -e "${RED}错误: 未找到 message-hub*.tar 文件${NC}"
        echo "请指定 tar 文件路径"
        exit 1
    fi
fi

# 检查文件是否存在
if [ ! -f "$TAR_FILE" ]; then
    echo -e "${RED}错误: 文件不存在: $TAR_FILE${NC}"
    exit 1
fi

echo "导入文件: $TAR_FILE"
FILE_SIZE=$(du -h "$TAR_FILE" | cut -f1)
echo "文件大小: $FILE_SIZE"
echo ""

# 导入镜像
echo -e "${YELLOW}导入镜像中...${NC}"
docker load -i "$TAR_FILE"

echo ""
echo -e "${GREEN}✓ 镜像导入成功${NC}"
echo ""

# 显示已导入的镜像
echo "已导入的镜像:"
docker images | grep message-integrate-agent || echo "  (未找到 message-integrate-agent 镜像)"
echo ""

# 验证
echo -e "${YELLOW}验证镜像...${NC}"
if docker image inspect message-integrate-agent:prod > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 镜像验证成功${NC}"
else
    echo -e "${YELLOW}⚠ 镜像验证: 未找到 message-integrate-agent:prod${NC}"
    echo "请检查镜像标签"
    docker images
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  导入完成!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "下一步:"
echo "  1. cp .env.prod.example .env.prod && nano .env.prod"
echo "  2. docker-compose -f docker-compose.prod.yml up -d"

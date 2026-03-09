#!/bin/bash
# ============================================================
# Docker 镜像构建和导出脚本
# 构建所有镜像并导出为 tar 文件（不进行网络拉取）
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

OUTPUT_DIR="docker-images"
VERSION="${VERSION:-$(date +%Y%m%d)}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Docker 镜像构建和导出${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# ============================================================
# 1. 构建 message-integrate-agent 镜像
# ============================================================
echo -e "${YELLOW}[1/4] 构建 message-integrate-agent 镜像...${NC}"
docker build -f Dockerfile.prod -t message-integrate-agent:prod .

echo -e "${YELLOW}导出镜像...${NC}"
docker save -o "$OUTPUT_DIR/message-integrate-agent-prod.tar" message-integrate-agent:prod
echo -e "${GREEN}✓ message-integrate-agent 导出完成${NC}"
echo ""

# ============================================================
# 2. 构建 bettafish 镜像
# ============================================================
echo -e "${YELLOW}[2/4] 构建 bettafish 镜像...${NC}"
docker build -t bettafish:latest -f bettafish/Dockerfile bettafish/

echo -e "${YELLOW}导出镜像...${NC}"
docker save -o "$OUTPUT_DIR/bettafish-latest.tar" bettafish:latest
echo -e "${GREEN}✓ bettafish 导出完成${NC}"
echo ""

# ============================================================
# 3. 构建 mirofish 镜像
# ============================================================
echo -e "${YELLOW}[3/4] 构建 mirofish 镜像...${NC}"
docker build -t mirofish:latest -f mirofish/Dockerfile mirofish/

echo -e "${YELLOW}导出镜像...${NC}"
docker save -o "$OUTPUT_DIR/mirofish-latest.tar" mirofish:latest
echo -e "${GREEN}✓ mirofish 导出完成${NC}"
echo ""

# ============================================================
# 4. 显示结果
# ============================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  镜像构建和导出完成!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "导出目录: $OUTPUT_DIR/"
echo ""
ls -lh "$OUTPUT_DIR"/*.tar
echo ""

# 计算总大小
TOTAL_SIZE=$(du -sh "$OUTPUT_DIR" | cut -f1)
echo "总大小: $TOTAL_SIZE"
echo ""

echo "复制到 NAS:"
echo "  scp -r $OUTPUT_DIR user@nas:/volume1/docker/"
echo ""
echo "在 NAS 上导入:"
echo "  cd /volume1/docker/$OUTPUT_DIR"
echo "  docker load -i message-integrate-agent-prod.tar"
echo "  docker load -i bettafish-latest.tar"
echo "  docker load -i mirofish-latest.tar"
echo ""
echo "然后启动服务:"
echo "  docker-compose -f docker-compose.prod.yml up -d"

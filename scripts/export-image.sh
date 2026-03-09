#!/bin/bash
# ============================================================
# Docker Image Export Script
# 将镜像导出为 tar 文件，方便传输到 NAS
# ============================================================
#
# 使用方法:
#   ./scripts/export-image.sh [image_name] [output_file]
#
# 示例:
#   ./scripts/export-image.sh
#   ./scripts/export-image.sh message-integrate-agent:prod
#   ./scripts/export-image.sh my-registry.com/message-integrate-agent:v1.0 ./message-hub.tar
#
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

IMAGE_NAME="${1:-message-integrate-agent:prod}"
OUTPUT_FILE="${2:-./message-hub-${IMAGE_NAME//\//-}.tar}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Docker Image Export${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "镜像: $IMAGE_NAME"
echo "输出: $OUTPUT_FILE"
echo ""

# 检查镜像是否存在
if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo -e "${YELLOW}镜像不存在，正在构建...${NC}"

    # 尝试使用 Dockerfile.prod 构建
    if [ -f "Dockerfile.prod" ]; then
        echo "使用 Dockerfile.prod 构建镜像..."
        docker build -f Dockerfile.prod -t "$IMAGE_NAME" .
    else
        echo -e "${RED}错误: Dockerfile.prod 不存在${NC}"
        exit 1
    fi
fi

# 导出镜像
echo -e "${YELLOW}导出镜像中...${NC}"
docker save -o "$OUTPUT_FILE" "$IMAGE_NAME"

# 显示文件大小
FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
echo -e "${GREEN}✓ 镜像已导出: $OUTPUT_FILE${NC}"
echo -e "${GREEN}✓ 文件大小: $FILE_SIZE${NC}"
echo ""

# 计算 SHA256 校验和
echo -e "${YELLOW}计算校验和...${NC}"
SHA256=$(sha256sum "$OUTPUT_FILE" | cut -d' ' -f1)
echo "SHA256: $SHA256"
echo ""

# 创建导入说明文件
cat > "${OUTPUT_FILE}.txt" << EOF
Docker Image Import Instructions
=================================

Image: $IMAGE_NAME
File: $(basename "$OUTPUT_FILE")
Size: $FILE_SIZE
SHA256: $SHA256

Import Command:
----------------
docker load -i $(basename "$OUTPUT_FILE")

Verify Command:
---------------
docker images | grep message-integrate-agent
docker run --rm message-integrate-agent:prod python -c "print('OK')"

Quick Start:
------------
1. Load: docker load -i $(basename "$OUTPUT_FILE")
2. Copy .env.prod.example to .env.prod and configure
3. Start: docker-compose -f docker-compose.prod.yml up -d
EOF

echo -e "${GREEN}✓ 导入说明已保存: ${OUTPUT_FILE}.txt${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  导出完成!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "传输到 NAS:"
echo "  scp $OUTPUT_FILE user@nas:/path/to/"
echo ""
echo "在 NAS 上导入:"
echo "  docker load -i $(basename "$OUTPUT_FILE")"
echo ""

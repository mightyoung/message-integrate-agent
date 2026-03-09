#!/bin/bash
# ============================================================
# 部署包生成脚本
# 生成可直接上传到 NAS 的文件
# ============================================================

set -e

VERSION="${VERSION:-$(date +%Y%m%d)}"
PACKAGE_DIR="message-hub-${VERSION}"

echo "创建部署目录: $PACKAGE_DIR"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/config"

# 复制必要文件
echo "复制配置文件..."

# Docker
cp docker-compose.prod.yml "$PACKAGE_DIR/"
cp Dockerfile.prod "$PACKAGE_DIR/"

# 环境变量
cp .env.prod "$PACKAGE_DIR/"

# 配置文件
cp -r config/* "$PACKAGE_DIR/config/"

# BettaFish
if [ -d "bettafish" ]; then
    cp -r bettafish "$PACKAGE_DIR/"
    echo "✓ 包含 BettaFish"
fi

# MiroFish
if [ -d "mirofish" ]; then
    cp -r mirofish "$PACKAGE_DIR/"
    echo "✓ 包含 MiroFish"
fi

# 部署说明
cp DEPLOY.md "$PACKAGE_DIR/"

# 显示文件列表
echo ""
echo "部署包内容:"
ls -la "$PACKAGE_DIR/"
echo ""

# 计算大小
du -sh "$PACKAGE_DIR"

echo ""
echo "✓ 部署包已创建: $PACKAGE_DIR/"
echo ""
echo "上传到 NAS 后执行:"
echo "  cd /volume1/docker/message-hub/"
echo "  docker-compose -f docker-compose.prod.yml build"
echo "  docker-compose -f docker-compose.prod.yml up -d"

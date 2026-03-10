#!/bin/bash
# ============================================================
# Message Integrate Agent - 打包部署文件
# ============================================================
#
# 使用方法:
#   ./package.sh
#
# 输出:
#   - message-hub-deploy.tar.gz (源代码 + 配置)
#
# ============================================================

set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_NAME="message-hub-deploy"

echo "=========================================="
echo "打包部署文件"
echo "=========================================="

# 创建临时目录
TEMP_DIR=$(mktemp -d)
echo "临时目录: $TEMP_DIR"

# 复制必要文件
echo "复制文件..."
mkdir -p $TEMP_DIR/$PACKAGE_NAME

# 核心文件
cp $BASE_DIR/Dockerfile.prod $TEMP_DIR/$PACKAGE_NAME/
cp $BASE_DIR/docker-compose.prod.yml $TEMP_DIR/$PACKAGE_NAME/
cp $BASE_DIR/deploy.sh $TEMP_DIR/$PACKAGE_NAME/
cp $BASE_DIR/requirements.txt $TEMP_DIR/$PACKAGE_NAME/
cp $BASE_DIR/.env.prod $TEMP_DIR/$PACKAGE_NAME/
cp $BASE_DIR/DEPLOY.md $TEMP_DIR/$PACKAGE_NAME/
cp $BASE_DIR/README-DEPLOY.md $TEMP_DIR/$PACKAGE_NAME/

# 复制 src 目录（排除 __pycache__）
echo "复制源代码..."
cp -r $BASE_DIR/src $TEMP_DIR/$PACKAGE_NAME/

# 复制 config 目录
echo "复制配置..."
cp -r $BASE_DIR/config $TEMP_DIR/$PACKAGE_NAME/

# 创建必要目录
echo "创建目录结构..."
mkdir -p $TEMP_DIR/$PACKAGE_NAME/logs
mkdir -p $TEMP_DIR/$PACKAGE_NAME/.learnings

# 设置脚本权限
chmod +x $TEMP_DIR/$PACKAGE_NAME/deploy.sh

# 打包源代码
echo "打包源代码..."
tar -czvf $BASE_DIR/${PACKAGE_NAME}.tar.gz -C $TEMP_DIR $PACKAGE_NAME

# 清理临时目录
rm -rf $TEMP_DIR

echo ""
echo "=========================================="
echo "打包完成!"
echo "=========================================="
echo ""
echo "输出文件:"
echo "  - ${PACKAGE_NAME}.tar.gz (源代码 + 配置)"
echo ""
echo "部署步骤:"
echo "  1. 解压: tar -xzvf ${PACKAGE_NAME}.tar.gz"
echo "  2. 进入目录: cd $PACKAGE_NAME"
echo "  3. 构建镜像: docker build -f Dockerfile.prod -t message-integrate-agent:prod ."
echo "  4. 启动服务: docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "注意: .env.prod 已包含所有配置，请根据需要修改"
echo ""

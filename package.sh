#!/bin/bash
# ============================================================
# Message Integrate Agent - 打包部署文件
# ============================================================
#
# 使用方法:
#   ./package.sh
#
# 输出: message-hub-deploy.tar.gz
#
# ============================================================

set -e

echo "=========================================="
echo "打包部署文件"
echo "=========================================="

# 打包文件名
PACKAGE_NAME="message-hub-deploy"

# 创建临时目录
TEMP_DIR=$(mktemp -d)
echo "临时目录: $TEMP_DIR"

# 复制必要文件
echo "复制文件..."
mkdir -p $TEMP_DIR/$PACKAGE_NAME

# 核心文件
cp -r Dockerfile.prod $TEMP_DIR/$PACKAGE_NAME/
cp -r docker-compose.prod.yml $TEMP_DIR/$PACKAGE_NAME/
cp -r deploy.sh $TEMP_DIR/$PACKAGE_NAME/
cp -r requirements.txt $TEMP_DIR/$PACKAGE_NAME/
cp -r .env.prod.example $TEMP_DIR/$PACKAGE_NAME/
cp -r DEPLOY.md $TEMP_DIR/$PACKAGE_NAME/
cp -r README-DEPLOY.md $TEMP_DIR/$PACKAGE_NAME/

# 复制 src 目录（排除 __pycache__）
echo "复制源代码..."
mkdir -p $TEMP_DIR/$PACKAGE_NAME/src
rsync -av --exclude='__pycache__' --exclude='*.pyc' src/ $TEMP_DIR/$PACKAGE_NAME/src/

# 复制 config 目录
echo "复制配置..."
cp -r config $TEMP_DIR/$PACKAGE_NAME/

# 创建必要目录
echo "创建目录结构..."
cd $TEMP_DIR/$PACKAGE_NAME
mkdir -p logs
mkdir -p .learnings

# 设置脚本权限
chmod +x deploy.sh

# 打包
echo "打包..."
cd $TEMP_DIR
tar -czvf ${PACKAGE_NAME}.tar.gz $PACKAGE_NAME

# 移动到当前目录
mv ${PACKAGE_NAME}.tar.gz ./

# 清理临时目录
rm -rf $TEMP_DIR

echo ""
echo "=========================================="
echo "打包完成!"
echo "=========================================="
echo ""
echo "输出文件: ${PACKAGE_NAME}.tar.gz"
echo ""
echo "部署步骤:"
echo "  1. 解压: tar -xzvf ${PACKAGE_NAME}.tar.gz"
echo "  2. 进入目录: cd $PACKAGE_NAME"
echo "  3. 复制配置: cp .env.prod.example .env.prod"
echo "  4. 修改配置: nano .env.prod"
echo "  5. 启动服务: docker-compose -f docker-compose.prod.yml up -d"
echo ""

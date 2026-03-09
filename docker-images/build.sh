# ============================================================
# Message Integrate Agent - 镜像构建脚本
# ============================================================
#
# 使用方式:
#   1. cd docker-images
#   2. chmod +x build.sh && ./build.sh
#
# ============================================================

set -e

echo "=== Message Hub 镜像构建脚本 ==="
echo ""

# 构建 message-integrate-agent 镜像
echo "=== 1. 构建 message-integrate-agent:prod ==="
cd ..
docker build -f Dockerfile.prod -t message-integrate-agent:prod .
echo "✓ 构建完成"
echo ""

# 导出镜像
echo "=== 2. 导出 message-integrate-agent:prod ==="
cd docker-images
docker save -o message-integrate-agent-prod.tar message-integrate-agent:prod
echo "✓ 导出完成: message-integrate-agent-prod.tar"
echo ""

# 拉取 clash 镜像
echo "=== 3. 拉取 dreamacro/clash:latest ==="
docker pull dreamacro/clash:latest
docker save -o clash-latest.tar dreamacro/clash:latest
echo "✓ 导出完成: clash-latest.tar"
echo ""

# 拉取/构建 bettafish
echo "=== 4. 处理 bettafish:latest ==="
if [ -d "../bettafish" ]; then
    cd ../bettafish
    docker build -t bettafish:latest .
    cd ../docker-images
    docker save -o bettafish-latest.tar bettafish:latest
    echo "✓ 导出完成: bettafish-latest.tar"
else
    echo "⚠️ bettafish 目录不存在，跳过"
fi
echo ""

# 拉取/构建 mirofish
echo "=== 5. 处理 mirofish:latest ==="
if [ -d "../mirofish" ]; then
    cd ../mirofish
    docker build -t mirofish:latest .
    cd ../docker-images
    docker save -o mirofish-latest.tar mirofish:latest
    echo "✓ 导出完成: mirofish-latest.tar"
else
    echo "⚠️ mirofish 目录不存在，跳过"
fi
echo ""

echo "=== 构建完成 ==="
echo ""
echo "生成的文件:"
ls -lh *.tar
echo ""
echo "下一步: 运行 ./deploy.sh 部署到 NAS"

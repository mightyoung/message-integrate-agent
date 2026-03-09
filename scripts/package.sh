#!/bin/bash
# ============================================================
# Deployment Package Script
# 将所有部署文件打包为可分发的压缩包
# ============================================================
#
# 使用方法:
#   ./scripts/package.sh
#
# 输出:
#   message-hub-deploy-{version}.tar.gz
#
# 包含:
#   - docker-compose.prod.yml
#   - Dockerfile.prod
#   - .env.prod.example
#   - config/
#   - 部署脚本
#
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 版本号
VERSION="${VERSION:-$(date +%Y%m%d)}"
PACKAGE_NAME="message-hub-deploy-${VERSION}"
OUTPUT_DIR="./deploy-package"
TAR_FILE="${PACKAGE_NAME}.tar.gz"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deployment Package Creator${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 创建临时目录
echo -e "${YELLOW}创建部署包...${NC}"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# 复制必要文件
echo "复制配置文件..."

# Docker 相关
cp docker-compose.prod.yml "$OUTPUT_DIR/"
cp Dockerfile.prod "$OUTPUT_DIR/"

# 使用实际的 .env.prod (包含真实配置)
if [ -f ".env.prod" ]; then
    cp .env.prod "$OUTPUT_DIR/.env.prod"
    echo "✓ 已包含 .env.prod (真实配置)"
elif [ -f ".env.prod.example" ]; then
    cp .env.prod.example "$OUTPUT_DIR/"
    echo "✓ 已包含 .env.prod.example (模板)"
fi

# 配置文件
cp -r config "$OUTPUT_DIR/"

# 部署脚本
mkdir -p "$OUTPUT_DIR/scripts"
cp scripts/import-image.sh "$OUTPUT_DIR/scripts/"
cp scripts/deploy-nas.sh "$OUTPUT_DIR/scripts/"

# 创建部署说明
cat > "$OUTPUT_DIR/README.md" << 'EOF'
# Message Integrate Agent - 部署包

## 快速部署指南

### 前置要求
- NAS 上已安装 Docker + Docker Compose
- NAS 上已运行: PostgreSQL, Redis, S3/RustFs, mihomo

### 部署步骤

#### 1. 导入 Docker 镜像
```bash
# 方法 A: 从 tar 文件导入 (推荐)
docker load -i message-hub-deploy-{version}.tar.gz

# 方法 B: 直接构建
docker build -f Dockerfile.prod -t message-integrate-agent:prod .
```

#### 2. 环境变量 (已包含真实配置)
```bash
# .env.prod 已包含真实配置，如需修改:
nano .env.prod
```

#### 3. 启动服务
```bash
# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

#### 4. 验证部署
```bash
# 健康检查
curl http://localhost:8080/health

# 查看容器状态
docker-compose -f docker-compose.prod.yml ps
```

## 端口说明

| 端口 | 服务 |
|------|------|
| 8080 | Gateway HTTP |
| 8081 | WebSocket |
| 4040 | ngrok Dashboard |

## 常见问题

### 无法连接数据库
- 检查 .env.prod 中的 PG_HOST, PG_PORT 配置
- 检查 NAS 防火墙是否开放端口

### 服务启动失败
- 查看日志: docker-compose logs gateway
- 检查 .env.prod 配置是否正确

## 文件结构

```
message-hub-deploy-{version}/
├── docker-compose.prod.yml  # 生产环境 compose
├── Dockerfile.prod           # 生产环境 Dockerfile
├── .env.prod.example        # 环境变量模板
├── config/                 # 配置文件
├── scripts/
│   ├── import-image.sh    # 镜像导入脚本
│   └── deploy-nas.sh      # NAS 部署脚本
└── README.md              # 本说明
```
EOF

# 创建一键部署脚本
cat > "$OUTPUT_DIR/deploy.sh" << 'DEPLOY_SCRIPT'
#!/bin/bash
# ============================================================
# 一键部署脚本
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Message Hub - 一键部署${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: docker-compose 未安装${NC}"
    exit 1
fi

# 检查镜像
if ! docker image inspect message-integrate-agent:prod &> /dev/null; then
    echo -e "${YELLOW}镜像不存在，正在导入...${NC}"

    # 查找 tar 文件
    TAR_FILE=$(ls message-hub-deploy*.tar.gz 2>/dev/null | head -1)
    if [ -z "$TAR_FILE" ]; then
        echo -e "${RED}错误: 未找到部署包${NC}"
        exit 1
    fi

    # 解压 (如果需要)
    if [[ "$TAR_FILE" == *.tar.gz ]]; then
        echo "解压部署包..."
        tar -xzf "$TAR_FILE"
        TAR_FILE=$(ls message-hub-deploy*/message-hub*.tar.gz 2>/dev/null | head -1)
    fi

    # 导入镜像
    if [ -n "$TAR_FILE" ] && [ -f "$TAR_FILE" ]; then
        docker load -i "$TAR_FILE"
    fi
fi

# 配置环境变量
if [ ! -f ".env.prod" ]; then
    if [ -f ".env.prod.example" ]; then
        echo -e "${YELLOW}复制环境变量配置...${NC}"
        cp .env.prod.example .env.prod
        echo -e "${RED}请先编辑 .env.prod 配置必要的环境变量${NC}"
        exit 1
    fi
fi

# 启动服务
echo -e "${YELLOW}启动服务...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# 等待启动
echo "等待服务启动..."
sleep 10

# 检查状态
if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 部署成功!${NC}"
    echo ""
    echo "访问地址:"
    echo "  - Gateway: http://<NAS-IP>:8080"
    echo "  - Health: http://<NAS-IP>:8080/health"
else
    echo -e "${YELLOW}⚠ 服务可能还在启动，查看日志:${NC}"
    docker-compose -f docker-compose.prod.yml logs --tail=20
fi
DEPLOY_SCRIPT

chmod +x "$OUTPUT_DIR/deploy.sh"

# 打包
echo -e "${YELLOW}打包中...${NC}"
cd "$OUTPUT_DIR"
tar -czf "../$TAR_FILE" ./*
cd ..

# 清理临时目录
rm -rf "$OUTPUT_DIR"

# 显示结果
FILE_SIZE=$(du -h "$TAR_FILE" | cut -f1)
echo ""
echo -e "${GREEN}✓ 部署包已创建: $TAR_FILE${NC}"
echo -e "${GREEN}✓ 文件大小: $FILE_SIZE${NC}"
echo ""

# 列出包内容
echo "包含文件:"
tar -tzf "$TAR_FILE" | head -20

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  打包完成!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "分发到 NAS:"
echo "  scp $TAR_FILE user@nas:/volume1/docker/"
echo ""
echo "在 NAS 上部署:"
echo "  1. 解压: tar -xzf $TAR_FILE"
echo "  2. 配置: nano .env.prod  (已包含配置)"
echo "  3. 部署: ./deploy.sh"

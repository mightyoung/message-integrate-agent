# Message Integrate Agent - 快速部署

## 环境要求

- Docker
- Docker Compose
- NAS 存储服务（PostgreSQL, Redis, RustFs）

## 快速开始

### 1. 解压部署包

```bash
tar -xzvf message-hub-deploy.tar.gz
cd message-hub-deploy
```

### 2. 配置环境变量

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

### 3. 启动服务

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 验证

```bash
# 健康检查
curl http://localhost:8080/health
```

## 功能

- 飞书 WebSocket 长连接
- 定时推送情报（学术论文、GitHub、Science）
- LLM 中文内容生成

## 详细文档

见 [DEPLOY.md](./DEPLOY.md)

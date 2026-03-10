# ============================================================
# Message Integrate Agent - Docker 部署手册
# ============================================================

## 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAS Docker Network                        │
│                                                                 │
│  ┌──────────────┐                                             │
│  │   gateway    │  飞书 WebSocket 长连接                       │
│  │   :8080      │  定时推送情报 (学术论文/GitHub/Science)     │
│  └──────────────┘                                             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
   飞书服务器
   (wss://msg-frontisonar.door.feishu.cn)

┌─────────────────────────────────────────────────────────────────┐
│                        NAS 存储服务                              │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PostgreSQL    │  │    Redis     │  │   RustFs     │     │
│  │   :45041      │  │    :40967    │  │   :37163     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## 方式一：使用 Docker 镜像（推荐）

### 步骤 1: 导入镜像

将 `message-integrate-agent-prod.tar` 文件上传到 NAS，然后执行：

```bash
# 导入镜像
docker load -i message-integrate-agent-prod.tar

# 验证镜像
docker images | grep message-integrate-agent
```

### 步骤 2: 配置环境变量

```bash
# 复制环境变量模板
cp .env.prod.example .env.prod

# 编辑配置
nano .env.prod
```

需要配置的关键变量：

```bash
# 飞书配置
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_WEBHOOK_URL=your_webhook_url
FEISHU_CONNECTION_MODE=websocket

# LLM 配置
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Firecrawl 配置
FIRECRAWL_API_KEY=fc-xxxxx

# NAS 存储
DATABASE_URL=postgresql://postgres:postgres@192.168.1.2:45041/bs_generator_db
REDIS_HOST=192.168.1.2
REDIS_PORT=40967
S3_ENDPOINT_URL=http://192.168.1.2:37163
```

### 步骤 3: 启动服务

```bash
# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

## 方式二：构建镜像

### 步骤 1: 在 NAS 上构建

```bash
# 构建镜像
docker build -f Dockerfile.prod -t message-integrate-agent:prod .

# 导出镜像（可选）
docker save message-integrate-agent:prod > message-integrate-agent-prod.tar
```

### 步骤 2: 启动服务

同方式一的步骤 2 和步骤 3

## 端口说明

| 端口 | 服务 |
|------|------|
| 8080 | Gateway HTTP |
| 8081 | WebSocket |

## 定时任务配置

在 `.env.prod` 中配置：

```bash
# 学术论文推送（每天 9:00）
INTELLIGENCE_CRON_ACADEMIC=0 9 * * *

# GitHub Trending 推送（每天 10:00）
INTELLIGENCE_CRON_GITHUB=0 10 * * *

# Science 热点推送（每天 11:00）
INTELLIGENCE_CRON_SCIENCE=0 11 * * *

# SciRobotics 推送（每天 11:30）
INTELLIGENCE_CRON_SCIROBOTICS=0 11 30 * * *
```

## 手动触发推送

```bash
# 学术论文推送
curl -X POST http://localhost:8080/api/intelligence/push/academic

# GitHub Trending
curl -X POST http://localhost:8080/api/intelligence/push/github

# Science 热点
curl -X POST http://localhost:8080/api/intelligence/push/science

# SciRobotics
curl -X POST http://localhost:8080/api/intelligence/push/scirobotics
```

## 常用命令

```bash
# 启动
docker-compose -f docker-compose.prod.yml start

# 停止
docker-compose -f docker-compose.prod.yml stop

# 重启
docker-compose -f docker-compose.prod.yml restart

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f gateway

# 进入容器
docker exec -it message-hub-gateway /bin/bash
```

## 验证

```bash
# 健康检查
curl http://localhost:8080/health

# 查看飞书连接状态
curl http://localhost:8080/api/status
```

## 常见问题

### Q: 无法连接飞书
A: 检查网络连接和 FEISHU 配置是否正确

### Q: 情报推送失败
A: 检查 FIRECRAWL_API_KEY 和 DEEPSEEK_API_KEY 配置

### Q: Science 抓取失败
A: Firecrawl 可能被限流，检查 API 配额

## 目录结构

```
message-hub-deploy/
├── Dockerfile.prod          # Docker 镜像构建
├── docker-compose.prod.yml # Docker Compose 配置
├── .env.prod.example      # 环境变量模板
├── config/               # 配置文件
│   └── settings.yaml
└── DEPLOY.md             # 本文档
```

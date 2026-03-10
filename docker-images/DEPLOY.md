# ============================================================
# Message Integrate Agent - 一键部署说明
# ============================================================

## 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAS Docker Network                        │
│                                                                 │
│  ┌──────────────┐                                               │
│  │   gateway    │                                               │
│  │(Feishu WS)  │                                               │
│  │   :8080      │                                               │
│  └──────────────┘                                               │
│         │                                                        │
│         │  飞书长连接 (WebSocket)                               │
│         └─────────────────────────────────────────────────────▶   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
   飞书服务器
   (wss://msg-frontier.feishu.cn)

┌─────────────────────────────────────────────────────────────────┐
│                        NAS 存储服务                             │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PostgreSQL    │  │    Redis     │  │   RustFs     │     │
│  │   :45041      │  │    :40967    │  │   :37163     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## 新增功能 (v2.0)

### 情报推送功能

| 功能 | 说明 | 触发方式 |
|------|------|----------|
| 学术论文 | 从 arXiv 获取最新 AI 相关论文 | 定时任务 |
| GitHub Trending | 获取热门开源项目 | 定时任务 |
| Science 热点 | 从 Science.org 抓取热点研究 | 定时任务 |
| SciRobotics | 机器人领域热点 | 定时任务 |

### LLM 内容生成

- **学术论文风格**: 顶级科学家思维（精准、简洁、包含核心发现）
- **GitHub 仓库风格**: 顶级开源工程师思维（实用、创新、可扩展）
- **新闻标题风格**: 顶级新闻编辑思维（简洁有力、倒金字塔结构）

## 上传到 NAS 的文件

将以下文件上传到 NAS 的 `/volume1/docker/message-hub/` 目录：

```
message-hub/
├── docker-compose.prod.yml    # 部署配置
├── Dockerfile.prod            # 镜像构建
├── .env.prod                 # 环境变量
├── config/                   # 配置目录
│   └── settings.yaml
└── DEPLOY.md                # 说明
```

## 环境变量配置

参考 `.env.prod.example` 配置以下环境变量：

```bash
# ==================== LLM 配置 ====================
DEEPSEEK_API_KEY=sk-xxxxx          # DeepSeek API Key

# ==================== Firecrawl 配置 ====================
FIRECRAWL_API_KEY=fc-xxxxx         # Firecrawl API Key

# ==================== NAS 存储配置 ====================
# PostgreSQL (NAS)
DATABASE_URL=postgresql://postgres:postgres@192.168.1.2:45041/bs_generator_db

# Redis (NAS)
REDIS_HOST=192.168.1.2
REDIS_PORT=40967

# RustFs S3 (NAS)
S3_ENDPOINT_URL=http://192.168.1.2:37163
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key

# ==================== 定时任务配置 ====================
INTELLIGENCE_CRON_ACADEMIC=0 9 * * *
INTELLIGENCE_CRON_GITHUB=0 10 * * *
INTELLIGENCE_CRON_SCIENCE=0 11 * * *
INTELLIGENCE_CRON_SCIROBOTICS=0 11 30 * * *
```

## NAS 上执行

### 1. 构建并启动服务

```bash
cd /volume1/docker/message-hub/
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 2. 验证

```bash
curl http://localhost:8080/health
docker-compose -f docker-compose.prod.yml logs -f
```

## 端口说明

| 端口 | 服务 |
|------|------|
| 8080 | Gateway HTTP |
| 8081 | WebSocket |

## NAS 存储服务

| 服务 | 地址 | 端口 |
|------|------|------|
| PostgreSQL | 192.168.1.2 | 45041 |
| Redis | 192.168.1.2 | 40967 |
| RustFs S3 | 192.168.1.2 | 37163 |

## 常用命令

```bash
# 启动/停止/重启
docker-compose -f docker-compose.prod.yml start|stop|restart

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f gateway

# 进入容器
docker exec -it message-hub-gateway /bin/bash
```

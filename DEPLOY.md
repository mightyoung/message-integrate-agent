# ============================================================
# Message Integrate Agent - 一键部署说明
# ============================================================

## 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAS Docker Network                        │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐                         │
│  │   gateway    │    │   mihomo     │                         │
│  │(Feishu WS)  │───▶│  (代理服务)  │                         │
│  │   :8080      │    │  :7890       │                         │
│  └──────────────┘    └──────────────┘                         │
│         │                    │                                  │
│         │            ┌──────▼──────┐                          │
│         │            │  bettafish  │  舆情分析               │
│         │            │   :5000     │                          │
│         │            └─────────────┘                          │
│         │                    │                                  │
│         │            ┌──────▼──────┐                          │
│         │            │  mirofish  │  预测分析               │
│         │            │   :5001     │                          │
│         │            └─────────────┘                          │
│         │                                                     │
│         │  飞书长连接 (WebSocket)                             │
│         └─────────────────────────────────────────────────────▶ │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
   飞书服务器
   (wss://msg-frontier.feishu.cn)
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
├── bettafish/               # 舆情分析服务
│   └── Dockerfile
├── mirofish/                # 预测分析服务
│   └── Dockerfile
├── config/                  # 配置目录
│   ├── clash/             # mihomo 配置
│   ├── proxy.yaml
│   └── settings.yaml
└── DEPLOY.md               # 说明
```

## 环境变量配置

新增以下环境变量（需要在 `.env.prod` 中配置）：

```bash
# ==================== LLM 配置 ====================
DEEPSEEK_API_KEY=sk-xxxxx          # DeepSeek API Key（用于生成中文标题/概要）

# ==================== Firecrawl 配置 ====================
FIRECRAWL_API_KEY=fc-xxxxx         # Firecrawl API Key（用于抓取 Science.org）

# ==================== GitHub 配置（可选）===============
GITHUB_TOKEN=ghp_xxxxx             # GitHub Token（提高 API 限流）

# ==================== 定时任务配置 ====================
# 学术论文推送（每天 9:00）
INTELLIGENCE_CRON_ACADEMIC=0 9 * * *

# GitHub Trending 推送（每天 10:00）
INTELLIGENCE_CRON_GITHUB=0 10 * * *

# Science 热点推送（每天 11:00）
INTELLIGENCE_CRON_SCIENCE=0 11 * * *

# SciRobotics 推送（每天 11:30）
INTELLIGENCE_CRON_SCIROBOTICS=0 11 30 * * *
```

## NAS 上执行

### 1. 构建并启动所有服务

```bash
cd /volume1/docker/message-hub/

# 重新构建镜像（包含新增的 Firecrawl 和 Translator）
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 2. 验证

```bash
# 查看状态
docker-compose -f docker-compose.prod.yml ps

# 健康检查
curl http://localhost:8080/health

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

## 端口说明

| 端口 | 服务 |
|------|------|
| 8080 | Gateway HTTP |
| 8081 | WebSocket |
| 7890 | mihomo HTTP 代理 |
| 5000 | BettaFish API (舆情分析) |
| 5001 | MiroFish API (预测分析) |
| 3000 | MiroFish Web UI |

## 飞书配置

已配置为 **WebSocket 长连接**模式 (`FEISHU_CONNECTION_MODE=websocket`)

- WebSocket 连接到 `wss://msg-frontier.feishu.cn`
- 不需要公网 IP，客户端主动连接
- 通过 mihomo 代理访问非中国大陆 IP

## 代理规则 (mihomo)

已配置智能路由：
- **国内域名/IP**: 直连 (DIRECT)
- **海外域名/IP**: 代理 (PROXY)
- **飞书域名**: 直连

配置文件: `config/clash/config.yaml`

## API 调用

### 手动触发情报推送

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

### BettaFish 舆情分析

```bash
# 舆情分析
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI发展", "depth": "deep"}'
```

### MiroFish 预测分析

```bash
# 预测分析
curl -X POST http://localhost:5001/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"scenario": "科技发展", "steps": 10}'
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
docker-compose -f docker-compose.prod.yml logs -f bettafish
docker-compose -f docker-compose.prod.yml logs -f mirofish
docker-compose -f docker-compose.prod.yml logs -f mihomo

# 进入容器
docker exec -it message-hub-gateway /bin/bash
docker exec -it message-hub-bettafish /bin/bash
docker exec -it message-hub-mirofish /bin/bash
```

## 常见问题

### Q: 无法连接飞书
A: 检查 mihomo 是否正常运行: `docker-compose ps mihomo`

### Q: BettaFish/MiroFish 启动失败
A: 检查 DeepSeek API 配置是否正确: `docker-compose logs bettafish`

### Q: 代理无法访问
A: 检查 config/clash/config.yaml 中的代理节点是否有效

### Q: 情报推送失败
A: 检查 FIRECRAWL_API_KEY 和 DEEPSEEK_API_KEY 是否配置正确

### Q: Science 抓取失败
A: Firecrawl 可能被限流，检查 API 配额: `docker-compose logs gateway | grep Firecrawl`

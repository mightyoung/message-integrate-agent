# Message Integrate Agent | 消息通信中枢 Agent

<p align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</p>

> **English** | [中文](#中文)

---

## English

### Overview

Message Integrate Agent is an **AI-powered intelligent message hub** that connects to multiple messaging platforms (Telegram, Feishu/Lark, WeChat) with intelligent task routing, self-evolution capabilities, and enterprise-grade Docker deployment support.

Inspired by [OpenClaw](https://github.com/yoheinakajima/openclaw) and designed with production-grade architecture, it serves as a unified gateway for multi-platform message management with AI-driven automation.

### Key Features

#### 🔌 Multi-Platform Support
- **Telegram** - Bot API with webhook support
- **Feishu/Lark** - WebSocket long connection + webhook (enterprise-ready)
- **WeChat** - Webhook integration
- Unified message format across all platforms

#### 🧠 Intelligent Routing
- **Keyword Router** - Fast rule-based routing (<10ms)
- **AI Intent Router** - LLM-powered semantic understanding
- **Multi-level Pipeline** - Menu → Rules → Vector → LLM fallback

#### 🔄 Self-Evolution Engine (Heartbeat)
Inspired by OpenClaw's autonomous agent design:
- **Information Intake** - Tiered information gathering (Hot → RSS → Academic → Search)
- **Value Judgment** - AI-powered content quality scoring
- **Knowledge Output** - Structured learning storage
- **Social Maintenance** - Platform health monitoring
- **Self-Reflection** - Performance analysis and optimization

#### 📡 Intelligence Pipeline
- **Tier 1: Hot Trends** - Hacker News, GitHub Trending, Weibo (direct API, no proxy)
- **Tier 2: RSS Feeds** - 300+ curated sources (WorldMonitor-style)
- **Tier 3: Academic Papers** - arXiv, PubMed API
- **Tier 4: AI Search** - Tavily (as supplement only)

#### 🐳 Docker-Ready
- One-click NAS deployment
- Built-in proxy support (mihomo/Clash)
- Health checks and auto-restart
- Resource limits and security hardening

#### 🔧 MCP Integration
- Model Context Protocol for tool exposure
- Search, LLM, Weather tools readily available

#### 📊 Sentiment Analysis
- Sentiment analysis for stored intelligence
- Positive/Negative/Neutral classification
- LLM-powered deep analysis
- Usage: `analyze id=123456`

#### 🔮 Prediction Analysis
- Future trend prediction based on content
- Supports URL or text input
- Multi-dimensional scenario projection with probability assessment
- Usage: `predict https://news.example.com` or `predict AI technology trends`

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Layer                                │
│   Telegram    │    Feishu    │    WeChat    │   WebSocket    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Gateway Layer                               │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │   WebSocket │  │   Webhook   │  │  Message Pipeline │   │
│  │   Server    │  │   Handler   │  │  Router → Agent  │   │
│  └─────────────┘  └──────────────┘  └───────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Agent Pool  │  │  Agent Loop  │  │  MCP Server  │
│  (Fast Path)│  │ (Deep Think)│  │  (Tools)    │
└──────────────┘  └──────────────┘  └──────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Self-Evolution Layer                          │
│  Heartbeat Engine  │  Skills Loader  │  Self-Learning Router │
└─────────────────────────────────────────────────────────────────┘
```

### Quick Start

#### 1. Clone & Install

```bash
git clone https://github.com/mightyoung/message-integrate-agent.git
cd message-integrate-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys

# Required: OPENAI_API_KEY
# Optional: TELEGRAM_BOT_TOKEN, FEISHU_APP_ID, TAVILY_API_KEY, etc.
```

#### 3. Run

```bash
# Local development
python -m src.main

# Or use startup script
./start.sh
```

#### 4. Docker Deployment (Recommended for Production)

```bash
# Build Docker image
docker build -f Dockerfile.prod -t message-integrate-agent:prod .

# Deploy with docker-compose
cd docker-images
docker-compose -f docker-compose.prod.yml up -d
```

### Configuration

#### Environment Variables

| Variable | Required | Description |
|----------|:--------:|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key for LLM |
| `FEISHU_APP_ID` | - | Feishu app ID |
| `FEISHU_APP_SECRET` | - | Feishu app secret |
| `TELEGRAM_BOT_TOKEN` | - | Telegram bot token |
| `TAVILY_API_KEY` | - | Tavily search API key |
| `HTTP_PROXY` | - | HTTP proxy URL |
| `HTTPS_PROXY` | - | HTTPS proxy URL |

### Project Structure

```
message-integrate-agent/
├── src/
│   ├── adapters/          # Platform adapters (Telegram, Feishu, WeChat)
│   ├── agents/            # Agent pool and loop
│   ├── gateway/           # WebSocket gateway and routing
│   ├── heartbeat/         # Self-evolution engine
│   ├── intelligence/      # Intelligence pipeline (RSS, hot, papers)
│   ├── router/           # Intent routing
│   ├── skills/           # Dynamic skill loader
│   └── storage/          # Storage clients (Redis, PostgreSQL, S3)
├── docker-images/         # Docker deployment files
├── docs/                  # Architecture and design docs
├── tests/                 # Test suite
└── scripts/               # Deployment scripts
```

### License

MIT License - see [LICENSE](LICENSE) for details.

---

<a name="中文"></a>

## 中文

### 概述

**消息通信中枢 Agent** (Message Integrate Agent) 是一个 **AI 驱动的智能消息中枢**，连接多个消息平台（ Telegram、飞书、微信），具备智能任务路由、自我进化能力和企业级 Docker 部署支持。

设计参考 [OpenClaw](https://github.com/yoheinakajima/openclaw) 自主智能体架构，采用生产级架构设计，作为多平台消息管理的统一入口，实现 AI 驱动的自动化。

### 核心特性

#### 🔌 多平台支持
- **Telegram** - Bot API + Webhook
- **飞书/钉钉** - WebSocket 长连接 + Webhook（企业级）
- **微信** - Webhook 集成
- 统一消息格式

#### 🧠 智能路由
- **关键词路由** - 快速规则匹配 (<10ms)
- **AI 意图路由** - LLM 语义理解
- **多级管道** - 菜单 → 规则 → 向量 → LLM 兜底

#### 🔄 自我进化引擎 (Heartbeat)
参考 OpenClaw 自主智能体设计：
- **信息摄入** - 分层信息获取 (热榜 → RSS → 学术 → 搜索)
- **价值判断** - AI 内容质量评分
- **知识输出** - 结构化学习存储
- **社交维护** - 平台健康监控
- **自我反思** - 性能分析与优化

#### 📡 情报流水线
- **Tier 1: 热榜** - Hacker News、GitHub Trending、微博热搜 (直连 API，无需代理)
- **Tier 2: RSS 订阅** - 300+ 精选源 (类 WorldMonitor)
- **Tier 3: 学术论文** - arXiv、PubMed API
- **Tier 4: AI 搜索** - Tavily (仅补充)

#### 🐳 Docker 部署就绪
- 一键 NAS 部署
- 内置代理支持 (mihomo/Clash)
- 健康检查与自动重启
- 资源限制与安全加固

#### 🔧 MCP 集成
- Model Context Protocol 工具暴露
- 搜索、LLM、天气等工具开箱即用

#### 📊 舆情分析
- 对已存储情报进行情感分析
- 支持正向/负向/中性情感判断
- 使用 LLM 进行深度分析
- 使用方式: `分析 id=123456`

#### 🔮 预测分析
- 基于内容进行未来趋势预测
- 支持 URL 或文本输入
- 多维度情景推演与概率评估
- 使用方式: `预测 https://news.example.com` 或 `预测 某项技术的发展趋势`

### 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户层                                    │
│   Telegram    │    飞书    │    微信    │   WebSocket        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        网关层                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐      │
│  │  WebSocket │  │   Webhook   │  │  消息处理管道     │      │
│  │   服务器    │  │   处理器    │  │  路由 → Agent   │      │
│  └─────────────┘  └──────────────┘  └───────────────────┘      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Agent 池   │  │  Agent Loop  │  │  MCP Server  │
│  (快速路径) │  │  (深度思考)  │  │   (工具)     │
└──────────────┘  └──────────────┘  └──────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       自我进化层                                  │
│  Heartbeat 引擎  │  技能加载器  │  自学习路由                    │
└─────────────────────────────────────────────────────────────────┘
```

### 快速开始

#### 1. 克隆与安装

```bash
git clone https://github.com/mightyoung/message-integrate-agent.git
cd message-integrate-agent

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置

```bash
cp .env.example .env
# 编辑 .env 填写 API 密钥

# 必需: OPENAI_API_KEY
# 可选: TELEGRAM_BOT_TOKEN, FEISHU_APP_ID, TAVILY_API_KEY 等
```

#### 3. 运行

```bash
# 本地开发
python -m src.main

# 或使用启动脚本
./start.sh
```

#### 4. Docker 部署（生产环境推荐）

```bash
# 构建 Docker 镜像
docker build -f Dockerfile.prod -t message-integrate-agent:prod .

# 使用 docker-compose 部署
cd docker-images
docker-compose -f docker-compose.prod.yml up -d
```

### 配置说明

#### 环境变量

| 变量 | 必需 | 说明 |
|----------|:--------:|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API 密钥 |
| `FEISHU_APP_ID` | - | 飞书应用 ID |
| `FEISHU_APP_SECRET` | - | 飞书应用密钥 |
| `TELEGRAM_BOT_TOKEN` | - | Telegram Bot 令牌 |
| `TAVILY_API_KEY` | - | Tavily 搜索 API 密钥 |
| `HTTP_PROXY` | - | HTTP 代理地址 |
| `HTTPS_PROXY` | - | HTTPS 代理地址 |

### 项目结构

```
message-integrate-agent/
├── src/
│   ├── adapters/          # 平台适配器 (Telegram, 飞书, 微信)
│   ├── agents/            # Agent 池和循环
│   ├── gateway/          # WebSocket 网关和路由
│   ├── heartbeat/        # 自我进化引擎
│   ├── intelligence/     # 情报流水线 (RSS, 热榜, 论文)
│   ├── router/           # 意图路由
│   ├── skills/           # 动态技能加载器
│   └── storage/          # 存储客户端 (Redis, PostgreSQL, S3)
├── docker-images/         # Docker 部署文件
├── docs/                  # 架构和设计文档
├── tests/                 # 测试套件
└── scripts/               # 部署脚本
```

### License

MIT License - 详见 [LICENSE](LICENSE)

---

<p align="center">

**Star** ⭐ | **Fork** 🍴 | **Contribute** 🤝

</p>

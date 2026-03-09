# Architecture - 信息通信中枢 Agent

## 1. 系统架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户层 (User Layer)                                │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────┐ │
│   │  Telegram │    │   飞书   │    │  微信   │    │  WebSocket CLI  │ │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘    └────────┬─────────┘ │
└────────┼───────────────┼───────────────┼────────────────────┼─────────────┘
         │               │               │                    │
         └───────────────┴───────┬───────┴────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         网关层 (Gateway Layer)                             │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                    WebSocket Gateway                                 │ │
│   │  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │ │
│   │  │  HTTP Server │  │ WebSocket Server │ │  Message Pipeline    │  │ │
│   │  │  (FastAPI)   │  │  (websockets)   │ │  → Router → Agent   │  │ │
│   │  └─────────────┘  └────────────────┘  └────────────────────────┘  │ │
│   └─────────────────────────────────────────────────────────────────────┘ │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│   │  Adapters   │  │  Rate Limit │  │   Session   │  │   Pipeline  │  │
│   │  Registry   │  │   Manager   │  │   Manager   │  │  Decision  │  │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
           ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│    Agent Pool     │  │   Agent Loop     │  │  MCP Server     │
│   (快速路径)      │  │   (深度处理)      │  │   (工具暴露)     │
│  ┌────────────┐  │  │ ┌────────────┐  │  │ ┌────────────┐  │
│  │ LLM Agent  │  │  │ │  THINK    │  │  │ │  search   │  │
│  │ Search    │  │  │ │  ACT      │  │  │ │  llm      │  │
│  │ API Agent │  │  │ │  OBSERVE  │  │  │ │  weather  │  │
│  └────────────┘  │  │ │  REFLECT  │  │  │ └────────────┘  │
└──────────────────┘  │ └────────────┘  │  └──────────────────┘
                        └─────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      自进化层 (Self-Evolution Layer)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Heartbeat  │  │ Experience  │  │   Skills    │  │   Router   │    │
│  │   Engine    │  │   Logger    │  │   Loader    │  │ Self-Learning│   │
│  │  (7步循环)   │  │  (.learnings)│  │ (动态加载)  │  │  (路由优化)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       智能服务层 (Intelligence Layer)                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ Intelligence     │  │   Push Service   │  │  Agent Comm     │      │
│  │ Pipeline         │  │   (主动推送)      │  │  (A2A Protocol) │      │
│  │ 抓取→分析→评分→推送 │  │  多渠道推送     │  │  Agent间通信    │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                       反馈闭环层 (Feedback Loop Layer)                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │  Feedback API    │  │  FeedbackLoop    │  │ Observability   │      │
│  │  反馈收集端点     │  │  AI反馈处理      │  │   指标监控      │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. 核心组件

### 2.1 网关层 (Gateway Layer)

| 组件 | 路径 | 描述 |
|------|------|------|
| WebSocketGateway | `src/gateway/websocket_server.py` | WebSocket + HTTP 网关 |
| MessagePipeline | `src/gateway/pipeline.py` | 消息处理流水线 (预路由→决策→处理) |
| AdapterRegistry | `src/adapters/registry.py` | 平台适配器注册 |
| SessionManager | `src/gateway/session.py` | 会话管理 |

**核心流程**:
```
用户消息 → Gateway → MessagePipeline
                           │
              ┌────────────┴────────────┐
              │ _needs_deep_processing() │
              │  - 复杂关键词检测         │
              │  - 消息长度 > 100        │
              │  - 多轮对话上下文         │
              └────────────┬────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         ▼                                   ▼
   AgentLoop (深度处理)              AgentPool (快速路径)
   - THINK → ACT                     - keyword_router
   - OBSERVE → REFLECT              - ai_router
         │                           - agent_pool
         └────────────┬──────────────┘
                      ▼
               响应 → 推送回用户
```

### 2.2 自进化层 (Self-Evolution Layer)

| 组件 | 路径 | 描述 |
|------|------|------|
| HeartbeatEngine | `src/heartbeat/engine.py` | 7步认知循环引擎 |
| ExperienceLogger | `src/memory/experience_logger.py` | 经验日志系统 |
| SkillsLoader | `src/skills/loader.py` | 动态技能加载 |
| SelfLearningRouter | `src/router/self_learning.py` | 自学习路由 |

**7步认知循环**:
```
1. INFORMATION_INTAKE (信息摄入)
   └─→ search_web 获取外部信息

2. VALUE_JUDGMENT (价值判断)
   └─→ 规则评分 + AI 分析

3. KNOWLEDGE_OUTPUT (知识输出)
   └─→ 保存到 .learnings/

4. SOCIAL_MAINTENANCE (社交维护)
   └─→ 检查平台健康状态

5. SELF_REFLECTION (自我反思)
   └─→ 分析指标和反馈

6. SKILL_UPDATE (技能更新)
   └─→ 动态加载技能

7. NOTIFICATION_CHECK (通知检查)
   └─→ 系统健康告警

8. INTELLIGENCE_GATHERING (情报收集)
   └─→ 情报获取→评分→推送
```

### 2.3 智能服务层 (Intelligence Layer)

| 组件 | 路径 | 描述 |
|------|------|------|
| IntelligencePipeline | `src/intelligence/pipeline.py` | 情报处理流水线 |
| IntelligenceFetcher | `src/intelligence/fetcher.py` | 新闻数据获取 |
| IntelligenceAnalyzer | `src/intelligence/analyzer.py` | AI 深度分析 |
| IntelligenceScorer | `src/intelligence/scorer.py` | 多维度评分 |
| IntelligencePusher | `src/intelligence/pusher.py` | 多渠道推送 |

**评分公式**:
```
score = recency×0.2 + relevance×0.3 + importance×0.3 + user_match×0.2
```

### 2.4 Agent 通信层 (Agent Communication)

| 组件 | 路径 | 描述 |
|------|------|------|
| A2AServer | `src/agent_comm/a2a.py` | A2A 协议服务器 |
| AgentCardRegistry | `src/agent_comm/cards.py` | Agent 能力注册 |
| AgentCommunicator | `src/agent_comm/__init__.py` | 统一通信接口 |

**A2A 协议** (Google 2025):
```
tasks/send     - 提交任务
tasks/get      - 获取任务状态
tasks/cancel   - 取消任务
agents/list    - 列出可用 Agent
agents/get     - 获取 Agent 详情
```

### 2.5 反馈闭环层 (Feedback Loop)

| 组件 | 路径 | 描述 |
|------|------|------|
| FeedbackService | `src/feedback/__init__.py` | 反馈收集服务 |
| FeedbackAPI | `src/feedback/api.py` | FastAPI 端点 |
| FeedbackLoop | `src/feedback/loop.py` | AI 反馈处理 |
| PushFeedbackTracker | `src/intelligence/pusher.py` | 推送反馈追踪 |

## 3. 业务流程

### 3.1 用户消息处理流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        用户消息处理流程                                   │
└─────────────────────────────────────────────────────────────────────────┘

用户发送消息
     │
     ▼
┌─────────────────┐
│  WebSocket/HTTP  │
│    Gateway      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MessagePipeline │
│  (预处理 + 决策) │
└────────┬────────┘
         │
         ▼
   需要深度处理?
    ┌────┴────┐
    │  YES    │  NO
    ▼         ▼
┌────────┐ ┌────────────┐
│AgentLoop│ │ AgentPool  │
│ THINK  │ │ keyword    │
│ ACT    │ │ router     │
│OBSERVE │ │ AI router  │
│REFLECT │ │ agent pool │
└───┬────┘ └─────┬──────┘
    │            │
    └─────┬──────┘
          │
          ▼
    ┌─────────────┐
    │ 响应生成    │
    └─────┬───────┘
          │
          ▼
    ┌─────────────┐
    │ Postprocess │
    │ (发送响应)  │
    └─────┬───────┘
          │
          ▼
    ┌─────────────┐
    │ 用户收到响应 │
    └─────────────┘
          │
          ▼ (可选)
    ┌─────────────┐
    │ 反馈提交    │
    │ (thumbs up/ │
    │ down/rating)│
    └─────────────┘
          │
          ▼
    ┌─────────────┐
    │ FeedbackLoop│
    │ (分析模式)  │
    └─────────────┘
```

### 3.2 主动情报推送流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       主动情报推送流程                                   │
└─────────────────────────────────────────────────────────────────────────┘

Heartbeat 触发
(定时任务)
     │
     ▼
┌─────────────────────────┐
│ IntelligenceGatheringTask│
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ IntelligencePipeline    │
│  1. fetch_data()       │  ← IntelligenceFetcher
│  2. analyze()          │  ← IntelligenceAnalyzer
│  3. score()            │  ← IntelligenceScorer
│  4. push()             │  ← IntelligencePusher
└────────────┬────────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌────────┐ ┌────────┐ ┌────────┐
│ 飞书   │ │ Telegram│ │ Email │
└────────┘ └────────┘ └────────┘
    │        │        │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ PushFeedbackTracker│
    │ (记录投递/打开/  │
    │  用户反馈)        │
    └─────────────────┘
```

### 3.3 Agent 间通信流程 (A2A)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Agent 间通信流程 (A2A)                             │
└─────────────────────────────────────────────────────────────────────────┘

本地 Agent
发起请求
     │
     ▼
┌─────────────────────┐
│ AgentCommunicator    │
│ .a2a_send_task()    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ A2AClient           │
│ (JSON-RPC over HTTP)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│         远程 A2A Server            │
│  ┌─────────────────────────────┐ │
│  │ tasks/send                   │ │
│  │   → 创建 Task                │ │
│  │   → 提交给 Handler           │ │
│  │   → 返回 taskId              │ │
│  └─────────────────────────────┘ │
└──────────┬────────────────────────┘
           │
           ▼
      taskId
           │
           ▼
┌─────────────────────┐
│ .a2a_get_task()    │
│ (轮询/订阅)         │
└─────────────────────┘
```

## 4. 部署流程

### 4.1 环境要求

| 组件 | 要求 |
|------|------|
| Python | 3.11+ |
| 数据库 | SQLite ( checkpoints, learnings ) |
| 消息平台 | Telegram Bot, 飞书 Webhook, WeChat |
| 网络 | 固定域名/公网 IP |

### 4.2 Docker 部署

```bash
# 1. 克隆项目
git clone <repo>
cd message-integrate-agent

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入:
# - TELEGRAM_BOT_TOKEN
# - FEISHU_WEBHOOK_URL
# - OPENAI_API_KEY
# - etc.

# 3. 启动
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

### 4.3 主要服务端口

| 端口 | 服务 |
|------|------|
| 8000 | WebSocket Gateway |
| 8081 | MCP Server |
| 8082 | A2A Server (可选) |

## 5. 行业最佳实践参考

### 5.1 架构模式

| 参考项目 | 核心概念 |
|----------|----------|
| Microsoft AutoGen | 多 Agent 对话, 消息先进 Agent 对话 |
| Google A2A Protocol | Agent 互操作标准 (2025) |
| CrewAI | Role-based 多 Agent 编排 |
| Claude Code | Agent 能力扩展 |
| TrendRadar | 情报聚合与推送 |
| OpenClaw | 心跳循环 + 经验日志 |

### 5.2 核心设计原则

1. **Pipeline 模式**: 消息处理流水线, 预路由→决策→处理
2. **自进化机制**: Heartbeat 循环 + 经验日志 + 技能动态加载
3. **反馈闭环**: 用户反馈 → AI 分析 → 系统改进
4. **标准化通信**: A2A 协议 + Agent Card 能力描述

### 5.3 关键设计决策

| 决策 | 理由 |
|------|------|
| FastAPI + WebSocket | 高性能异步 I/O |
| AgentLoop vs AgentPool | 简单请求快速响应, 复杂问题深度处理 |
| 情报多维度评分 | 时效性+相关性+重要性+用户匹配 |
| A2A Protocol | 标准化 Agent 间通信 |

## 6. 目录结构

```
message-integrate-agent/
├── src/
│   ├── main.py                 # 主入口
│   ├── config.py               # 配置
│   │
│   ├── gateway/               # 网关层
│   │   ├── websocket_server.py
│   │   ├── pipeline.py
│   │   ├── session.py
│   │   └── rate_limiter.py
│   │
│   ├── adapters/               # 平台适配器
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── telegram_adapter.py
│   │   ├── feishu_adapter.py
│   │   └── wechat_adapter.py
│   │
│   ├── agents/                # Agent 系统
│   │   ├── pool.py
│   │   ├── loop.py
│   │   ├── checkpoint.py
│   │   ├── roles.py
│   │   └── enforcer.py
│   │
│   ├── router/                # 路由系统
│   │   ├── keyword_router.py
│   │   ├── ai_router.py
│   │   ├── registry.py
│   │   └── self_learning.py
│   │
│   ├── heartbeat/             # 自进化引擎
│   │   ├── engine.py
│   │   ├── response.py
│   │   ├── checklist.py
│   │   ├── queue.py
│   │   ├── scheduler.py
│   │   ├── idempotent.py
│   │   └── memory.py
│   │
│   ├── intelligence/          # 情报系统
│   │   ├── fetcher.py
│   │   ├── analyzer.py
│   │   ├── scorer.py
│   │   ├── pusher.py
│   │   └── pipeline.py
│   │
│   ├── agent_comm/            # Agent 通信
│   │   ├── protocol.py
│   │   ├── a2a.py
│   │   ├── cards.py
│   │   └── __init__.py
│   │
│   ├── feedback/              # 反馈系统
│   │   ├── __init__.py
│   │   ├── api.py
│   │   └── loop.py
│   │
│   ├── push/                 # 推送服务
│   ├── memory/               # 经验日志
│   ├── skills/               # 技能系统
│   ├── mcp/                  # MCP 服务器
│   ├── observability/        # 可观测性
│   └── proxy/                # 代理管理
│
├── tests/                    # 测试
├── .learnings/               # 学习数据
├── logs/                     # 日志
├── docs/                     # 文档
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 7. 监控与运维

### 7.1 健康检查

```bash
# 基础健康检查
GET /health

# 详细状态
GET /health/detailed
```

### 7.2 日志

- 位置: `logs/app.log`
- 轮转: 100MB / 7天

### 7.3 关键指标

| 指标 | 描述 |
|------|------|
| active_connections | WebSocket 连接数 |
| messages_processed | 消息处理数 |
| feedback_thumbs_up | 正面反馈数 |
| feedback_thumbs_down | 负面反馈数 |
| agent_loop_runs | AgentLoop 执行次数 |
| intelligence_pushed | 情报推送数 |

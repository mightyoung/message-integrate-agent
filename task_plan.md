# 信息通信中枢 Agent - 实现计划 (v2.0)

## 项目概述

**项目名称**: message-integrate-agent
**目标**: 构建一个连接移动端消息平台(Telegram、飞书、微信)的AI助手，支持Docker部署，通过智能路由分发任务给不同的AI Agent和服务，具备OpenClaw风格的自进化能力。

---

## 已完成阶段

### ✅ 阶段 1-7: 核心功能 (已完成)

| 阶段 | 内容 | 状态 |
|------|------|------|
| 1 | 项目骨架搭建 | ✅ |
| 2 | Gateway 核心 | ✅ |
| 3 | 消息平台适配器 | ✅ |
| 4 | MCP Server 集成 | ✅ |
| 5 | 代理支持 | ✅ |
| 6 | 智能路由 | ✅ |
| 7 | Agent Pool | ✅ |

---

## 新增阶段：自进化能力 (P0)

### 阶段 9: 心跳循环系统 [completed]

**任务**:
- [x] 9.1 实现 HeartbeatEngine 心跳引擎
- [x] 9.2 实现7步认知循环 (信息摄入、价值判断、知识输出、社交维护、自我反思、技能更新、通知检查)
- [x] 9.3 集成到主程序

**产出**:
- `src/heartbeat/engine.py` - 心跳循环引擎

---

### 阶段 10: 经验日志系统 [completed]

**任务**:
- [x] 10.1 实现 ExperienceLogger 经验日志
- [x] 10.2 实现 .learnings/ 目录结构 (LEARNINGS.md, ERRORS.md, FEATURE_REQUESTS.md)
- [x] 10.3 集成到错误处理系统

**产出**:
- `src/memory/experience_logger.py` - 结构化经验日志

---

### 阶段 11: Skills 动态加载 [completed]

**任务**:
- [x] 11.1 实现 SkillsLoader 技能加载器
- [x] 11.2 实现目录扫描和动态导入
- [x] 11.3 支持运行时注册技能

**产出**:
- `src/skills/loader.py` - 动态技能加载器

---

### 阶段 12: 自学习路由 [completed]

**任务**:
- [x] 12.1 实现 SelfLearningRouter 自学习路由器
- [x] 12.2 实现关键词自动提取
- [x] 12.3 实现从成功案例学习

**产出**:
- `src/router/self_learning.py` - 自学习路由

---

## 新增阶段：架构增强 (P1)

### 阶段 13: Agent 间通信 [pending]

**目标**: 实现接收网络内其他 agent 或后端服务的信息

**任务**:
- [ ] 13.1 实现 Agent Registry 协议
- [ ] 13.2 实现服务发现机制
- [ ] 13.3 实现 RPC 通信层
- [ ] 13.4 实现消息队列支持

**产出**:
- `src/agent_comm/` - Agent 通信模块

---

### 阶段 14: 主动推送能力 [pending]

**目标**: 支持主动向用户推送消息

**任务**:
- [ ] 14.1 实现用户状态追踪
- [ ] 14.2 实现消息队列管理
- [ ] 14.3 实现推送策略引擎
- [ ] 14.4 集成飞书/微信主动推送

---

### 阶段 15: Docker 部署优化 [pending]

**目标**: 完善 Docker 部署配置

**任务**:
- [ ] 15.1 优化 Dockerfile (多阶段构建)
- [ ] 15.2 完善 docker-compose.yml
- [ ] 15.3 添加健康检查
- [ ] 15.4 配置日志收集

---

### 阶段 16: 用户反馈系统 [pending]

**目标**: 收集用户对回复质量的反馈

**任务**:
- [ ] 16.1 实现反馈收集接口
- [ ] 16.2 实现评分机制
- [ ] 16.3 集成到经验日志
- [ ] 16.4 反馈驱动的路由优化

---

## 当前架构

```
message-integrate-agent/src/
├── main.py                 # 主入口
├── config.py              # 配置
├── error_handling.py      # 错误处理
│
├── gateway/               # 消息网关
│   ├── websocket_server.py
│   ├── pipeline.py
│   ├── rate_limiter.py
│   ├── session.py
│   ├── message.py
│   └── dispatcher.py
│
├── adapters/              # 平台适配器
│   ├── base.py
│   ├── registry.py
│   ├── capabilities.py
│   ├── telegram_adapter.py
│   ├── feishu_adapter.py
│   └── wechat_adapter.py
│
├── agents/                # Agent 池
│   ├── pool.py
│   ├── llm_agent.py
│   ├── search_agent.py
│   └── api_agent.py
│
├── router/                # 路由
│   ├── keyword_router.py
│   ├── ai_router.py
│   ├── registry.py
│   └── self_learning.py  # 🧠 自学习
│
├── mcp/                   # MCP 服务器
│   ├── server.py
│   └── tools/
│
├── proxy/                 # 代理管理
│   └── manager.py
│
├── heartbeat/            # 🧬 心跳循环 ⭐
│   └── engine.py
│
├── memory/              # 📚 经验日志 ⭐
│   └── experience_logger.py
│
└── skills/              # ⚡ 动态技能 ⭐
    └── loader.py
```

---

## 技术栈

| 组件 | 技术选型 |
|------|----------|
| 语言 | Python 3.11+ |
| Web框架 | FastAPI 0.109+ |
| MCP | FastMCP 2.0+ |
| 消息网关 | websockets 14.0+ |
| 部署 | Docker, Docker Compose |

---

## 下一步

优先实施阶段 13-14：
1. Agent 间通信 (接收 trenradar、bettafish 等信息)
2. 主动推送能力 (通过飞书等通道)

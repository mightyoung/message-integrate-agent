# 信息通信中枢 Agent - 实现计划 (v2.1)

## 项目概述

**项目名称**: message-integrate-agent
**目标**: 构建一个连接移动端消息平台(Telegram、飞书、微信)的AI助手，支持Docker部署，通过智能路由分发任务给不同的AI Agent和服务，具备OpenClaw风格的自进化能力。

---

## 已完成阶段

### ✅ 阶段 1-25: 全部完成

| 阶段 | 内容 | 状态 |
|------|------|------|
| 1-7 | 核心功能 | ✅ |
| 9-12 | 自进化能力 | ✅ |
| 13 | Agent通信 | ✅ |
| 14 | 主动推送 | ✅ |
| 15 | Docker部署优化 | ✅ |
| 16 | 用户反馈系统 | ✅ |
| 17 | 可观测性系统 | ✅ |
| 18 | 代码质量提升 | ✅ |
| 19 | Heartbeat增强 | ✅ |
| 20 | 技能系统增强 | ✅ |
| 21 | AgentLoop标准化 | ✅ |
| 22 | 消息→Agent流程 | ✅ |
| 23 | 反馈闭环 | ✅ |
| 24 | 情报→推送闭环 | ✅ |
| 25 | A2A协议 | ✅ |

---

## 新增阶段：意图识别系统 (P0)

### 阶段 26: 飞书菜单集成 [completed]

**设计文档**: `docs/plans/2026-03-08-intent-recognition-design.md`
**实现计划**: `docs/plans/2026-03-08-intent-recognition-impl-plan.md`

**目标**: 实现 Level 0 意图识别 (确定性操作，100%准确)

**任务**:
- [x] 26.1 在飞书开发者控制台配置自定义菜单 (用户操作)
- [x] 26.2 实现 FeishuMenuHandler 处理器
- [x] 26.3 集成菜单事件到路由管道
- [x] 26.4 测试菜单点击事件响应

**菜单配置**:
```
📰 情报: 热点新闻 | 科技动态 | AI进展 | 投资并购 | 行业报告
🔍 搜索: 搜索新闻 | 搜索资讯 | 搜索趋势 | 高级搜索
⚙️ 设置: 获取配置 | 推送频率 | 语言设置 | 清除历史
```

**产出**:
- `src/router/menu_handler.py` - 菜单事件处理器
- `src/adapters/feishu_adapter.py` - 添加菜单事件处理
- `tests/test_menu_handler.py` - 测试用例

**关键限制**: 飞书菜单仅支持**一对一私聊**，不支持群聊

---

### 阶段 27: 基础设施 [pending]

**目标**: 创建数据存储层 (PostgreSQL + Redis)

**任务**:
- [ ] 27.1 创建 PostgreSQL Schema (intents, conversations, messages, feedback)
- [ ] 27.2 实现数据模型 (src/router/models.py)
- [ ] 27.3 实现 Redis Session Manager (src/router/session_manager.py)

**产出**:
- `scripts/create_intent_schema.sql` - 数据库脚本
- `src/router/models.py` - 数据模型
- `src/router/session_manager.py` - 会话管理

---

### 阶段 28: 核心路由引擎 [pending]

**目标**: 实现多层意图识别 (Menu → Rule → Vector → LLM)

**任务**:
- [ ] 28.1 增强 IntentRegistry (50+ 意图定义)
- [ ] 28.2 实现 MultiLevelRouter 路由引擎
- [ ] 28.3 集成现有 KeywordRouter (Level 1)
- [ ] 28.4 集成 LLM 路由 (Level 3)

**产出**:
- `src/router/registry.py` - 意图注册表 (增强)
- `src/router/engine.py` - 路由引擎 (新建)

**复用组件**:
- `src/router/keyword_router.py` - 关键词路由
- `src/router/self_learning.py` - 自学习路由

---

### 阶段 29: Agent 执行协调 [pending]

**目标**: 实现意图执行与 Agent 协调

**任务**:
- [ ] 29.1 实现 AgentCoordinator 协调器
- [ ] 29.2 集成现有 Agent (LLMAgent, SearchAgent)
- [ ] 29.3 集成 Intelligence 模块 (情报获取)

**产出**:
- `src/router/coordinator.py` - Agent 协调器

**复用组件**:
- `src/agents/llm_agent.py` - LLM 对话
- `src/agents/search_agent.py` - Web 搜索
- `src/intelligence/pusher.py` - 情报推送

---

### 阶段 30: 学习系统 [pending]

**目标**: 实现自适应学习能力

**任务**:
- [ ] 30.1 集成 SelfLearningRouter (反馈学习)
- [ ] 30.2 实现 FeedbackCollector 反馈收集
- [ ] 30.3 实现规则自动更新

**产出**:
- `src/router/learning.py` - 学习引擎

---

### 阶段 31: 测试与优化 [pending]

**目标**: 全面测试与性能优化

**任务**:
- [ ] 31.1 单元测试 (menu_handler, engine, coordinator)
- [ ] 31.2 集成测试 (端到端流程)
- [ ] 31.3 性能优化 (缓存、连接池)
- [ ] 31.4 文档完善

---

## 意图识别系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        IntentRouter (统一入口)                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   Routing Pipeline                           │   │
│  │  ┌─────────┐  ┌─────────────┐  ┌──────────┐  ┌────────┐  │   │
│  │  │  Menu  │→ │   Rules     │→ │   LLM    │→ │Fallback│  │   │
│  │  │ Level0 │  │  Level1     │  │ Level3   │  │        │  │   │
│  │  │ <5ms   │  │   <10ms     │  │  <300ms  │  │        │  │   │
│  │  └─────────┘  └─────────────┘  └──────────┘  └────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
        ┌───────────────────┐    ┌───────────────────────┐
        │  ContextManager   │    │  LearningEngine       │
        │  (Redis + PG)    │    │  (SelfLearningRouter) │
        └───────────────────┘    └───────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
        ┌───────────────────┐    ┌───────────────────────┐
        │  AgentCoordinator  │    │  FeedbackCollector    │
        │  • Intelligence   │    │  (User Feedback)      │
        │  • Search          │    └───────────────────────┘
        │  • LLM             │
        └───────────────────┘
```

---

## 意图分类 (50+)

| 类别 | 数量 | 占比 |
|------|------|------|
| 情报类 | 40 | 70% |
| 对话类 | 15 | 30% |
| 系统类 | 5 | - |

---

## 时间线

| 阶段 | 天数 | 关键交付物 |
|------|------|-----------|
| Phase 0: 飞书菜单 | Day 1-2 | 菜单配置、事件处理器 |
| Phase 1: 基础设施 | Day 2-4 | 数据库模型、Session管理 |
| Phase 2: 核心路由 | Day 4-7 | 多层路由引擎、意图注册 |
| Phase 3: Agent执行 | Day 7-9 | Agent协调器 |
| Phase 4: 学习系统 | Day 9-10 | 自适应学习 |
| Phase 5: 测试优化 | Day 10-12 | 测试、文档 |

---

## 新任务：飞书长连接 + Mihomo 代理集成

### 阶段 A: Mihomo 代理集成
- [ ] A.1 创建 MihomoConnector 类 (src/proxy/mihomo.py)
- [ ] A.2 修改 config/proxy.yaml 添加 mihomo 配置
- [ ] A.3 增强 ProxyManager 集成 mihomo
- [ ] A.4 测试本地代理连接

### 阶段 B: GeoIP 路由支持
- [ ] B.1 创建 GeoIPRouter 类 (src/proxy/geoip.py)
- [ ] B.2 集成中国 IP 段数据
- [ ] B.3 实现 HybridRouter 混合路由
- [ ] B.4 测试 GeoIP 判断

### 阶段 C: 飞书长连接修复
- [ ] C.1 修复 FeishuWebSocketClient 同步/异步问题
- [ ] C.2 在 FeishuAdapter 中正确调用
- [ ] C.3 测试长连接稳定性

### 阶段 D: 搜索代理集成
- [ ] D.1 修改 search_web 函数集成代理判断
- [ ] D.2 配置 Tavily 等域名走代理
- [ ] D.3 端到端测试

---

## 设计文档
- `docs/plans/2026-03-08-feishu-websocket-mihomo-design.md`

## 关键决策
| Decision | Rationale |
|----------|-----------|
| 使用混合模式（域名+GeoIP） | 用户明确需求 |
| HTTP 9090 + SOCKS5 7890 双端口 | 用户明确选择 |
| 飞书长连接直连 | 用户明确不需要代理 |
| 使用域名规则优先，GeoIP fallback | 性能更好 |
| docker-compose 自建 mihomo | 用户要求 |
| 使用 host 网络模式 | 让 mihomo 直接访问外网 |

## 错误记录
| Error | Attempt | Resolution |
|-------|---------|------------|
| FeishuWebSocketClient asyncio 冲突 | 1 | 使用同步 start() 方法 |
| lark_oapi SDK API 不熟悉 | 1 | 通过 dir() 和 inspect 探索 |
| EventDispatcherHandler 导入错误 | 1 | 从 lark_oapi 直接导入 |

## 新增文件
- `config/clash/config.yaml` - Clash.Meta 配置 (备用)
- `docker-compose.yml` - 更新为使用 NAS mihomo
- `.env` - 添加代理配置
- `config/proxy.yaml` - 更新 mihomo 配置
- `src/intelligence/feeds_config.py` - 集成 TrendRadar + WorldMonitor RSS 源

## 测试结果
✅ 飞书长连接: connected to wss://msg-frontier.feishu.cn - ping success
✅ mihomo 代理: Tavily/GitHub 通过代理访问成功
✅ 飞书/百度直连: 不走代理访问成功
✅ RSS 源集成: 300+ 源，覆盖 geopolitics, military, cyber, tech, finance, science 等分类
✅ ArXiv + 论文翻译/总结: 设计完成，待实现
✅ BettaFish + MiroFish 集成: 设计完成，待实现

# 进度记录

## 项目完成状态: ✅ 全部完成 (核心模块)

### 核心模块完成情况

| 模块 | 阶段 | 状态 |
|------|------|------|
| 核心功能 | 1-7 | ✅ |
| 自进化能力 | 9-12 | ✅ |
| Agent通信 | 13 | ✅ |
| 主动推送 | 14 | ✅ |
| 用户反馈 | 16 | ✅ |
| 可观测性 | 17 | ✅ |
| 代码质量 | 18 | ✅ |
| Heartbeat增强 | 19 | ✅ |
| 技能系统 | 20 | ✅ |
| AgentLoop | 21 | ✅ |
| 消息→Agent流程 | 22 | ✅ |
| 反馈闭环 | 23 | ✅ |
| 情报→推送闭环 | 24 | ✅ |
| A2A协议 | 25 | ✅ |
| **意图识别** | **26-31** | **🔄 进行中** |

---

## 会话信息

**日期**: 2026-03-08
**用户**: muyi
**项目**: message-integrate-agent
**会话**: 意图识别系统设计与实现

---

## 最新: 意图识别系统 (2026-03-08)

### 设计阶段 ✅

**任务**:
- [x] 26.1 意图识别系统设计
- [x] 26.2 飞书自定义菜单集成设计
- [x] 26.3 实现计划制定

**产出**:
- `docs/plans/2026-03-08-intent-recognition-design.md` - 设计文档 (1000+ 行)
- `docs/plans/2026-03-08-intent-recognition-impl-plan.md` - 实现计划

**设计要点**:
- 多层路由: Menu (Level 0) → Rule (Level 1) → Vector (Level 2) → LLM (Level 3)
- 50+ 意图分类: 情报类 40 个 (70%), 对话类 15 个 (30%), 系统类 5 个
- PostgreSQL + pgvector + Redis 存储
- 自适应学习 (基于现有 SelfLearningRouter)

**飞书菜单设计** (关键限制):
- 仅支持一对一私聊，不支持群聊
- 3 主菜单 + 13 子菜单
- 配置步骤: 开发者控制台 → Bot能力 → 自定义菜单 → 推送事件

### 实现阶段 🔄

**计划时间线**: 8-12 天

| 阶段 | 任务 | 状态 |
|------|------|------|
| Phase 0 | 飞书菜单集成 | ✅ 已完成 |
| Phase 1 | 基础设施 (DB + Redis) | ⏳ 待开始 |
| Phase 2 | 核心路由引擎 | ⏳ 待开始 |
| Phase 3 | Agent 执行协调 | ⏳ 待开始 |
| Phase 4 | 学习系统 | ⏳ 待开始 |
| Phase 5 | 测试优化 | ⏳ 待开始 |

**已完成**:

#### Phase 0.3: 菜单事件处理器 ✅
- 创建 `src/router/menu_handler.py`
  - FeishuMenuHandler 类
  - 13 个菜单项映射
  - IntentResult 数据类
  - get_menu_handler() 全局实例
  - handle_menu_event() 事件处理

#### Phase 0.4: 集成到 FeishuAdapter ✅
- 修改 `src/adapters/feishu_adapter.py`
  - 添加菜单事件处理 (`im.menu` 类型)
  - 添加 `_execute_menu_intent()` 方法
  - 支持 13 个菜单项的意图执行

#### 测试 ✅
- 创建 `tests/test_menu_handler.py` - 9 个测试用例
- 所有测试通过 (90 + 9 = 99 tests)
- `src/router/menu_handler.py` - 菜单事件处理器
- `src/router/models.py` - 数据模型
- `src/router/session_manager.py` - 会话管理
- `src/router/engine.py` - 路由引擎
- `src/router/coordinator.py` - Agent 协调器
- `src/router/learning.py` - 学习引擎
- `scripts/create_intent_schema.sql` - 数据库脚本

**可复用组件**:
- `src/router/keyword_router.py` - 关键词路由
- `src/router/self_learning.py` - 自学习
- `src/agents/llm_agent.py` - LLM 对话
- `src/agents/search_agent.py` - Web 搜索
- `src/intelligence/pusher.py` - 情报推送
- `src/adapters/feishu_adapter.py` - 飞书适配器

---

### 架构优化摘要

**Level 0: 飞书菜单** (确定性操作)
```
优点: 100%准确, <5ms延迟, 零成本
限制: 仅私聊
```

**Level 1: 规则匹配** (KeywordRouter)
```
优点: <10ms延迟, 可解释
限制: 需要关键词覆盖
```

**Level 2: 向量语义** (pgvector)
```
优点: 语义理解, 模糊匹配
限制: 需要训练数据
```

**Level 3: LLM 理解** (DeepSeek)
```
优点: 理解复杂意图
限制: 延迟高, 成本高
```

---

### 行业最佳实践参考

1. **Rasa NLU Pipeline**: 规则 → ML → Fallback
2. **Few-shot Learning**: 3-5 示例提升意图识别
3. **置信度阈值**:
   - > 0.85 → 直接执行
   - 0.6-0.85 → 确认后执行
   - < 0.6 → LLM 兜底

---

## 架构文档

详细架构说明见: `docs/architecture.md`

---

## 最新完成: 阶段 25 - A2A 协议实现

### 22.1 Intelligence 模块 ✅ (Task #56)

基于 TrendRadar 重构情报处理系统:

**创建文件**:
- `src/intelligence/__init__.py` - 模块入口
- `src/intelligence/fetcher.py` - 新闻数据获取 (基于 TrendRadar DataFetcher)
- `src/intelligence/analyzer.py` - AI 分析 (基于 TrendRadar AIAnalyzer)
- `src/intelligence/scorer.py` - 用户匹配评分
- `src/intelligence/pusher.py` - 多渠道推送 (基于 TrendRadar NotificationDispatcher)
- `src/intelligence/pipeline.py` - 处理流水线

**集成**:
- 更新 `src/main.py` - 添加 IntelligencePipeline 初始化
- 更新 `requirements.txt` - 添加 requests 依赖

### 22.2 AgentLoop 集成到 MessagePipeline ✅ (Task #57)

实现消息→Agent 流程闭环:

**修改文件**:
- `src/gateway/pipeline.py` - 添加 AgentLoop 集成
  - 构造函数添加 agent_loop, checkpoint_manager 参数
  - 添加 `_needs_deep_processing()` 决策方法
  - 添加 `_process_with_loop()` 深度处理方法
  - 添加 `_process_fast_path()` 快速路径方法
  - 更新 `set_components()` 支持新组件

- `src/gateway/websocket_server.py` - 添加 AgentLoop 连接
  - 构造函数初始化 agent_loop, checkpoint_manager
  - 添加 `set_agent_loop()` 方法

- `src/main.py` - 集成所有组件
  - 添加 CheckpointManager 和 AgentLoop 初始化
  - 添加 gateway.set_agent_loop() 调用
  - 添加 checkpoint_manager 和 agent_loop 到 app 存储

**决策逻辑**:
- 复杂关键词: 分析、为什么、怎么、应该、建议、比较、总结、写、开发
- 消息长度 > 100 字符
- 多轮对话上下文 (is_continuation flag)

### 23.1 反馈 API 端点 ✅ (Task #58)

创建 FastAPI 端点:
- `src/feedback/api.py` - 反馈收集端点
  - POST /feedback - 提交反馈
  - GET /feedback/{feedback_id} - 获取反馈
  - GET /feedback/user/{user_id} - 用户反馈历史
  - GET /feedback/stats - 反馈统计
  - POST /feedback/webhook - Webhook 接收外部反馈

### 23.2 FeedbackLoop 类 ✅ (Task #59)

创建反馈闭环处理器:
- `src/feedback/loop.py` - 反馈闭环处理
  - FeedbackLoop 类 - 核心处理器
  - FeedbackPattern - 反馈模式检测
  - ReflectionResult - 反思结果
  - 模式分析 (同话题多次负面、低评分聚集)
  - get_suggestions() 改进建议

### 23.3 负面反馈触发 Agent 反思 ✅ (Task #60)

实现负面反馈→Agent反思闭环:
- thumbs_down 触发反思
- 低评分 (<=2) 触发反思
- 使用 AgentLoop 进行深度分析
- 记录反思结果到经验日志

### 23.4 纠正更新知识库 ✅ (Task #61)

实现纠正→知识库更新:
- correction 反馈触发知识更新
- 提取纠正内容
- 尝试更新关键词路由规则
- 记录到经验日志

**设计参考**:
- Self-Refine: agent 生成自我反馈
- RLHF: 从人类反馈中学习
- Critic Pattern: 即时反馈机制

### 24.1-24.2 IntelligenceScorer ✅ (已存在)

基于多维度评分:
- 时效性 (0.2) + 相关性 (0.3) + 重要性 (0.3) + 用户匹配 (0.2)
- UserProfile 用户画像 (兴趣、偏好分类、通知渠道)
- ScoredIntelligence 评分后情报

### 24.3 Heartbeat 集成 IntelligencePipeline ✅ (Task #62)

添加情报收集任务到 Heartbeat:
- `src/heartbeat/engine.py` - 添加 IntelligenceGatheringTask
- 添加 HeartbeatStep.INTELLIGENCE_GATHERING 步骤
- 在 Heartbeat 循环中定期执行情报收集→推送
- main.py 中连接 IntelligencePipeline 到 Heartbeat

### 24.4 推送反馈收集 ✅ (Task #63)

实现推送反馈追踪:
- `src/intelligence/pusher.py` - 添加 PushFeedbackTracker
  - PushRecord - 推送记录
  - PushFeedbackTracker - 反馈追踪器
  - record_push() - 记录推送
  - mark_delivered() / mark_opened() - 跟踪状态
  - record_feedback() - 用户反馈 (useful/not_useful)
  - get_engagement_stats() - 参与度统计

**行业最佳实践**:
- AI-powered optimization: 推送时机优化
- Personalization: 个性化推送
- User control: 用户控制权

### 25.1 AgentCard 注册机制 ✅ (Task #65)

实现 Google A2A Agent Card:
- `src/agent_comm/cards.py`
  - AgentCard - Agent 能力描述
  - AgentCardRegistry - 注册中心
  - AgentSkill - 技能定义
  - AuthType/Capability - 枚举定义

### 25.2 A2A Protocol Server ✅ (Task #66)

实现 A2A 协议服务器:
- `src/agent_comm/a2a.py`
  - A2AServer - 服务器实现
  - A2AClient - 客户端
  - Task/TaskState - 任务管理
  - tasks/send, tasks/get, tasks/cancel 端点
  - agents/list, agents/get 端点

### 25.3 外部 Agent 注册 ✅ (Task #67)

注册外部 Agent:
- register_trendradar_agent() - TrendRadar 情报 Agent
- register_berberfish_agent() - BerberFish 多模态 Agent
- 集成到 AgentCommunicator

### 25.4 任务分发与结果回收 ✅ (Task #68)

实现 A2A 任务分发:
- AgentCommunicator.a2a_send_task() - 发送任务
- AgentCommunicator.a2a_get_task() - 获取任务状态
- AgentCommunicator.a2a_list_agents() - 列出可用 Agent

**行业最佳实践**:
- Google A2A Protocol: Agent 互操作标准
- Agent Card: JSON 能力描述
- JSON-RPC over HTTP: 标准通信格式

### 19.1 HeartbeatResponse 响应契约 ✅ (Task #40)
- 创建 `src/heartbeat/response.py`
- 实现 HeartbeatStatus 枚举 (ok/alert/error)
- 实现 HeartbeatResponse 数据类
- 提供 ok(), alert(), error() 工厂方法
- 实现 to_push_message() 转换方法
- 实现 from_agent_result() 解析方法
- 添加 create_idempotency_key() 幂等性函数
- 添加 parse_channel() 通道解析函数

### 19.2 HeartbeatChecklist 检查清单 ✅ (Task #41)
- 创建 `src/heartbeat/checklist.py`
- 实现 ChecklistItem 数据类
- 实现 EvaluationResult 评估结果
- 实现 HeartbeatChecklist 主类
- 支持从 .learnings/HEARTBEAT.md 加载
- 支持默认检查项模板 (error_rate, user_feedback, inactive_users, skill_updates, health_status)
- 实现 _evaluate_condition() 安全条件评估
- 实现 _generate_response() 生成响应

### 19.3 CommandQueue Lane队列 ✅ (Task #42)
- 创建 `src/heartbeat/queue.py`
- 实现 LaneType 枚举 (global/session/sub_agent/cron)
- 实现 LANE_CONFIG 配置
- 实现 Command 数据类 (id, name, args, lane, session_id, idempotency_key, priority)
- 实现 CommandResult 数据类
- 实现 CommandQueue 主类
  - enqueue() 入队
  - _run_lane() Lane 运行循环
  - _execute() 命令执行
  - get_result() 获取结果
  - get_status() 队列状态
  - cancel() 取消命令
  - shutdown() 关闭
- 支持并发控制、幂等检查、FIFO排序

### 19.4 Cron 调度器 ✅ (Task #43)
- 创建 `src/heartbeat/scheduler.py`
- 实现 Job 数据类
- 实现 ScheduleType 枚举 (interval/cron/once)
- 实现 Scheduler 主类
  - schedule_interval() 间隔调度
  - schedule_cron() Cron 表达式调度
  - schedule_at() 一次性调度
  - unschedule() 取消任务
  - get_job() 获取任务
  - list_jobs() 列出任务
  - get_next_run_times() 下次运行时间
  - _scheduler_loop() 调度循环
- 支持 croniter 库（可选）
- 支持 max_runs 限制

### 19.5 IdempotentCommand 幂等命令 ✅ (Task #44)
- 创建 `src/heartbeat/idempotent.py`
- 实现 IdempotentResult 数据类
- 实现 IdempotentExecutor 主类
  - execute() 幂等执行
  - get_result() 获取缓存结果
  - invalidate() 使缓存失效
  - clear() 清空缓存
  - get_stats() 统计信息
- 实现 create_idempotent_key() Key 生成
- 实现 create_user_action_key() 用户动作 Key
- 实现 create_session_key() 会话 Key
- 支持 TTL 过期、缓存清理

### 19.6 MemoryCompactionTrigger 内存压缩 ✅ (Task #45)
- 创建 `src/heartbeat/memory.py`
- 实现 MemorySnapshot 快照数据类
- 实现 MemoryCompactionTrigger 主类
  - should_trigger() 阈值检测
  - trigger() 触发压缩
  - _build_compaction_prompt() 构建提示
  - _create_snapshot() 创建快照
  - _save_snapshot() 保存笔记
- 支持自定义压缩处理器
- 生成 .learnings/memory/ 目录下的笔记文件
- 支持 cooldown 冷却时间

### 20.1-3 技能系统增强 ✅ (Task #46-48)

#### 20.1 SkillGate 门控检查 ✅ (Task #46)
- 创建 `src/skills/gate.py`
- 实现 SkillMetadata 数据类
- 实现 GateResult 门控结果
- 实现 SkillGate 主类
  - check() 检查技能是否满足加载条件
  - _parse_metadata() 解析 YAML frontmatter
  - _check_binaries() 检查二进制依赖
  - _check_env_vars() 检查环境变量
  - _check_configs() 检查配置文件
  - _check_platform() 检查平台兼容性
- 支持 PyYAML (可选)
- 缓存机制

#### 20.2 ToolPolicy 工具策略 ✅ (Task #47)
- 创建 `src/skills/policy.py`
- 实现 PolicyEffect 枚举 (allow/deny)
- 定义 CORE_TOOLS 核心工具集合
- 实现 ToolPolicyRule 数据类
- 实现 ToolPolicy 主类
  - add_rule() 添加规则
  - remove_rule() 移除规则
  - is_allowed() 检查访问权限
  - _evaluate() 评估访问
  - _match_pattern() 模式匹配
  - get_allowed_tools() 获取允许工具
- 策略优先级: global_deny > agent_deny > global_allow > agent_allow > default
- 核心工具始终可用

#### 20.3 SkillRegistry 版本管理 ✅ (Task #48)
- 创建 `src/skills/registry.py`
- 实现 SkillVersion 语义版本类
- 实现 SkillInfo 技能信息类
- 实现 SkillUpdate 更新信息类
- 实现 SkillRegistry 主类
  - register() 注册技能
  - unregister() 注销技能
  - get() 获取技能
  - list_skills() 列出技能
  - list_updates() 检查更新
  - resolve() 解析版本
  - lock()/unlock() 版本锁定
  - resolve_dependencies() 依赖解析
- 支持三层优先级 (workspace/managed/bundled)
- 版本锁定文件 (.learnings/skills.lock)

### 19.7 HeartbeatIntegration 集成 ✅ (Task #49)
- 创建 `src/heartbeat/integration.py`
- 集成所有心跳组件
- 提供统一入口 HeartbeatIntegration
  - 队列操作 (enqueue_command, register_command_handler)
  - 调度操作 (schedule_interval, schedule_cron)
  - 幂等执行 (execute_idempotent)
  - 内存压缩 (should_compact_memory, compact_memory)
  - 检查清单 (evaluate_checklist, load_checklist)
- 提供 get_heartbeat_integration() 全局实例

### 20.4 SkillsIntegration 集成 ✅ (Task #50)
- 创建 `src/skills/integration.py`
- 集成所有技能增强组件
- 提供统一入口 SkillsIntegration
  - 技能发现 (discover_skills, 三层优先级)
  - 技能加载 (load_skill, unload_skill)
  - 工具策略 (is_tool_allowed, add_tool_policy)
  - 版本管理 (lock_skill_version, get_skill_version)
- 支持门控检查、工具策略、版本锁定

### 18.1 修复裸 except (P0) ✅
- `src/mcp/tools/search.py` - 第35行 except: → except (AttributeError, ValueError, TypeError)
- `src/mcp/tools/llm.py` - 第71行和157行 except: → except (AttributeError, ValueError, TypeError)

### 18.4 优化模块导入 (P1) ✅
- `src/heartbeat/engine.py` - 添加 LazyLoader 类
- 替换8处函数级导入为 LazyLoader.get() 调用:
  - search_web (line 124)
  - get_adapter_registry (line 301)
  - WebSocketGateway (line 337)
  - get_observability_service (line 365)
  - get_feedback_service (line 386, 629)
  - get_skills_loader (line 513)
  - get_push_service (line 616)

---

## 完整进度

### ✅ 阶段 1-7: 核心功能 (已完成)

- [x] 项目骨架搭建
- [x] Gateway 核心
- [x] 消息平台适配器
- [x] MCP Server 集成
- [x] 代理支持
- [x] 智能路由
- [x] Agent Pool

### ✅ 阶段 9-12: 自进化能力 (已完成)

- [x] 9.1 心跳循环引擎 - `src/heartbeat/engine.py`
- [x] 9.2 7步认知循环
- [x] 10.1 经验日志系统 - `src/memory/experience_logger.py`
- [x] 10.2 .learnings/ 目录结构
- [x] 11.1 Skills 动态加载 - `src/skills/loader.py`
- [x] 12.1 自学习路由 - `src/router/self_learning.py`

### ✅ 阶段 16: 用户反馈系统 (已完成)

- [x] 16.1 反馈收集接口 (FeedbackService)
- [x] 16.2 评分机制 (thumbs_up/down, rating)
- [x] 16.3 集成到经验日志 (correction -> ExperienceLogger)
- [x] 16.4 反馈统计 (FeedbackStats)

### ✅ 阶段 13: Agent 间通信 (已完成)

- [x] 13.1 服务注册中心 (ServiceRegistry)
- [x] 13.2 RPC 客户端 (RPCClient)
- [x] 13.3 消息队列 (MessageQueue)
- [x] 13.4 通信协议 (AgentMessage, Command)
- [x] 13.5 Agent 通信器 (AgentCommunicator)

### ✅ 阶段 14: 主动推送能力 (已完成)

- [x] 14.1 推送服务 (PushService)
- [x] 14.2 用户状态管理 (UserStateManager)
- [x] 14.3 推送策略引擎 (PushStrategy)
- [x] 14.4 消息队列 (PushQueue)

---

## 测试状态

```
85 tests passed
├── test_adapters.py      14 tests
├── test_pipeline.py      10 tests
├── test_rate_limiter.py  17 tests
├── test_gateway.py       19 tests
├── test_keyword_router.py 3 tests
├── test_llm_agent.py    3 tests
├── test_agent_pool.py    3 tests
├── test_message.py       3 tests
├── test_session.py       5 tests
└── test_registry.py      4 tests
```

---

## 新增文件

| 文件 | 说明 |
|------|------|
| `src/heartbeat/engine.py` | 心跳循环引擎 |
| `src/memory/experience_logger.py` | 经验日志系统 |
| `src/skills/loader.py` | 动态技能加载器 |
| `src/router/self_learning.py` | 自学习路由 |
| `src/agent_comm/__init__.py` | Agent 通信模块 |
| `src/agent_comm/protocol.py` | 通信协议定义 |
| `src/push/__init__.py` | 主动推送系统 |
| `src/feedback/__init__.py` | 用户反馈系统 |
| `src/observability/__init__.py` | 可观测性系统 |
| `docs/analysis_report.md` | 深度分析报告 |
| `src/agents/loop.py` | Agent 循环 (THINK→ACT→OBSERVE→REFLECT) |
| `src/agents/checkpoint.py` | SQLite 状态持久化 |
| `src/agents/roles.py` | 角色协作系统 (Sisyphus/Hephaestus/Prometheus) |
| `src/agents/enforcer.py` | 任务监督系统 (TodoEnforcer) |

---

## 技术债务

1. ✅ 已修复: main.py 中变量定义顺序问题 (第46行使用feishu_config，第57行才定义)
2. ✅ 已修复: 核心模块集成到lifespan (HeartbeatEngine, ExperienceLogger, PushService, AgentCommunicator)
3. ✅ 已修复: docker-compose.yml 添加 .learnings 持久化挂载
4. ✅ 已修复: 添加日志收集配置

---

## 最新发现 (2026-03-08)

### 行业最佳实践

1. **Agentic Design Patterns** - Ali Shamaei (Google)
   - 21个可复用设计模式
   - 核心执行模式: Reflection, Routing, Parallelisation, Tool Use, Planning, Multi-Agent Collaboration
   - 记忆与学习模式: 使AI能够从每次交互中学习和进化

2. **自进化机制** - 腾讯云技术白皮书
   - 6大核心组件: Continuous Learning, Feedback Loop, Memory, Meta-Learning, Self-Reflection, Autonomous Goal Setting
   - 实施步骤: 架构设计 → 在线学习 → 反馈机制 → 记忆系统 → 元学习 → 自监控 → 安全对齐

3. **参考项目**:
   - OpenClaw: 心跳循环 + 经验日志
   - TrendRadar: 多通道消息聚合
   - Claude Code: Agent能力扩展

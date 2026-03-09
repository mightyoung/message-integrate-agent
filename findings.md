# 研究发现

## 一、顶级专家视角分析

### 1.1 Jeff Bezos 思维：以用户反馈为驱动

**核心思维**：每做一个决定，问"这能否让用户的生活变得更美好？"

**当前系统问题**：
- 系统是完全被动的，用户不主动发消息就没有任何动作
- 没有收集用户对回复质量的反馈
- 没有追踪哪些路由决策是"好"的，哪些是"坏"的

**改进方向**：
- 添加用户反馈收集机制（👍👎 或评分）
- 追踪每个 agent 处理的成功率
- 建立反馈 → 学习的闭环

---

### 1.2 Sam Altman 思维：迭代速度和能力扩展

**核心思维**：快速迭代，小步快跑，持续能力扩展

**当前系统问题**：
- Agent 能力是静态的，运行时无法动态添加新 agent
- 关键词路由是硬编码的，无法从交互中学习
- 没有 skills 系统

**改进方向**：
- ✅ 已实现：Skills 动态加载系统
- ✅ 已实现：自学习路由机制

---

### 1.3 OpenClaw 思维：自主驱动的心跳

**核心思维**：智能体不是等待命令的工具，而是有"生命"的实体

**实现状态**：
- ✅ 已实现：HeartbeatEngine 心跳引擎
- ✅ 已实现：7步认知循环
- ✅ 已实现：ExperienceLogger 经验日志

---

## 二、行业最佳实践

### 2.1 Agent 通信模式

**参考项目**: OpenClaw, LangChain Agents, AutoGPT

**推荐方案**:
- **服务注册**: 使用 Consul 或 etcd 进行服务发现
- **通信协议**: gRPC 用于高效 Agent 间通信
- **消息队列**: Redis Pub/Sub 或 RabbitMQ

### 2.2 主动推送架构

**参考项目**: TrendRadar, Pusher, Firebase Cloud Messaging

**推荐方案**:
- **用户状态管理**: Redis 存储用户在线状态
- **消息队列**: Celery + Redis 实现异步推送
- **推送策略**: 频率限制 + 用户偏好配置

### 2.3 Docker 部署最佳实践

**参考项目**: Docker 官方最佳实践

**推荐方案**:
- 多阶段构建减小镜像大小
- 使用非 root 用户运行
- 健康检查探针
- 日志收集配置

---

## 三、设计模式参考

### 3.1 消息总线模式

```python
# 使用观察者模式实现消息总线
class MessageBus:
    def publish(self, topic, message):
        for subscriber in self.subscribers[topic]:
            subscriber.handle(message)

    def subscribe(self, topic, handler):
        self.subscribers[topic].append(handler)
```

### 3.2 命令模式

```python
# 用于指令下发
class Command:
    def execute(self):
        pass

class CommandDispatcher:
    def register(self, cmd_name, handler):
        self.handlers[cmd_name] = handler

    def dispatch(self, cmd_name, params):
        return self.handlers[cmd_name].execute(params)
```

### 3.3 状态机模式

```python
# 用于用户会话状态管理
class UserState:
    states = ['idle', 'waiting', 'processing', 'error']

    def transition(self, event):
        # 状态转换逻辑
        pass
```

---

## 四、技术选型建议

| 功能 | 推荐技术 | 理由 |
|------|----------|------|
| Agent 通信 | gRPC + Protobuf | 高效、类型安全 |
| 服务发现 | Consul | 成熟方案 |
| 消息队列 | Redis Pub/Sub | 轻量级 |
| 主动推送 | Celery + Redis | Python 原生 |
| 配置管理 | etcd | 热更新 |

---

## 参考项目分析

### 1. TrendRadar (https://github.com/sansan0/TrendRadar)

**核心特点**:
- AI舆论监控工具，支持多平台热点聚合
- 支持9种消息通道：WeChat, Feishu, DingTalk, Telegram, Email, ntfy, Bark, Slack
- MCP v4.0.0 集成，使用 LiteLLM (100+ AI提供商)
- 统一调度系统 (timeline.yaml)
- Docker部署友好

**消息适配设计**:
- 每个通道有特定格式指南和字节限制
  - Feishu: 30KB
  - DingTalk: 20KB
- MCP层提供 `get_channel_format_guide` 工具
- 智能批量发送，自动拆分长消息

**可借鉴点**:
- 通道格式自适应机制
- 统一调度系统设计
- 多通道管理经验

---

### 2. OpenClaw (https://github.com/openclaw/openclaw)

**核心特点**:
- 本地运行的个人AI助手
- 支持20+消息平台
- Gateway WebSocket控制平面 (ws://127.0.0.1:18789)
- Pi agent (RPC with tool/block streaming)

**Agent通信机制**:
- Session模型：`sessions_list`, `sessions_history`, `sessions_send`
- 多Agent路由：workspace隔离，per-agent sessions
- 支持voice (ElevenLabs + TTS)
- 支持Canvas workspace

**消息平台支持**:
| 平台 | 库 |
|------|-----|
| WhatsApp | Baileys |
| Telegram | grammY |
| Slack | Bolt |
| Discord | discord.js |
| Signal | signal-cli |
| iMessage | BlueBubbles |

**可借鉴点**:
- Gateway架构模式
- Session通信模型
- 多平台适配器设计模式

---

## 最佳实践

### 1. MCP Server 实现

**官方文档**: https://modelcontextprotocol.io/docs

**技术选型**:
- Python: 使用 `FastMCP` (推荐)
- TypeScript: 使用 `@modelcontextprotocol/sdk`

**关键点**:
- STDIO传输: 不能使用 `print()`，必须用 `sys.stderr`
- HTTP传输: 标准输出日志可用
- 工具定义: 使用类型提示和docstring自动生成

**示例代码**:
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
async def search_web(query: str, engine: str = "tavily") -> str:
    """搜索工具

    Args:
        query: 搜索关键词
        engine: 搜索引擎 (tavily/google/ddg)
    """
    # 实现逻辑
    pass
```

---

### 2. Docker 代理配置

**官方文档**: https://docs.docker.com/network/proxy/

**方法**:
1. 在 `~/.docker/config.json` 配置
2. 使用环境变量 `HTTP_PROXY`, `HTTPS_PROXY`
3. Docker自动设置大小写版本

**注意事项**:
- 代理配置存储为明文，注意安全
- 只对新容器生效
- 使用 `--build-arg` 传递构建时代理

---

### 3. Telegram Bot API

**官方文档**: https://core.telegram.org/bots/api

**关键点**:
- Token通过 @BotFather 获取
- Webhook端口: 443, 80, 88, 8443
- 支持4种参数传递方式
- Update类型: `message`, `edited_message`, `callback_query`, `inline_query`

**推荐库**: grammY (Python/TypeScript)

---

### 4. 飞书开放平台

**官方文档**: https://open.feishu.cn/

**关键点**:
- 需要创建企业应用获取 App ID 和 App Secret
- 使用 Webhook 接收消息
- 消息体使用 JSON 格式

---

## 技术方案对比

| 方面 | 方案A (推荐) | 方案B | 方案C |
|------|-------------|-------|-------|
| Agent通信 | MCP Server | Session Model | Event-Driven |
| 消息路由 | Gateway WebSocket | Session路由 | Message Broker |
| 代理配置 | 环境变量 | sing-box | v2ray |
| 实现难度 | 中 | 低 | 高 |
| 扩展性 | 好 | 中 | 最好 |

---

## 五、Agentic AI 架构模式 (2025最新)

### 5.1 Ali Shamaei - 核心执行模式

**来源**: [The Architecture Behind Autonomous AI Agents](https://ashamaei.medium.com/the-architecture-behind-autonomous-ai-agents-core-execution-patterns-c9eead631f79)

| 模式 | 描述 | 当前项目 |
|------|------|---------|
| **Reflection** | 自我反思和评估 | ✅ 已实现 (HeartbeatStep.SELF_REFLECTION) |
| **Routing** | 动态路由到专家 | ✅ 已实现 |
| **Parallelisation** | 并行执行独立任务 | ⚠️ 部分实现 |
| **Tool Use** | 外部工具调用 | ✅ 已实现 (MCP Tools) |
| **Planning** | 分解复杂目标 | ❌ 缺失 |
| **Multi-Agent Collaboration** | 多Agent协作 | ⚠️ 已实现框架 |

### 5.2 腾讯云 - 自进化机制

**来源**: [How to implement the self-evolution mechanism of AI Agent?](https://www.tencentcloud.com/techpedia/126465)

**6大核心组件**:
1. **Continuous Learning** - 实时或周期性学习
2. **Feedback Loop** - 用户反馈/奖励信号
3. **Memory & Knowledge** - 短期/长期记忆
4. **Meta-Learning** - 学习如何学习
5. **Self-Reflection** - 周期性自我评估
6. **Autonomous Goal Setting** - 动态目标设定

**实施步骤**:
1. 设计模块化架构
2. 集成在线学习算法
3. 嵌入反馈机制
4. 启用记忆系统
5. 应用元学习
6. 部署自监控工具
7. 确保安全和对齐

---

## 七、用户反馈系统最佳实践

### 7.1 Datagrid 7条建议

**来源**: [7 Tips to Build Self-Improving AI Agents](https://www.datagrid.com/blog/7-tips-build-self-improving-ai-agents-feedback-loops)

| 建议 | 描述 |
|------|------|
| Tip #1 | Safe Memory Evolution - 版本控制、验证、隔离 |
| Tip #2 | Validate Feedback Quality - 多步验证、路由到正确组件 |
| Tip #3 | Safe Planning Evolution - 隔离规划模块、渐进式部署 |
| Tip #4 | Monitor Reasoning Chain - 完整可观测性 |
| Tip #5 | Tool-Use Evolution - 工具使用反馈边界 |

### 7.2 腾讯云 - 用户反馈机制

**来源**: [How can AI agents continuously improve through user feedback?](https://www.tencentcloud.com/techpedia/126688)

**用户反馈类型**:
1. **显式反馈** - 用户直接评价（评分、 thumbs up/down）
2. **隐式反馈** - 用户行为分析（停留时间、再次访问）

**反馈收集机制**:
1. 会话结束时的评分请求
2. 实时满意度按钮
3. 行为数据采集

---

## 九、自监控与自愈系统

### 9.1 Self-Healing AI Agents

**来源**: [How Self-Healing AI Agents Are Revolutionizing IT](https://web.superagi.com/how-self-healing-ai-agents-are-revolutionizing-it-healthcare-and-manufacturing-real-world-case-studies/)

**核心能力**:
1. **自主监控与诊断** - 监控系统状态，诊断问题
2. **自动修复** - 实施修复措施
3. **持续优化** - 从经验中学习改进

### 9.2 实施模式

| 模式 | 描述 | 当前实现 |
|------|------|---------|
| 健康检查 | 定期检查系统组件状态 | ✅ SocialMaintenanceTask |
| 错误分析 | 分析错误模式 | ✅ SelfReflectionTask |
| 技能更新 | 动态加载新技能 | ✅ SkillUpdateTask |
| 告警通知 | 系统异常告警 | ✅ NotificationCheckTask |
| 知识积累 | 保存学习成果 | ✅ KnowledgeOutputTask |

---

## 八、可观测性系统最佳实践

### 8.1 Microsoft AI Agents for Beginners

**来源**: [AI Agents in Production: Observability & Evaluation](https://microsoft.github.io/ai-agents-for-beginners/10-ai-agents-production/)

**核心可观测性指标**:
1. **延迟 (Latency)** - 请求响应时间
2. **错误率 (Error Rate)** - 失败请求百分比
3. **工具调用成功率** - 外部工具调用成功率
4. **Token使用量** - 成本追踪
5. **路由决策准确率** - 路由质量评估

### 8.2 LangChain 生产监控

**来源**: [Agent Observability](https://www.langchain.com/conceptual-guides/production-monitoring)

**与传统可观测性的区别**:
- Agent需要追踪输入→推理→输出完整链路
- 需要记录每个tool call的输入输出
- 需要追踪状态变化和决策点

### 8.3 十大关键指标

**来源**: [Top 10 Metrics for AI Agent Performance](https://dev.to/kuldeep_paul/top-10-metrics-to-monitor-for-reliable-ai-agent-performance-4b36)

| 指标 | 描述 |
|------|------|
| 1. Request Latency | 请求延迟 |
| 2. Error Rate | 错误率 |
| 3. Tool Call Success Rate | 工具调用成功率 |
| 4. Token Usage | Token使用量 |
| 5. Cost per Request | 单次请求成本 |
| 6. Routing Accuracy | 路由准确率 |
| 7. User Satisfaction | 用户满意度 |
| 8. Recovery Time | 故障恢复时间 |
| 9. Throughput | 吞吐量 |
| 10. Queue Depth | 队列深度 |

### 🔴 P0 - 致命问题

| 问题 | 位置 | 描述 |
|------|------|------|
| 变量未定义 | main.py:46 | `feishu_config` 在定义前使用 |
| 模块未集成 | main.py | HeartbeatEngine等4个核心模块未启动 |
| 持久化缺失 | docker-compose.yml | .learnings目录未挂载 |

### 🟡 P1 - 重要问题

| 问题 | 描述 |
|------|------|
| 全局单例 | 难以测试，状态难以控制 |
| Stub实现 | Heartbeat各task是模拟数据 |
| 缺少Planning | 未实现复杂目标分解 |

**选择方案A (Gateway + MCP)** 理由:
1. MCP是标准协议，生态成熟
2. 参考TrendRadar已有成功案例
3. Docker部署友好
4. 扩展Agent能力简单

---

## 十、代码质量最佳实践

### 10.1 Python PEP 8 异常处理

**原则**: 永远不要使用 `except:` 捕获所有异常

**错误示例**:
```python
# ❌ 错误 - 捕获所有异常
try:
    do_something()
except:
    handle_error()
```

**正确示例**:
```python
# ✅ 正确 - 指定具体异常类型
try:
    do_something()
except (ValueError, TypeError) as e:
    handle_error()
```

**理由**:
1. 捕获 KeyboardInterrupt, SystemExit 会导致程序无法正常退出
2. 隐藏真实错误，增加调试难度
3. 不符合 Python 之禅 "Explicit is better than implicit"

### 10.2 依赖注入 vs 全局单例

**问题**: 全局单例导致难以测试

**改进方案** - 依赖注入:
```python
# ❌ 全局单例
_service = None
def get_service():
    global _service
    if _service is None:
        _service = Service()
    return _service

# ✅ 依赖注入
class Application:
    def __init__(self, service: Service = None):
        self.service = service or Service()
```

### 10.3 模块内导入

**原则**: 在模块顶部导入依赖，不在函数内导入

**错误示例**:
```python
# ❌ 函数内导入
def execute():
    from module import something
    ...
```

**正确示例**:
```python
# ✅ 模块顶部导入
from module import something

def execute():
    ...
```

### 10.4 懒加载模式 (Lazy Loading)

**场景**: 避免循环导入，或延迟加载重型模块

**实现**:
```python
class LazyLoader:
    """懒加载器 - 避免在函数内部导入模块"""
    _cache: Dict[str, Any] = {}

    @classmethod
    def get(cls, module_path: str, attr: str = None):
        """懒加载模块"""
        key = f"{module_path}:{attr}" if attr else module_path
        if key not in cls._cache:
            try:
                import importlib
                module = importlib.import_module(module_path)
                cls._cache[key] = getattr(module, attr) if attr else module
            except ImportError as e:
                cls._cache[key] = None
                logger.warning(f"懒加载失败 {module_path}: {e}")
        return cls._cache[key]

# 使用示例
def execute():
    search_web = LazyLoader.get("src.mcp.tools.search", "search_web")
    if search_web:
        results = await search_web(query)
```

**优点**:
1. 避免循环导入
2. 延迟加载重型模块（减少启动时间）
3. 保持模块顶部导入的代码风格

---

## 十一、最新行业研究 (2025)

### 11.1 Google A2A Protocol

**来源**: https://github.com/a2aproject/A2A

**核心概念**:
- **Agent Card**: JSON 格式描述 Agent 能力
- **Task**: 跨 Agent 任务传递
- **Message**: Agent 间消息格式

**Agent Card 示例**:
```json
{
  "version": "1.0",
  "name": "TrendRadar Agent",
  "description": "获取科技趋势情报",
  "skills": [
    {"id": "tech_trends", "name": "科技趋势分析"}
  ],
  "endpoint": "http://trendradar:8080/a2a"
}
```

**A2A vs MCP**:
| 维度 | A2A | MCP |
|------|-----|-----|
| 用途 | Agent 间通信 | Agent ↔ 工具 |
| 模式 | 异步任务 | 函数调用 |
| 状态 | Task lifecycle | 无状态 |

---

### 11.2 AutoGen 多 Agent 对话

**来源**: https://microsoft.github.io/autogen/0.2/docs/Use-Cases/agent_chat

**核心模式**:
```python
from autogen import ConversableAgent

agent = ConversableAgent(
    name="assistant",
    llm_config=llm_config,
    function_map={"get_weather": get_weather}
)

# 消息进入 Agent 对话，Agent 可以多轮交互、调用工具
result = await agent.a_generate_reply(messages=[user_message])
```

**关键特性**:
- Shared state management across agents
- Group chat for multi-agent collaboration
- Memory module for context persistence

---

### 11.3 用户反馈学习系统

**来源**: https://medium.com/@nomannayeem/lets-build-a-self-improving-ai-agent-that-learns-from-your-feedback-722d2ce9c2d9

**实现模式**:
```python
class FeedbackLearner:
    async def process_feedback(self, feedback: UserFeedback):
        # 1. 记录反馈
        await self.store.save(feedback)

        # 2. 负面反馈触发反思
        if feedback.feedback_type == FeedbackType.THUMBS_DOWN:
            await self._analyze_failure(feedback)

        # 3. 纠正更新知识库
        if feedback.feedback_type == FeedbackType.CORRECTION:
            await self._update_knowledge(feedback)
```

---

### 11.4 情报评分系统

**评分公式**:
```
情报价值 = f(时效性, 相关性, 置信度, 用户兴趣匹配)

score = recency * 0.2 + topic_match * 0.4 + credibility * 0.3 + feedback_adj * 0.1
```

**实现要点**:
1. **时效性**: 发布时间距离当前的小时数
2. **主题匹配**: 情报主题与用户兴趣的重叠度
3. **来源置信度**: 来源可信度评分
4. **历史反馈**: 用户对该类型情报的历史反馈调整

---

## 十二、架构问题诊断

### 🔴 P0 - 致命问题

| 问题 | 位置 | 描述 |
|------|------|------|
| 消息→Agent 断裂 | pipeline.py | 消息直接路由，无 Agent 消化 |
| 反馈未闭环 | feedback/ | FeedbackService 存在但无收集入口 |
| 情报→推送断裂 | heartbeat/push | 两系统独立，无价值评估连接 |
| A2A 协议缺失 | agent_comm/ | 无标准化 Agent 通信 |

### 🟡 P1 - 重要问题

| 问题 | 描述 |
|------|------|
| 会话持久化 | 内存存储，重启丢失 |
| 用户画像 | 无个性化学习 |
| 流式输出 | 阻塞等待完整响应 |

---

## 十三、飞书长连接 + Mihomo 代理研究

### 1. 飞书 WebSocket 长连接机制

**关键发现**：
- OpenClaw/TrendRadar 使用 `@larksuiteoapi/node-sdk`（Node.js 版本）
- 核心是 `WSClient.start()` 建立**出站连接**到 `wss://msg-frontier.feishu.cn`
- 这是**客户端主动连接**，不需要公网 IP

**Python SDK 问题**：
- `lark_oapi` Python SDK API 与 Node.js 版本完全不同
- 需要使用 `ws.Client` 类（不是 `client.Client`）
- 事件处理器需要继承 `EventDispatcherHandler`

**测试结果**：
```
✅ connected to wss://msg-frontier.feishu.cn/ws/v2?...
✅ ping success
✅ receive pong
```

### 2. mihomo 代理模式

**代理协议**：
- HTTP 代理：端口 9090
- SOCKS5 代理：端口 7890

**路由策略**：
- 域名规则：proxy_domains / direct_domains
- GeoIP：判断目标 IP 是否在中国大陆
- 混合模式：域名优先，fallback 用 GeoIP

### 3. 项目现有组件

- `ProxyManager`: 已有域名规则路由
- `FeishuAdapter`: 已支持 webhook 和 websocket 模式
- `FeishuWebSocketClient`: 已实现但有同步/异步问题

### 4. 行业参考

- Clash.Meta: mihomo 是 Clash.Meta 的 Go 实现
- 代理自动选择：类似 Surge、Shadowrocket 的 "代理规则"
- 混合模式：常见于科学上网工具

### 5. 技术挑战

1. asyncio 冲突：lark_oapi SDK 内部使用 `run_until_complete`
2. 代理判断：需要高效判断域名/IP 是否需要代理
3. 连接管理：长连接需要心跳维护

### 7. RSS 源集成

**来源**:
- WorldMonitor: 435+ 精选 RSS 源
- TrendRadar: 中文热榜

**集成的分类**:
- geopolitics: 世界政治
- military: 军事
- cyber: 网络安全
- tech: 科技
- finance: 经济
- science: 科学
- china: 中国
- social: 社交媒体热榜

**统计**:
- 300+ RSS 源
- 支持中英文
- Tier 1-3 信任层级

### 8. ArXiv 论文源增强

**ArXiv API**:
- 基础 URL: `http://export.arxiv.org/api/query`
- 支持分类: cs.AI, cs.LG, cs.CL, cs.CV 等

**处理流程**:
```
获取论文 → 翻译标题 → 总结摘要 → 推送
```

### 9. BettaFish + MiroFish 研究

**BettaFish**:
- 舆情分析系统，多智能体协同
- 功能: 爬虫 + 分析 + 报告
- 架构: Python + Flask

**MiroFish**:
- AI 预测引擎，多智能体仿真
- 功能: 仿真 + 预测 + 推演
- 架构: Python + Vue
- Stars: 6.6k

**集成方案**:
- 独立 Docker 容器
- REST API 对接
- Docker Network 通信

### 6. Docker 网络架构

**方案变更**：由于 mihomo 在另一个 Docker Compose 的子网，用户要求自行创建代理服务。

**实现方案**：
- 在 docker-compose.yml 中添加 mihomo 服务
- 使用 host 网络模式让 mihomo 直接访问外网
- gateway 容器通过 Docker 网络连接到 mihomo
- 配置 HTTP_PROXY/HTTPS_PROXY 环境变量

**Vmess 节点配置**：
```
服务器: c59s3.portablesubmarines.com
端口: 16255
UUID: 917f15f7-e9b8-47b3-87df-51b36fe63e8b
协议: TCP + TLS
跳过证书验证: true
```

**最终网络架构**：
```
NAS (192.168.1.2)           本地 Mac / Docker Container
┌──────────────┐             ┌─────────────────────────┐
│   mihomo    │             │    gateway container    │
│  port:7890  │◀── proxy ──▶│ HTTP_PROXY env var    │
│  port:9090  │             │                        │
└──────────────┘             └─────────────────────────┘
       │                             │
       │                             │
       ▼                             ▼
   外部网络                   ┌─────────────────────────┐
   (Vmess)                  │ 飞书/百度直连          │
                            │ (NO_PROXY 配置)        │
                            └─────────────────────────┘
```

**配置更新**：
1. docker-compose.yml - 指向 NAS mihomo
2. .env - HTTP_PROXY/HTTPS_PROXY 指向 192.168.1.2:7890
3. config/proxy.yaml - mihomo 配置更新

---

## 十四、S3/RustFs + PostgreSQL + 向量存储集成 (2026-03-08)

### 14.1 配置信息

**PostgreSQL + pgvector (NAS)**:
```
DATABASE_URL=postgresql://postgres:postgres@192.168.1.2:45041/bs_generator_db
PG_HOST=192.168.1.2
PG_PORT=45041
PG_USER=postgres
PG_PASSWORD=postgres
PG_DB_NAME=intelligence_db
```

**S3/RustFs Storage (NAS)**:
```
S3_ENDPOINT_URL=http://192.168.1.2:37163
S3_ACCESS_KEY=7BG4U5KOh2dAkjeFlbcQ
S3_SECRET_KEY=seIUqnd9YrMf0vbSz5c1iFAoJQDpwOEH6ZGPVgC2
S3_BUCKET_NAME=mightyoung
S3_REGION_NAME=us-east-1
```

**Redis (NAS)**:
```
REDIS_HOST=192.168.1.2
REDIS_PORT=40967
REDIS_DB=0
```

### 14.2 新增模块

**存储模块** (`src/storage/`):
- `s3_client.py` - S3/RustFs 客户端
- `postgres_client.py` - PostgreSQL + pgvector 客户端
- `redis_client.py` - Redis 客户端
- `md_generator.py` - Markdown 文件生成器

### 14.3 tech-news-digest 技能

**已安装**: `draco-agent/tech-news-digest@tech-news-digest`

功能:
- 151 个数据源 (RSS, Twitter, GitHub, Reddit)
- 质量评分与去重
- 多格式输出 (Discord/Email/PDF)

位置: `~/.agents/skills/tech-news-digest`

### 14.4 InfoID 设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           InfoID 结构 (64-bit)                         │
├────────────┬──────────┬────────────┬────────────┬──────────────────────┤
│ 时间戳      │ 类型ID   │ 来源ID     │ 序列号     │ 校验码              │
│ (41 bits)  │ (8 bits) │ (6 bits)   │ (8 bits)   │ (1 bit)             │
└────────────┴──────────┴────────────┴────────────┴──────────────────────┘
```

| 字段 | 长度 | 说明 | 示例 |
|------|------|------|------|
| 时间戳 | 41 bits | 毫秒级时间戳 | 2026-03-08 10:30:00 |
| 类型ID | 8 bits | 信息类型 (0-255) | 1=RSS, 2=用户输入, 3=BettaFish, 4=MiroFish |
| 来源ID | 6 bits | 来源系统 (0-63) | 1=微博, 2=知乎, 3=RSS, 4=飞书 |
| 序列号 | 8 bits | 同一毫秒内序列 (0-255) | 自动递增 |
| 校验码 | 1 bit | CRC 校验 | 0 |

### 14.5 用户触发机制

```python
COMMAND_PATTERNS = {
    "bettafish": [
        r"对(.+?)利用bettafish进行深入分析",
        r"bettafish分析(.+)",
    ],
    "mirofish": [
        r"对(.+?)利用mirofish进行预测性分析",
        r"mirofish预测(.+)",
    ],
}
```

### 14.6 依赖更新

新增 Python 包:
- boto3>=1.34.0
- psycopg2-binary>=2.9.9
- redis>=5.0.0

---

## 十五、Agent 系统提示词优化 (2026-03-09)

### 15.1 行业最佳实践参考

分析了以下顶级 AI Agent 的系统提示词:
- **Claude Code** (Anthropic): 简洁、直接、任务导向
- **Cursor Agent 2.0**: 详细工具定义、输出格式规范
- **Manus**: 角色定义、能力描述、限制说明
- **Windsurf**: 多步骤指导、示例驱动

### 15.2 优化要点

| 优化项 | 之前 | 之后 |
|--------|------|------|
| 角色定义 | 简单一句 | 完整角色描述 |
| 输出格式 | 无规范 | JSON Schema + 示例 |
| 项目上下文 | 缺失 | 包含项目背景 |
| 约束说明 | 无 | 明确约束条件 |
| Agent 列表 | 3 个 | 6 个 (含 bettafish/mirofish) |

### 15.3 新增模块

**文件**: `src/prompts/__init__.py`

包含以下提示词:
- `INTENT_ROUTER_PROMPT` - 意图路由
- `INTELLIGENCE_ANALYZER_PROMPT` - 情报分析
- `TRANSLATOR_PROMPT` - 翻译助手
- `README_SUMMARIZER_PROMPT` - README 摘要
- `BETTAFISH_ANALYZER_PROMPT` - 舆情分析
- `MIROFISH_PREDICTOR_PROMPT` - 预测分析
- `LLM_AGENT_PROMPT` - 通用 LLM

### 15.4 更新的文件

| 文件 | 更新内容 |
|------|----------|
| `src/router/ai_router.py` | 使用优化后的意图路由提示词 |
| `src/intelligence/analyzer.py` | 使用优化后的分析和翻译提示词 |
| `src/agents/llm_agent.py` | 使用优化后的通用助手提示词 |

### 15.5 示例: 意图路由提示词

```python
INTENT_ROUTER_PROMPT = """# 消息路由助手

## 角色定义
你是一个智能消息路由器，负责分析用户消息并将任务分配给最合适的 AI Agent。

## 项目上下文
- 项目名称: message-integrate-agent
- 功能: 连接 Telegram、飞书、微信的消息中枢

## 可用 Agent
| Agent | 描述 | 适用场景 |
|-------|------|----------|
| llm | 对话型 AI | 问答、翻译 |
| search | 搜索 Agent | 天气、新闻 |
| intelligence | 情报分析 | 趋势分析 |
| bettafish | 舆情深度分析 | 情感分析 |
| mirofish | 预测性分析 | 趋势预测 |

## 输出格式
```json
{
    "agent": "llm|search|intelligence|bettafish|mirofish",
    "action": "具体动作名称",
    "reasoning": "简短推理说明",
    "confidence": 0.0-1.0
}
```
```"""

---

## 十五、GitHub Trending + README 摘要 (2026-03-09)

### 15.1 GitHub Trending 数据源

**新增模块**: `src/intelligence/github_trending.py`

功能:
- 获取 GitHub 热门仓库 (按主题: llm, ai-agent, crypto, frontier-tech)
- 按星数排序
- 估算每日星数增长

**搜索查询**:
```python
TRENDING_QUERIES = [
    {"topic": "llm", "q": "llm large-language-model in:topics,name,description"},
    {"topic": "ai-agent", "q": "ai-agent autonomous-agent in:topics,name,description"},
    {"topic": "crypto", "q": "blockchain ethereum solidity defi in:topics,name,description"},
    {"topic": "frontier-tech", "q": "machine-learning deep-learning in:topics,name,description"},
]
```

### 15.2 README 摘要生成

**新增模块**: `src/intelligence/readme_fetcher.py`

功能:
- 自动获取仓库 README.md 内容
- 使用 LLM 生成项目简要说明
- 支持批量获取

**使用示例**:
```python
from src.intelligence import GitHubTrendingFetcher, ReadmeFetcher, ReadmeSummarizer

# 获取 Trending
fetcher = GitHubTrendingFetcher()
repos = fetcher.fetch()

# 获取 README 并生成摘要
readme_fetcher = ReadmeFetcher()
summarizer = ReadmeSummarizer(llm_client)

for repo in repos[:5]:
    readme = readme_fetcher.fetch(repo.repo)
    if readme:
        summary = summarizer.summarize(readme, repo.name)
        repo.summary = summary
```

### 15.3 MD 生成器更新

**更新文件**: `src/storage/md_generator.py`

新增方法:
- `generate_github_trending()` - 生成 GitHub Trending 摘要

### 15.4 环境变量

```bash
# GitHub Token (可选，提高 API 限制)
GITHUB_TOKEN=
```

---

## 十六、Summarize CLI 集成 (2026-03-09)

### 16.1 功能特性

基于 [summarize-1.0.0 skill](https://summarize.sh) 集成，提供:

- **URL 总结** - 网页内容摘要
- **文件总结** - PDF、图片、音频文件
- **YouTube 总结** - 视频内容摘要
- **Firecrawl 支持** - 抓取被屏蔽的网站
- **Apify 支持** - YouTube 抓取 fallback

### 16.2 使用方法

```python
from src.intelligence import SummarizeClient, create_summarize_client

# 创建客户端
client = create_summarize_client(
    model="google/gemini-2.0-flash-exp",
    api_key="your-api-key",
    firecrawl_api_key="your-firecrawl-key",  # 可选
    apify_api_token="your-apify-token",       # 可选
)

# 总结 URL
result = await client.summarize_url(
    "https://example.com",
    length="medium",
    firecrawl="auto",  # auto/off/always
)

# 总结 YouTube
result = await client.summarize_youtube(
    "https://youtu.be/xxx",
    length="medium",
    use_apify=True,
)

# 总结文件
result = await client.summarize_file(
    "/path/to/file.pdf",
    length="medium",
)

# JSON 格式输出
result = await client.summarize_json(url="https://example.com")
```

### 16.3 支持的 LLM 模型

| 模型 | 环境变量 |
|------|----------|
| Google Gemini | `GEMINI_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| xAI | `XAI_API_KEY` |

### 16.4 配置文件

可选配置文件: `~/.summarize/config.json`

```json
{
    "model": "google/gemini-2.0-flash-exp"
}
```

### 16.5 安装

```bash
# macOS
brew install steipete/tap/summarize

# 验证
summarize --version
```

---

## 十七、NAS 部署手册 (2026-03-09)

### 17.1 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAS (192.168.1.2)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ PostgreSQL  │  │    Redis   │  │    S3/RustFs Storage   │ │
│  │  :45041     │  │   :40967   │  │      :37163            │ │
│  │ + pgvector  │  │             │  │   (mightyoung bucket)  │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│         │                │                      │                 │
│         └────────────────┼──────────────────────┘                 │
│                          │                                        │
│                    ┌─────▼─────┐                                  │
│                    │  mihomo   │  (代理服务 :7890)                │
│                    │  :7890    │                                  │
│                    └───────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Docker 容器
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Container                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              message-hub-gateway                         │   │
│  │  - FastAPI Gateway (:8080/8081)                         │   │
│  │  - Agent Pool                                           │   │
│  │  - Intelligence Pipeline                                │   │
│  │  - Feishu/Telegram Adapter                             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 17.2 NAS 服务前置要求

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL + pgvector | 45041 | 向量数据库 |
| Redis | 40967 | 缓存、会话 |
| S3/RustFs | 37163 | MD 文件存储 |
| mihomo | 7890 | HTTP/HTTPS 代理 |

### 17.3 部署文件

- `docs/deployment-nas.md` - 完整部署手册
- `scripts/deploy-nas.sh` - 快速部署脚本

### 17.4 快速部署

```bash
# 1. 复制配置
cp .env.example .env
nano .env

# 2. 运行部署脚本
bash scripts/deploy-nas.sh

# 或使用 docker-compose
docker-compose up -d
```

### 17.5 验证部署

```bash
# 健康检查
curl http://localhost:8080/health

# 查看状态
curl http://localhost:8080/health/detail
```

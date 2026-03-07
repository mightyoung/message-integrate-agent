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

## 结论

**选择方案A (Gateway + MCP)** 理由:
1. MCP是标准协议，生态成熟
2. 参考TrendRadar已有成功案例
3. Docker部署友好
4. 扩展Agent能力简单

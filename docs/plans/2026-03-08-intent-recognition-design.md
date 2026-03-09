# Intent Recognition System Design - 2026-03-08

## 0. 设计优化摘要 (基于飞书自定义菜单)

**优化方案**: 引入飞书自定义菜单作为 Level 0，替代简单的语义识别

```
原设计:
  Level 1: 规则匹配     → <10ms
  Level 2: 向量语义     → 50ms
  Level 3: LLM 深度    → 300ms

优化后:
  Level 0: 飞书菜单    → <5ms  (确定性操作，100%准确)
  Level 1: 规则匹配    → <10ms
  Level 2: 向量语义    → 50ms
  Level 3: LLM 深度   → 300ms
```

**优势**:
- 确定性操作，无需理解用户意图
- 100% 准确率，无误判
- 极低延迟 <5ms
- 减少 LLM 调用，降低成本

---

## 1. 设计目标

设计一个意图识别系统，支持：
- **70% 情报反馈** (WorldMonitor + 分析)
- **30% 对话** (LLMAgent)
- **50+ 意图** 分类
- **自适应学习** (记录用户反馈)
- **多轮对话上下文**
- **PostgreSQL + pgvector + Redis** 存储

---

## 2. 行业最佳实践分析

### 2.1 顶级方案对比

| 方案 | 代表产品 | 核心特点 | 适用场景 |
|------|----------|----------|----------|
| **规则 + ML 混合** | Rasa | NLU管道：规则 → Transformer | 复杂对话系统 |
| **LLM 主导演** | GPTs / CoPilot | 动态理解 + 函数调用 | 通用对话 |
| **向量检索主导** | 定制向量库 | 语义匹配 + Top-K | 意图分类 |
| **多意图槽位填充** | Dialogflow ES | 意图 + 实体 + 槽位 | 任务型对话 |

### 2.2 关键设计模式

**分层意图识别 (Rasa 模式)**:
```
1. Rule Policy (高优先级规则) → <10ms
2. ML Policy (机器学习分类) → 50-200ms
3. Fallback (LLM 兜底) → 500ms+
```

**置信度阈值设计**:
- 置信度 > 0.85 → 直接执行
- 置信度 0.6-0.85 → 确认后执行
- 置信度 < 0.6 → LLM 兜底

**反馈循环学习** (参考项目现有 SelfLearningRouter):
- 成功案例 → 提取关键词 → 更新规则库
- 失败案例 → 记录 → 周期性分析

---

## 3. 系统架构设计

### 3.1 总体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        IntentRouter (统一入口)                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Routing Pipeline                           │   │
│  │  ┌─────────┐  ┌─────────────┐  ┌──────────┐  ┌────────┐  │   │
│  │  │  Rules  │→ │   Vector     │→ │   LLM    │→ │Fallback│  │   │
│  │  │ Fast    │  │  Semantic    │  │ Deep     │  │  (DM)  │  │   │
│  │  │ <10ms   │  │   50ms       │  │ 300ms    │  │ 500ms  │  │   │
│  │  └─────────┘  └─────────────┘  └──────────┘  └────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
        ┌───────────────────┐    ┌───────────────────────┐
        │  ContextManager   │    │  LearningEngine       │
        │  (Redis + PG)     │    │  (SelfLearningRouter) │
        └───────────────────┘    └───────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
        ┌───────────────────┐    ┌───────────────────────┐
        │  AgentCoordinator  │    │  FeedbackCollector    │
        │  - Intelligence   │    │  (User Feedback)      │
        │  - Search          │    └───────────────────────┘
        │  - LLM             │
        │  - API             │
        └───────────────────┘
```

### 3.2 核心组件

#### 3.2.1 IntentDefinition (意图定义)

```python
class IntentDefinition:
    id: str                    # intent_search_news
    name: str                  # "搜索新闻"
    description: str           # "搜索最新新闻资讯"
    agent: AgentType           # SEARCH
    keywords: List[str]        # ["新闻", "最新", "资讯"]
    patterns: List[str]       # 正则表达式
    examples: List[str]       # Few-shot examples
    required_slots: List[Slot] # 需要的槽位
    priority: int             # 优先级 (1-100)
    confidence_threshold: float # 置信度阈值
    response_template: str     # 响应模板
```

#### 3.2.2 IntentRegistry (意图注册表)

```python
class IntentRegistry:
    """50+ 意图分类"""

    # 情报类意图 (70%)
    INTELLIGENCE = {
        "view_hot_news":        # 查看热点新闻
        "filter_by_category":   # 按分类筛选
        "search_intelligence": # 搜索情报
        "get_summary":         # 获取摘要
        "translate_content":   # 翻译内容
        "analyze_trend":       # 分析趋势
        # ... 更多
    }

    # 对话类意图 (30%)
    CONVERSATION = {
        "general_chat":        # 闲聊
        "ask_question":        # 提问
        "get_help":            # 获取帮助
        # ... 更多
    }

    # 系统类意图
    SYSTEM = {
        "get_settings":        # 获取设置
        "change_settings":    # 修改设置
        "clear_history":       # 清除历史
    }
```

#### 3.2.3 MultiLevelRouter (多层路由)

```python
class MultiLevelRouter:
    """三层路由引擎"""

    async def route(
        self,
        message: str,
        user_id: str,
        context: Dict
    ) -> RoutingResult:
        # Level 1: 规则匹配 (<10ms)
        result = await self._rule_match(message)
        if result.confidence > 0.9:
            return result

        # Level 2: 向量语义匹配 (<50ms)
        result = await self._vector_match(message)
        if result.confidence > 0.85:
            return result

        # Level 3: LLM 深度理解 (<300ms)
        result = await self._llm_match(message, context)
        if result.confidence > 0.7:
            return result

        # Fallback: 降级处理
        return self._fallback(message)
```

#### 3.2.4 ContextManager (上下文管理)

```python
class ContextManager:
    """多轮对话上下文"""

    def __init__(self, redis_client, pg_pool):
        self.redis = redis_client  # 短期会话
        self.pg = pg_pool          # 长期存储

    async def get_context(
        self,
        user_id: str,
        conversation_id: str
    ) -> ConversationContext:
        # 从 Redis 获取当前会话
        # 从 PG 获取历史会话
        pass

    async def update_context(
        self,
        user_id: str,
        intent: str,
        slots: Dict
    ):
        # 更新 Redis 会话状态
        # 定期持久化到 PG
        pass
```

---

## 4. 飞书自定义菜单设计

> **⚠️ 重要限制**: 飞书菜单仅支持**一对一私聊**，不支持群聊场景。

### 4.1 菜单配置限制

| 特性 | 折叠菜单 | 悬浮菜单 |
|------|----------|----------|
| 主菜单数量 | 最多 3 个 | 最多 5 个 |
| 子菜单数量 | 每个最多 5 个 | 每个最多 10 个 |
| 飞书版本要求 | V5.27+ | V7.22+ |
| 菜单文本限制 | 最长 60 字符 | 最长 60 字符 |

**推荐配置**: 使用**折叠菜单** (Collapsible menu)，与悬浮菜单兼容。

### 4.2 菜单配置 (3 主菜单 + 13 子菜单)

```
┌─────────────────────────────────────────────────────────┐
│                    飞书机器人菜单                          │
├──────────────┬──────────────────┬─────────────────────┤
│   📰 情报    │   🔍 搜索        │    ⚙️ 设置          │
├──────────────┼──────────────────┼─────────────────────┤
│ • 热点新闻    │ • 搜索新闻       │ • 获取当前配置       │
│ • 科技动态    │ • 搜索资讯       │ • 切换推送频率       │
│ • AI 进展    │ • 搜索趋势       │ • 语言设置          │
│ • 投资并购    │ • 高级搜索       │ • 清除会话历史       │
│ • 行业报告    │                  │                     │
└──────────────┴──────────────────┴─────────────────────┘
```

### 4.3 配置步骤 (飞书开放平台操作)

#### Step 1: 进入开发者控制台

1. 访问 [飞书开发者控制台](https://open.feishu.cn/app)
2. 选择已创建的应用或创建新应用
3. 点击应用图标进入应用详情页

#### Step 2: 添加机器人能力

1. 在左侧导航栏点击 **添加应用能力**
2. 点击 **Bot** 下的 **添加能力** 按钮

#### Step 3: 启用自定义菜单

1. 在 Bot 能力配置页面，点击 **Bot 自定义菜单** 旁的 **编辑** 按钮
2. 将菜单状态切换为 **已启用**
3. 选择菜单显示样式:
   - **折叠菜单** (推荐): 菜单选项位于输入框左侧区域
   - **悬浮菜单**: 菜单选项持续显示在输入框上方

#### Step 4: 配置菜单项

```
主菜单 1: 📰 情报
├── 热点新闻       (event_id: menu_intelligence_hot)
├── 科技动态       (event_id: menu_intelligence_tech)
├── AI进展         (event_id: menu_intelligence_ai)
├── 投资并购       (event_id: menu_intelligence_investment)
└── 行业报告       (event_id: menu_intelligence_report)

主菜单 2: 🔍 搜索
├── 搜索新闻       (event_id: menu_search_news)
├── 搜索资讯       (event_id: menu_search_info)
├── 搜索趋势       (event_id: menu_search_trend)
└── 高级搜索       (event_id: menu_search_advanced)

主菜单 3: ⚙️ 设置
├── 获取当前配置   (event_id: menu_settings_get)
├── 切换推送频率   (event_id: menu_settings_frequency)
├── 语言设置       (event_id: menu_settings_language)
└── 清除会话历史   (event_id: menu_settings_clear)
```

**动作类型选择**: 选择 **推送事件 (Push event)**，这样用户点击菜单时会向服务器发送事件。

#### Step 5: 发布应用版本

1. 创建新应用版本
2. 发布版本使配置生效
3. **⚠️ 等待 5 分钟**后菜单才会显示

---

### 4.4 事件订阅配置

#### Step 1: 订阅菜单事件

在开发者控制台 → 事件订阅页面，添加以下事件:

```
事件名称: Bot 自定义菜单事件 (im.menu)
事件ID: im.menu
```

#### Step 2: 配置请求 URL

将事件请求 URL 设置为:
```
https://your-server.com/webhook/feishu
```

---

### 4.5 服务器端实现

#### 4.5.1 菜单事件处理器

```python
class FeishuMenuHandler:
    """飞书菜单事件处理器"""

    # 菜单 ID 到意图的映射
    MENU_MAPPING = {
        # 主菜单: 情报
        "menu_intelligence_hot": {
            "intent": "view_hot_news",
            "agent": "intelligence",
            "params": {"category": "hot"}
        },
        "menu_intelligence_tech": {
            "intent": "view_category_news",
            "agent": "intelligence",
            "params": {"category": "tech"}
        },
        "menu_intelligence_ai": {
            "intent": "view_category_news",
            "agent": "intelligence",
            "params": {"category": "ai"}
        },
        "menu_intelligence_investment": {
            "intent": "view_category_news",
            "agent": "intelligence",
            "params": {"category": "investment"}
        },
        "menu_intelligence_report": {
            "intent": "view_category_news",
            "agent": "intelligence",
            "params": {"category": "report"}
        },

        # 主菜单: 搜索
        "menu_search_news": {
            "intent": "search_intelligence",
            "agent": "search",
            "params": {"type": "news"}
        },
        "menu_search_info": {
            "intent": "search_intelligence",
            "agent": "search",
            "params": {"type": "info"}
        },
        "menu_search_trend": {
            "intent": "search_intelligence",
            "agent": "search",
            "params": {"type": "trend"}
        },
        "menu_search_advanced": {
            "intent": "search_advanced",
            "agent": "search",
            "params": {}
        },

        # 主菜单: 设置
        "menu_settings_get": {
            "intent": "get_settings",
            "agent": "system",
            "params": {}
        },
        "menu_settings_frequency": {
            "intent": "change_settings",
            "agent": "system",
            "params": {"key": "frequency"}
        },
        "menu_settings_language": {
            "intent": "change_settings",
            "agent": "system",
            "params": {"key": "language"}
        },
        "menu_settings_clear": {
            "intent": "clear_history",
            "agent": "system",
            "params": {}
        },
    }

    async def handle_menu_event(
        self,
        event: Dict[str, Any]
    ) -> Optional[IntentResult]:
        """处理菜单点击事件

        事件结构:
        {
            "event": {
                "type": "im.menu",
                "menu_event": {
                    "chat_id": "oc_xxx",
                    "user_id": "ou_xxx",
                    "menu_event_id": "menu_intelligence_hot"  # 菜单项ID
                }
            }
        }
        """
        menu_event = event.get("event", {}).get("menu_event", {})
        menu_id = menu_event.get("menu_event_id", "")

        if not menu_id:
            logger.warning("Menu event missing menu_event_id")
            return None

        if menu_id not in self.MENU_MAPPING:
            logger.warning(f"Unknown menu: {menu_id}")
            return None

        config = self.MENU_MAPPING[menu_id]
        user_id = menu_event.get("user_id", "")

        logger.info(f"Menu clicked: {menu_id} by user {user_id}")

        # 返回意图结果 (100% 置信度)
        return IntentResult(
            intent=config["intent"],
            agent=config["agent"],
            params=config["params"],
            confidence=1.0,
            source="menu",
            user_id=user_id
        )
```

#### 4.5.2 在 FeishuAdapter 中集成

```python
class FeishuAdapter(BaseAdapter):
    """飞书适配器 - 集成菜单事件处理"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # ... 其他初始化
        self.menu_handler = FeishuMenuHandler()

    async def handle_webhook(self, payload: Dict[str, Any]) -> Optional[AdapterMessage]:
        """处理飞书 webhook 事件"""
        event_type = payload.get("type")

        # 处理菜单事件
        if event_type == "im.menu":
            return await self._handle_menu_event(payload)

        # 处理消息事件
        if event_type == "callback":
            return await self._handle_message_callback(payload)

        return None

    async def _handle_menu_event(
        self,
        payload: Dict[str, Any]
    ) -> Optional[AdapterMessage]:
        """处理菜单点击事件"""
        # 解析菜单事件
        menu_event = payload.get("event", {})
        menu_type = menu_event.get("type")

        if menu_type == "im.menu":
            menu_data = menu_event.get("menu_event", {})

            # 获取意图结果
            intent_result = await self.menu_handler.handle_menu_event(payload)

            if intent_result:
                # 执行意图
                response = await self._execute_intent(intent_result)

                # 发送响应消息
                await self.send_message(
                    chat_id=intent_result.user_id,  # 私聊
                    content=response
                )

        return None
```

#### 4.5.3 菜单事件 webhook 格式

飞书发送的菜单事件格式:

```json
{
    "schema": "2.0",
    "header": {
        "event_id": "evt_xxx",
        "event_type": "im.menu",
        "token": "xxx",
        "create_time": "1701234567890",
        "token_type": "tenant_access_token"
    },
    "event": {
        "type": "im.menu",
        "menu_event": {
            "chat_id": "oc_631c2295e3b354931a9e450cad99c9f2",
            "user_id": "ou_123456789",
            "menu_event_id": "menu_intelligence_hot"
        }
    }
}
```

---

### 4.6 优化后的路由管道

```python
class MultiLevelRouter:
    """优化后的多层路由引擎"""

    async def route(
        self,
        message: str,
        user_id: str,
        context: Context,
        menu_source: str = None  # 新增: 菜单来源
    ) -> RoutingResult:
        # Level 0: 菜单点击 (最高优先级，100% 准确)
        if menu_source:
            return await self._handle_menu_source(menu_source, user_id)

        # Level 1: 规则匹配 (<10ms)
        result = await self._rule_match(message)
        if result.confidence > 0.9:
            return result

        # Level 2: 向量语义匹配 (<50ms)
        result = await self._vector_match(message)
        if result.confidence > 0.85:
            return result

        # Level 3: LLM 深度理解 (<300ms)
        result = await self._llm_match(message, context)
        if result.confidence > 0.7:
            return result

        # Fallback: 降级处理
        return self._fallback(message)
```

---

### 4.7 配置检查清单

```
□ 1. 在飞书开发者控制台启用 Bot 能力
□ 2. 配置自定义菜单 (3主菜单 + 13子菜单)
□ 3. 选择菜单动作为"推送事件"
□ 4. 订阅 "im.menu" 事件
□ 5. 配置事件请求 URL
□ 6. 创建并发布应用版本
□ 7. 等待 5 分钟使配置生效
□ 8. 服务器端实现菜单事件处理
□ 9. 测试菜单点击响应
```

---

### 4.8 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 菜单不显示 | 版本过低 | 升级到 V5.27+ (折叠菜单) 或 V7.22+ (悬浮菜单) |
| 菜单不显示 | 未发布版本 | 创建并发布应用版本 |
| 菜单不显示 | 发布时间不足 | 发布后等待 5 分钟 |
| 事件未收到 | 未订阅事件 | 在事件订阅页面添加 im.menu |
| 事件未收到 | 请求 URL 错误 | 检查服务器 URL 是否可访问 |
| 群聊无法使用 | 飞书限制 | 飞书菜单仅支持私聊 |
            "agent": "system",
            "params": {}
        },
        "menu_settings_frequency": {
            "intent": "change_settings",
            "agent": "system",
            "params": {"key": "frequency"}
        },
        "menu_settings_language": {
            "intent": "change_settings",
            "agent": "system",
            "params": {"key": "language"}
        },
        "menu_settings_clear": {
            "intent": "clear_history",
            "agent": "system",
            "params": {}
        },
    }

    async def handle_menu_click(
        self,
        menu_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """处理菜单点击事件"""
        if menu_id not in self.MENU_MAPPING:
            logger.warning(f"Unknown menu: {menu_id}")
            return None

        config = self.MENU_MAPPING[menu_id]

        # 创建意图结果
        return IntentResult(
            intent=config["intent"],
            agent=config["agent"],
            params=config["params"],
            confidence=1.0,  # 菜单点击 100% 确定
            source="menu"
        )
```

### 4.3 菜单创建 API

```python
async def create_bot_menu(
    self,
    menus: List[Dict]
) -> bool:
    """创建飞书机器人菜单"""

    url = f"{self.api_base}/bot/v3/menu"

    payload = {
        "menu": menus  # 菜单结构
    }

    response = await self._post(url, payload)
    return response.get("code") == 0

# 菜单结构示例
MENUS = [
    {
        "name": "📰 情报",
        "menus": [
            {"name": "热点新闻", "id": "menu_intelligence_hot"},
            {"name": "科技动态", "id": "menu_intelligence_tech"},
            {"name": "AI 进展", "id": "menu_intelligence_ai"},
            {"name": "投资并购", "id": "menu_intelligence_investment"},
            {"name": "行业报告", "id": "menu_intelligence_report"},
        ]
    },
    {
        "name": "🔍 搜索",
        "menus": [
            {"name": "搜索新闻", "id": "menu_search_news"},
            {"name": "搜索资讯", "id": "menu_search_info"},
            {"name": "搜索趋势", "id": "menu_search_trend"},
            {"name": "高级搜索", "id": "menu_search_advanced"},
        ]
    },
    {
        "name": "⚙️ 设置",
        "menus": [
            {"name": "获取当前配置", "id": "menu_settings_get"},
            {"name": "切换推送频率", "id": "menu_settings_frequency"},
            {"name": "语言设置", "id": "menu_settings_language"},
            {"name": "清除会话历史", "id": "menu_settings_clear"},
        ]
    }
]
```

### 4.4 优化后的路由管道

```python
class MultiLevelRouter:
    """优化后的多层路由引擎"""

    async def route(
        self,
        message: str,
        user_id: str,
        context: Context,
        menu_source: str = None  # 新增: 菜单来源
    ) -> RoutingResult:
        # Level 0: 菜单点击 (最高优先级，100% 准确)
        if menu_source:
            return await self._handle_menu_source(menu_source, user_id)

        # Level 1: 规则匹配 (<10ms)
        result = await self._rule_match(message)
        if result.confidence > 0.9:
            return result

        # Level 2: 向量语义匹配 (<50ms)
        result = await self._vector_match(message)
        if result.confidence > 0.85:
            return result

        # Level 3: LLM 深度理解 (<300ms)
        result = await self._llm_match(message, context)
        if result.confidence > 0.7:
            return result

        # Fallback: 降级处理
        return self._fallback(message)
```

---

## 5. 数据模型设计

### 5.1 PostgreSQL 表结构

```sql
-- 意图定义表
CREATE TABLE intents (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    agent VARCHAR(20) NOT NULL,
    keywords TEXT[],  -- 数组
    patterns TEXT[],
    examples TEXT[],
    priority INT DEFAULT 50,
    confidence_threshold FLOAT DEFAULT 0.7,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 意图向量嵌入 (pgvector)
CREATE TABLE intent_embeddings (
    id SERIAL PRIMARY KEY,
    intent_id VARCHAR(50) REFERENCES intents(id),
    embedding vector(1536),  -- OpenAI embedding dimension
    created_at TIMESTAMP DEFAULT NOW()
);

-- 对话历史表
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(10) NOT NULL,  -- user/assistant
    content TEXT NOT NULL,
    intent_id VARCHAR(50),
    confidence FLOAT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 用户反馈表
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    message_id UUID REFERENCES messages(id),
    user_id VARCHAR(50) NOT NULL,
    is_positive BOOLEAN NOT NULL,
    corrected_intent VARCHAR(50),
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.2 Redis 结构

```python
# Key: session:{user_id}:{conversation_id}
# TTL: 30 minutes

{
    "current_intent": "view_hot_news",
    "slots": {
        "category": "tech",
        "date": "2026-03-08"
    },
    "history": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "context_variables": {
        "last_intent": "search_intelligence",
        "last_result_count": 10
    }
}
```

---

## 6. 意图分类体系 (50+ 意图)

### 6.1 情报类意图 (40 个)

| 意图ID | 名称 | Agent | 关键词 |
|--------|------|-------|--------|
| view_hot_news | 查看热点新闻 | Intelligence | 热点,热门,最新 |
| filter_by_category | 按分类筛选 | Intelligence | 分类,科技,AI |
| search_intelligence | 搜索情报 | Intelligence | 搜索,找,查 |
| get_summary | 获取摘要 | Intelligence | 摘要,总结,概括 |
| translate_content | 翻译内容 | Intelligence | 翻译,英文 |
| analyze_trend | 分析趋势 | Intelligence | 趋势,分析 |
| compare_news | 对比新闻 | Intelligence | 对比,比较 |
| get_details | 获取详情 | Intelligence | 详情,详细 |
| bookmark_news | 收藏新闻 | Intelligence | 收藏,保存 |
| share_news | 分享新闻 | Intelligence | 分享,转发 |
| ... | ... | ... | ... |

### 5.2 对话类意图 (15 个)

| 意图ID | 名称 | Agent | 关键词 |
|--------|------|-------|--------|
| general_chat | 闲聊 | LLM | 你好,在吗 |
| ask_question | 提问 | LLM | 什么是,怎么 |
| get_help | 获取帮助 | LLM | 帮助,help |
| explain_concept | 解释概念 | LLM | 解释,说明 |
| calculate | 计算 | API | 计算,等于 |
| ... | ... | ... | ... |

### 5.3 系统类意图 (5 个)

| 意图ID | 名称 | Agent | 关键词 |
|--------|------|-------|--------|
| get_settings | 获取设置 | System | 设置,配置 |
| change_settings | 修改设置 | System | 更改,修改 |
| clear_history | 清除历史 | System | 清除,删除 |
| get_help_system | 系统帮助 | System | 帮助,help |
| feedback | 反馈 | System | 反馈,意见 |

---

## 7. 核心算法设计

### 6.1 多层路由算法

```python
async def route(self, message: str, context: Context) -> RoutingResult:
    # 预处理
    normalized = self._normalize(message)

    # Level 1: 规则匹配 (10ms)
    rule_result = self._match_rules(normalized)
    if rule_result.confidence > 0.9:
        return rule_result

    # Level 2: 向量匹配 (50ms)
    vector_result = await self._match_vectors(normalized)
    if vector_result.confidence > 0.85:
        return vector_result

    # Level 3: LLM 匹配 (300ms)
    llm_result = await self._match_llm(normalized, context)
    if llm_result.confidence > 0.7:
        return llm_result

    # Fallback
    return self._fallback(normalized)
```

### 6.2 向量匹配算法

```python
async def _match_vectors(self, message: str) -> RoutingResult:
    # 1. 生成 embedding
    embedding = await self.embedding_service.get_embedding(message)

    # 2. 向量相似度搜索 (Top-K)
    results = await self.vector_store.search(
        embedding=embedding,
        top_k=3,
        threshold=0.75
    )

    # 3. 融合排序
    final_result = self._rank_results(results)

    return final_result
```

### 6.3 LLM 意图识别 (Few-shot)

```python
SYSTEM_PROMPT = """你是一个意图识别专家。根据用户消息，识别其意图。

可用意图：
- view_hot_news: 查看热点新闻
- search_intelligence: 搜索情报
- general_chat: 闲聊
- translate_content: 翻译内容

示例：
用户: "最近有什么AI新闻" → intent: search_intelligence
用户: "你好" → intent: general_chat

请返回JSON格式：
{"intent": "意图ID", "confidence": 0.0-1.0, "slots": {}}"""

async def _match_llm(self, message: str, context: Context) -> RoutingResult:
    response = await self.llm.chat(
        prompt=message,
        system=SYSTEM_PROMPT,
        few_shot_examples=context.examples
    )
    return self._parse_response(response)
```

### 6.4 自适应学习算法

```python
async def learn_from_feedback(
    self,
    user_id: str,
    message: str,
    intent_id: str,
    is_positive: bool
):
    if is_positive:
        # 成功案例 → 提取关键词 → 更新规则库
        keywords = self._extract_keywords(message)
        self.self_learning_router.learn_from_success(
            message=message,
            agent=intent_id,
            keywords=keywords
        )

        # 更新向量库
        await self._update_embedding(message, intent_id)
    else:
        # 失败案例 → 记录 → 周期性分析
        self.self_learning_router.learn_from_failure(
            message=message,
            intent=intent_id
        )
```

---

## 8. 消息回路设计

### 8.1 用户反馈机制

```
┌──────────┐    文字消息     ┌──────────┐    处理      ┌──────────┐
│  用户    │ ──────────────→ │  系统    │ ──────────→ │ Intent  │
│          │                 │          │             │ Router  │
└──────────┘                 └──────────┘             └────┬─────┘
     │                                                    │
     │    响应消息 (Card/Text)                             │
     ←────────────────────────────────────────────────────┘
```

### 7.2 反馈类型

1. **显式反馈**: 用户点击按钮 (callback)
2. **隐式反馈**: 用户发送文字消息
3. **直接纠正**: 用户说"不是这个"

### 7.3 反馈处理流程

```python
async def handle_feedback(
    self,
    message: str,
    user_id: str,
    context: ConversationContext
) -> Response:
    # 1. 检测是否是反馈消息
    if self._is_feedback(message):
        # 处理反馈
        await self._process_feedback(message, context)
        return Response(text="收到反馈，感谢您的建议！")

    # 2. 正常意图识别
    result = await self.route(message, user_id, context)

    # 3. 执行意图
    response = await self._execute_intent(result, context)

    # 4. 等待用户反馈
    return response
```

---

## 9. 实现计划

### Phase 0: 飞书菜单集成 (1-2 天) ⚡
- [ ] 在飞书开放平台配置自定义菜单
- [ ] 实现 FeishuMenuHandler 处理器
- [ ] 集成菜单事件到路由管道 (Level 0)
- [ ] 测试菜单点击事件响应

**菜单配置**:
```
📰 情报: 热点新闻 | 科技动态 | AI进展 | 投资并购 | 行业报告
🔍 搜索: 搜索新闻 | 搜索资讯 | 搜索趋势 | 高级搜索
⚙️ 设置: 获取配置 | 推送频率 | 语言设置 | 清除历史
```

### Phase 1: 基础设施 (1-2 天)
- [ ] PostgreSQL 表结构创建
- [ ] Redis 会话管理
- [ ] IntentDefinition 数据模型

### Phase 2: 核心路由 (2-3 天)
- [ ] MultiLevelRouter 实现
- [ ] 规则匹配引擎
- [ ] 向量匹配 (pgvector)
- [ ] LLM 匹配

### Phase 3: 意图扩展 (2-3 天)
- [ ] 50+ 意图定义
- [ ] IntentRegistry 实现
- [ ] Few-shot examples

### Phase 4: 学习系统 (2 天)
- [ ] 自适应学习
- [ ] 反馈收集
- [ ] 规则自动更新

### Phase 5: 测试优化 (1-2 天)
- [ ] E2E 测试
- [ ] 性能优化
- [ ] 监控指标

---

## 10. 关键技术选型

| 组件 | 技术选型 | 理由 |
|------|----------|------|
| 向量存储 | pgvector | 已有 PostgreSQL，一致性好 |
| 短期存储 | Redis | 快速会话管理 |
| 长期存储 | PostgreSQL | 可靠持久化 |
| Embedding | OpenAI text-embedding-3-small | 成本低，效果好 |
| LLM | DeepSeek | 已有 API，成本低 |

---

## 11. 监控指标

| 指标 | 目标 | 告警阈值 |
|------|------|----------|
| 意图识别准确率 | > 90% | < 80% |
| 平均响应延迟 | < 500ms | > 1s |
| 路由命中率 | > 95% | < 90% |
| 学习模式激活数 | 持续增长 | 停滞 |

---

## 附录: 参考资料

1. Rasa NLU Pipeline: https://rasa.com/docs/rasa/
2. Intent Classification Best Practices: https://shadecoder.com/topics/intention-recognition-a-comprehensive-guide-for-2025
3. Few-shot Learning for Intent Detection: https://irisagent.com/blog/building-chatbots-with-intent-detection-guide/

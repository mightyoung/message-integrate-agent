# Intent Recognition System Implementation Plan

## Overview

This implementation plan is based on the design document: `docs/plans/2026-03-08-intent-recognition-design.md`

**Implementation Duration**: 8-12 days
**Target**: Production-ready intent recognition system with Feishu menu integration

---

## Phase 0: Feishu Menu Integration (Day 1-2) ⚡

### Goals
- Configure Feishu custom menu in developer console
- Implement menu event handler
- Integrate with existing FeishuAdapter

### Tasks

#### Task 0.1: Configure Feishu Custom Menu (Day 1)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 1 hour

**Steps**:
1. [ ] Log in to [Feishu Developer Console](https://open.feishu.cn/app)
2. [ ] Select application `cli_a92bb8c6c239dcc2` (from .env)
3. [ ] Navigate to Bot capability settings
4. [ ] Enable "Bot Custom Menu"
5. [ ] Configure 3 main menus with 13 submenus:
   ```
   📰 情报: 热点新闻, 科技动态, AI进展, 投资并购, 行业报告
   🔍 搜索: 搜索新闻, 搜索资讯, 搜索趋势, 高级搜索
   ⚙️ 设置: 获取当前配置, 切换推送频率, 语言设置, 清除会话历史
   ```
6. [ ] Set action type to "Push event" for each menu item
7. [ ] Create and publish application version
8. [ ] Wait 5 minutes for menu to appear

**Deliverable**: Menu configured in Feishu console

---

#### Task 0.2: Subscribe to Menu Event (Day 1)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 30 minutes

**Steps**:
1. [ ] Navigate to Event Subscription page
2. [ ] Add event: `im.menu` (Bot Custom Menu Event)
3. [ ] Set request URL to: `https://your-server.com/webhook/feishu`
4. [ ] Verify URL is accessible

**Deliverable**: Event subscription configured

---

#### Task 0.3: Implement Menu Event Handler (Day 2)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 2 hours

**File**: `src/router/menu_handler.py` (NEW)

**Implementation**:
```python
# src/router/menu_handler.py
from dataclasses import dataclass
from typing import Dict, Optional, Any
from loguru import logger


@dataclass
class IntentResult:
    """Intent recognition result"""
    intent: str
    agent: str
    params: Dict[str, Any]
    confidence: float
    source: str  # "menu", "rule", "vector", "llm"
    user_id: str = ""


class FeishuMenuHandler:
    """Feishu menu event handler"""

    MENU_MAPPING = {
        # 情报
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
        # 搜索
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
        # 设置
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
        """Handle menu click event"""
        menu_event = event.get("event", {}).get("menu_event", {})
        menu_id = menu_event.get("menu_event_id", "")
        user_id = menu_event.get("user_id", "")

        if not menu_id:
            logger.warning("Menu event missing menu_event_id")
            return None

        if menu_id not in self.MENU_MAPPING:
            logger.warning(f"Unknown menu: {menu_id}")
            return None

        config = self.MENU_MAPPING[menu_id]
        logger.info(f"Menu clicked: {menu_id} by user {user_id}")

        return IntentResult(
            intent=config["intent"],
            agent=config["agent"],
            params=config["params"],
            confidence=1.0,  # 100% from menu
            source="menu",
            user_id=user_id
        )


# Global instance
_menu_handler: Optional[FeishuMenuHandler] = None


def get_menu_handler() -> FeishuMenuHandler:
    """Get global menu handler instance"""
    global _menu_handler
    if _menu_handler is None:
        _menu_handler = FeishuMenuHandler()
    return _menu_handler
```

**Deliverable**: `src/router/menu_handler.py` created

---

#### Task 0.4: Integrate Menu Handler into FeishuAdapter (Day 2)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 1 hour

**File**: `src/adapters/feishu_adapter.py`

**Changes**:
1. [ ] Import menu handler
2. [ ] Add menu event type handling in `handle_webhook`
3. [ ] Route menu events to menu handler
4. [ ] Execute intent and send response

**Code Changes**:
```python
# In feishu_adapter.py, add:
from src.router.menu_handler import get_menu_handler

async def handle_webhook(self, payload: Dict[str, Any]) -> Optional[AdapterMessage]:
    event_type = payload.get("type")

    # Handle menu event
    if event_type == "im.menu":
        return await self._handle_menu_event(payload)

    # ... existing code

async def _handle_menu_event(self, payload: Dict[str, Any]) -> Optional[AdapterMessage]:
    """Handle menu click event"""
    menu_handler = get_menu_handler()
    intent_result = await menu_handler.handle_menu_event(payload)

    if intent_result:
        # Execute intent
        response = await self._execute_intent(intent_result)

        # Send response to user (private message)
        await self.send_message(
            chat_id=intent_result.user_id,
            content=response
        )

    return None
```

**Deliverable**: Menu events integrated into FeishuAdapter

---

#### Task 0.5: Test Menu Integration (Day 2)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 1 hour

**Test Steps**:
1. [ ] Start the server
2. [ ] Open Feishu, find the bot in private chat
3. [ ] Verify menu appears
4. [ ] Click each menu item
5. [ ] Verify correct response is received

**Deliverable**: Menu integration tested and working

---

## Phase 1: Infrastructure (Day 2-4)

### Goals
- Create PostgreSQL tables for intent storage
- Set up Redis for session management
- Implement data models

### Tasks

#### Task 1.1: Create PostgreSQL Schema (Day 2)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 1 hour

**File**: `scripts/create_intent_schema.sql` (NEW)

**SQL**:
```sql
-- Intent definitions table
CREATE TABLE IF NOT EXISTS intents (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    agent VARCHAR(20) NOT NULL,
    keywords TEXT[],
    patterns TEXT[],
    examples TEXT[],
    priority INT DEFAULT 50,
    confidence_threshold FLOAT DEFAULT 0.7,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Intent embeddings for vector search (if using pgvector)
-- Note: Requires pgvector extension
-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS intent_embeddings (
    id SERIAL PRIMARY KEY,
    intent_id VARCHAR(50) REFERENCES intents(id),
    embedding vector(1536),  -- OpenAI embedding dimension
    created_at TIMESTAMP DEFAULT NOW()
);

-- Conversation history
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations(user_id);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(10) NOT NULL,  -- user/assistant
    content TEXT NOT NULL,
    intent_id VARCHAR(50),
    confidence FLOAT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);

-- User feedback
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    message_id UUID REFERENCES messages(id),
    user_id VARCHAR(50) NOT NULL,
    is_positive BOOLEAN NOT NULL,
    corrected_intent VARCHAR(50),
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_feedback_user ON feedback(user_id);
```

**Deliverable**: SQL schema created

---

#### Task 1.2: Implement Data Models (Day 3)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 2 hours

**File**: `src/router/models.py` (NEW)

**Implementation**:
```python
# src/router/models.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class AgentType(Enum):
    """Agent types"""
    INTELLIGENCE = "intelligence"
    SEARCH = "search"
    LLM = "llm"
    API = "api"
    SYSTEM = "system"


class IntentSource(Enum):
    """Intent recognition source"""
    MENU = "menu"
    RULE = "rule"
    VECTOR = "vector"
    LLM = "llm"
    FALLBACK = "fallback"


@dataclass
class Slot:
    """Intent slot"""
    name: str
    type: str
    required: bool = False
    default: Any = None


@dataclass
class IntentDefinition:
    """Intent definition"""
    id: str
    name: str
    description: str
    agent: AgentType
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    priority: int = 50
    confidence_threshold: float = 0.7
    required_slots: List[Slot] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class IntentResult:
    """Intent recognition result"""
    intent: str
    agent: str
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    source: IntentSource = IntentSource.FALLBACK
    user_id: str = ""
    message: str = ""


@dataclass
class ConversationContext:
    """Conversation context"""
    user_id: str
    conversation_id: str
    platform: str
    current_intent: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, str]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
```

**Deliverable**: Data models created

---

#### Task 1.3: Set Up Redis Session Manager (Day 3-4)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 2 hours

**File**: `src/router/session_manager.py` (NEW)

**Implementation**:
```python
# src/router/session_manager.py
import json
from typing import Optional, Dict, Any, List
from datetime import timedelta
import redis.asyncio as redis
from loguru import logger


class SessionManager:
    """Redis-based session manager"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self.default_ttl = timedelta(minutes=30)

    async def connect(self):
        """Connect to Redis"""
        self._client = await redis.from_url(self.redis_url)
        logger.info("Session manager connected to Redis")

    async def close(self):
        """Close connection"""
        if self._client:
            await self._client.close()

    def _session_key(self, user_id: str, conversation_id: str) -> str:
        """Generate session key"""
        return f"session:{user_id}:{conversation_id}"

    async def get_context(
        self,
        user_id: str,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get conversation context from Redis"""
        if not self._client:
            return None

        key = self._session_key(user_id, conversation_id)
        data = await self._client.get(key)

        if data:
            return json.loads(data)
        return None

    async def set_context(
        self,
        user_id: str,
        conversation_id: str,
        context: Dict[str, Any],
        ttl: Optional[timedelta] = None
    ):
        """Save conversation context to Redis"""
        if not self._client:
            return

        key = self._session_key(user_id, conversation_id)
        ttl = ttl or self.default_ttl

        await self._client.setex(
            key,
            ttl,
            json.dumps(context, ensure_ascii=False)
        )

    async def update_context(
        self,
        user_id: str,
        conversation_id: str,
        updates: Dict[str, Any]
    ):
        """Update specific fields in context"""
        context = await self.get_context(user_id, conversation_id)
        if context is None:
            context = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "current_intent": None,
                "slots": {},
                "history": [],
                "variables": {}
            }

        context.update(updates)
        await self.set_context(user_id, conversation_id, context)

    async def add_to_history(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str
    ):
        """Add message to conversation history"""
        context = await self.get_context(user_id, conversation_id)
        if context is None:
            context = {"history": []}

        context["history"].append({"role": role, "content": content})

        # Keep last 20 messages
        if len(context["history"]) > 20:
            context["history"] = context["history"][-20:]

        await self.set_context(user_id, conversation_id, context)

    async def clear_session(
        self,
        user_id: str,
        conversation_id: str
    ):
        """Clear session"""
        if not self._client:
            return

        key = self._session_key(user_id, conversation_id)
        await self._client.delete(key)


# Global instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
```

**Deliverable**: Session manager implemented

---

## Phase 2: Core Router Implementation (Day 4-7)

### Goals
- Implement multi-level routing (Menu → Rule → Vector → LLM)
- Create intent registry
- Integrate with existing agents

### Tasks

#### Task 2.1: Create Intent Registry (Day 4)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 2 hours

**File**: `src/router/registry.py` (ENHANCE)

**Changes**: Add 50+ intent definitions

```python
# Enhanced src/router/registry.py
from typing import Dict, List, Optional
from src.router.models import IntentDefinition, AgentType


class IntentRegistry:
    """Registry of all available intents"""

    def __init__(self):
        self.intents: Dict[str, IntentDefinition] = {}
        self._load_default_intents()

    def _load_default_intents(self):
        """Load default 50+ intents"""

        # === 情报类意图 (40个) ===

        self.register(IntentDefinition(
            id="view_hot_news",
            name="查看热点新闻",
            description="获取当前热点新闻",
            agent=AgentType.INTELLIGENCE,
            keywords=["热点", "热门", "最新", "头条"],
            priority=90
        ))

        self.register(IntentDefinition(
            id="view_category_news",
            name="按分类查看新闻",
            description="按指定分类查看新闻",
            agent=AgentType.INTELLIGENCE,
            keywords=["科技", "AI", "投资", "行业"],
            priority=80
        ))

        self.register(IntentDefinition(
            id="search_intelligence",
            name="搜索情报",
            description="搜索特定主题的情报",
            agent=AgentType.SEARCH,
            keywords=["搜索", "找", "查", "关于"],
            priority=85
        ))

        self.register(IntentDefinition(
            id="get_summary",
            name="获取摘要",
            description="获取新闻摘要",
            agent=AgentType.INTELLIGENCE,
            keywords=["摘要", "总结", "概括", "简报"],
            priority=70
        ))

        self.register(IntentDefinition(
            id="translate_content",
            name="翻译内容",
            description="翻译内容为中文",
            agent=AgentType.INTELLIGENCE,
            keywords=["翻译", "英文", "英文版"],
            priority=75
        ))

        # ... Continue with remaining 35+ intents

        # === 对话类意图 (15个) ===

        self.register(IntentDefinition(
            id="general_chat",
            name="闲聊",
            description="一般对话",
            agent=AgentType.LLM,
            keywords=["你好", "在吗", "嗨", "hey"],
            priority=50
        ))

        self.register(IntentDefinition(
            id="ask_question",
            name="提问",
            description="提出问题",
            agent=AgentType.LLM,
            keywords=["什么是", "怎么", "如何", "为什么"],
            priority=60
        ))

        # ... Continue with remaining conversation intents

        # === 系统类意图 (5个) ===

        self.register(IntentDefinition(
            id="get_settings",
            name="获取设置",
            description="获取当前配置",
            agent=AgentType.SYSTEM,
            keywords=["设置", "配置", "状态"],
            priority=95
        ))

        self.register(IntentDefinition(
            id="change_settings",
            name="修改设置",
            description="修改配置",
            agent=AgentType.SYSTEM,
            keywords=["更改", "修改", "调整"],
            priority=90
        ))

        self.register(IntentDefinition(
            id="clear_history",
            name="清除历史",
            description="清除对话历史",
            agent=AgentType.SYSTEM,
            keywords=["清除", "删除", "清空"],
            priority=85
        ))

    def register(self, intent: IntentDefinition):
        """Register an intent"""
        self.intents[intent.id] = intent

    def get(self, intent_id: str) -> Optional[IntentDefinition]:
        """Get intent by ID"""
        return self.intents.get(intent_id)

    def get_by_keyword(self, keyword: str) -> List[IntentDefinition]:
        """Find intents by keyword"""
        keyword = keyword.lower()
        results = []
        for intent in self.intents.values():
            if any(keyword in kw.lower() for kw in intent.keywords):
                results.append(intent)
        return sorted(results, key=lambda x: x.priority, reverse=True)

    def get_all(self) -> List[IntentDefinition]:
        """Get all intents"""
        return list(self.intents.values())
```

**Deliverable**: Intent registry with 50+ intents

---

#### Task 2.2: Implement Multi-Level Router (Day 5-6)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 4 hours

**File**: `src/router/engine.py` (NEW)

**Implementation**:
```python
# src/router/engine.py
from typing import Optional, Dict, Any
from loguru import logger

from src.router.models import IntentResult, IntentSource, ConversationContext
from src.router.menu_handler import get_menu_handler
from src.router.keyword_router import KeywordRouter
from src.router.registry import IntentRegistry
from src.router.session_manager import get_session_manager
from src.mcp.tools.llm import chat_with_llm


class IntentRouter:
    """Multi-level intent recognition router"""

    def __init__(self):
        self.menu_handler = get_menu_handler()
        self.keyword_router = KeywordRouter()
        self.registry = IntentRegistry()
        self.session_manager = get_session_manager()
        self._setup_keyword_rules()

    def _setup_keyword_rules(self):
        """Setup keyword routing rules"""
        for intent in self.registry.get_all():
            if intent.keywords:
                self.keyword_router.add_rule(
                    keywords=intent.keywords,
                    agent=intent.agent.value,
                    action=intent.id
                )
        self.keyword_router.set_default("llm")

    async def route(
        self,
        message: str,
        user_id: str,
        conversation_id: str,
        menu_source: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentResult:
        """Main routing method with multi-level fallback"""

        # Level 0: Menu click (highest priority, 100% accuracy)
        if menu_source:
            logger.info(f"Routing via menu: {menu_source}")
            result = await self._handle_menu(menu_source, user_id)
            if result:
                return result

        # Level 1: Keyword matching (<10ms)
        logger.info(f"Routing via keyword: {message[:50]}")
        result = await self._handle_keyword(message)
        if result and result.confidence > 0.9:
            return result

        # Level 2: Vector semantic (if implemented) (<50ms)
        # result = await self._handle_vector(message)
        # if result and result.confidence > 0.85:
        #     return result

        # Level 3: LLM matching (<300ms)
        logger.info(f"Routing via LLM: {message[:50]}")
        result = await self._handle_llm(message, context or {})
        if result and result.confidence > 0.7:
            return result

        # Fallback
        return self._fallback(message)

    async def _handle_menu(
        self,
        menu_id: str,
        user_id: str
    ) -> Optional[IntentResult]:
        """Handle menu click"""
        # Build fake event structure
        event = {
            "event": {
                "menu_event": {
                    "menu_event_id": menu_id,
                    "user_id": user_id
                }
            }
        }
        return await self.menu_handler.handle_menu_event(event)

    async def _handle_keyword(self, message: str) -> Optional[IntentResult]:
        """Handle keyword-based routing"""
        result = self.keyword_router.route(message)
        if result:
            return IntentResult(
                intent=result.get("action", result.get("agent")),
                agent=result.get("agent", "llm"),
                params={},
                confidence=0.95,
                source=IntentSource.RULE
            )
        return None

    async def _handle_llm(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Optional[IntentResult]:
        """Handle LLM-based routing"""
        try:
            system_prompt = """你是一个意图识别专家。根据用户消息，识别其意图。

可用意图：
- view_hot_news: 查看热点新闻
- view_category_news: 按分类查看新闻
- search_intelligence: 搜索情报
- get_summary: 获取摘要
- translate_content: 翻译内容
- general_chat: 闲聊
- ask_question: 提问
- get_settings: 获取设置
- change_settings: 修改设置
- clear_history: 清除历史

请返回JSON格式：
{"intent": "意图ID", "confidence": 0.0-1.0}"""

            response = await chat_with_llm(
                prompt=message,
                model="deepseek-chat",
                system_message=system_prompt,
                temperature=0.3,
                max_tokens=200
            )

            # Parse JSON response
            import json
            import re

            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return IntentResult(
                    intent=data.get("intent", "general_chat"),
                    agent=self._get_agent_for_intent(data.get("intent", "general_chat")),
                    params={},
                    confidence=float(data.get("confidence", 0.5)),
                    source=IntentSource.LLM
                )

        except Exception as e:
            logger.error(f"LLM routing error: {e}")

        return None

    def _get_agent_for_intent(self, intent_id: str) -> str:
        """Get agent type for intent"""
        intent = self.registry.get(intent_id)
        if intent:
            return intent.agent.value
        return "llm"

    def _fallback(self, message: str) -> IntentResult:
        """Fallback to general chat"""
        return IntentResult(
            intent="general_chat",
            agent="llm",
            params={},
            confidence=0.3,
            source=IntentSource.FALLBACK,
            message=message
        )


# Global instance
_intent_router: Optional[IntentRouter] = None


def get_intent_router() -> IntentRouter:
    """Get global intent router"""
    global _intent_router
    if _intent_router is None:
        _intent_router = IntentRouter()
    return _intent_router
```

**Deliverable**: Multi-level router implemented

---

#### Task 2.3: Integrate Router with Dispatcher (Day 7)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 2 hours

**File**: `src/gateway/dispatcher.py` (ENHANCE)

**Changes**:
1. [ ] Add intent router to dispatcher
2. [ ] Handle menu events
3. [ ] Route messages through intent router

```python
# Enhanced dispatcher.py
from src.router.engine import get_intent_router


class IntentDispatcher(Dispatcher):
    """Enhanced dispatcher with intent recognition"""

    def __init__(self):
        super().__init__()
        self.intent_router = get_intent_router()

    async def dispatch(self, message: UnifiedMessage) -> Optional[Dict[str, Any]]:
        """Dispatch with intent recognition"""

        # Check for menu event
        if hasattr(message, 'menu_source') and message.menu_source:
            return await self._handle_menu(message)

        # Use intent router
        result = await self.intent_router.route(
            message=message.content,
            user_id=message.user_id,
            conversation_id=message.conversation_id,
            context={"platform": message.platform.value}
        )

        # Execute intent
        return await self._execute_intent(result, message)
```

**Deliverable**: Router integrated with dispatcher

---

## Phase 3: Agent Execution (Day 7-9)

### Goals
- Implement agent coordinator
- Connect to existing agents (LLMAgent, SearchAgent, Intelligence)
- Handle intent execution

### Tasks

#### Task 3.1: Implement Agent Coordinator (Day 7-8)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 3 hours

**File**: `src/router/coordinator.py` (NEW)

```python
# src/router/coordinator.py
from typing import Dict, Any, Optional
from loguru import logger

from src.router.models import IntentResult, AgentType
from src.agents.llm_agent import LLMAgent
from src.agents.search_agent import SearchAgent
from src.intelligence.pusher import IntelligencePusher


class AgentCoordinator:
    """Coordinates agent execution based on intent"""

    def __init__(self):
        self.llm_agent = LLMAgent()
        self.search_agent = SearchAgent()
        self.intelligence_pusher = IntelligencePusher()

    async def execute(
        self,
        intent_result: IntentResult,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Execute intent using appropriate agent"""

        agent = intent_result.agent
        params = intent_result.params

        logger.info(f"Executing intent: {intent_result.intent} with agent: {agent}")

        if agent == AgentType.INTELLIGENCE.value or agent == "intelligence":
            return await self._execute_intelligence(intent_result, context)
        elif agent == AgentType.SEARCH.value or agent == "search":
            return await self._execute_search(intent_result, message)
        elif agent == AgentType.LLM.value or agent == "llm":
            return await self._execute_llm(intent_result, message, context)
        elif agent == AgentType.SYSTEM.value or agent == "system":
            return await self._execute_system(intent_result, context)
        elif agent == AgentType.API.value or agent == "api":
            return await self._execute_api(intent_result, message)
        else:
            return await self._execute_llm(intent_result, message, context)

    async def _execute_intelligence(
        self,
        intent: IntentResult,
        context: Dict[str, Any]
    ) -> str:
        """Execute intelligence-related intent"""
        intent_id = intent.intent

        if intent_id == "view_hot_news":
            return await self.intelligence_pusher.get_hot_news()
        elif intent_id == "view_category_news":
            category = intent.params.get("category", "tech")
            return await self.intelligence_pusher.get_news_by_category(category)
        elif intent_id == "get_summary":
            return await self.intelligence_pusher.get_summary()
        elif intent_id == "translate_content":
            return await self.intelligence_pusher.translate_recent()
        else:
            return await self.intelligence_pusher.get_hot_news()

    async def _execute_search(
        self,
        intent: IntentResult,
        message: str
    ) -> str:
        """Execute search-related intent"""
        query = message.replace("搜索", "").replace("找", "").strip()
        if not query:
            query = intent.params.get("query", "")

        search_type = intent.params.get("type", "news")

        if search_type == "news":
            return await self.search_agent.search_news(query)
        elif search_type == "trend":
            return await self.search_agent.search_trends(query)
        else:
            return await self.search_agent.search(query)

    async def _execute_llm(
        self,
        intent: IntentResult,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Execute LLM conversation"""
        return await self.llm_agent.handle(
            message=message,
            user_id=context.get("user_id", ""),
            context={"platform": context.get("platform", "feishu")}
        )

    async def _execute_system(
        self,
        intent: IntentResult,
        context: Dict[str, Any]
    ) -> str:
        """Execute system-related intent"""
        intent_id = intent.intent

        if intent_id == "get_settings":
            return "当前设置:\n- 推送频率: 每日\n- 语言: 中文"
        elif intent_id == "change_settings":
            key = intent.params.get("key")
            return f"设置项 {key} 已更新"
        elif intent_id == "clear_history":
            return "对话历史已清除"

        return "未知系统操作"

    async def _execute_api(
        self,
        intent: IntentResult,
        message: str
    ) -> str:
        """Execute API-related intent"""
        return "API 调用功能开发中"


# Global instance
_coordinator: Optional[AgentCoordinator] = None


def get_agent_coordinator() -> AgentCoordinator:
    """Get global agent coordinator"""
    global _coordinator
    if _coordinator is None:
        _coordinator = AgentCoordinator()
    return _coordinator
```

**Deliverable**: Agent coordinator implemented

---

## Phase 4: Learning System (Day 9-10)

### Goals
- Integrate with existing SelfLearningRouter
- Implement feedback collection
- Enable continuous learning

### Tasks

#### Task 4.1: Integrate Self-Learning (Day 9)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 2 hours

**File**: `src/router/learning.py` (NEW)

```python
# src/router/learning.py
from typing import Optional
from loguru import logger

from src.router.self_learning import get_self_learning_router


class LearningEngine:
    """Learning engine for intent recognition"""

    def __init__(self):
        self.self_learning = get_self_learning_router()

    async def learn_from_success(
        self,
        message: str,
        intent_id: str,
        user_id: str
    ):
        """Learn from successful interaction"""
        self.self_learning.learn_from_success(
            message=message,
            agent=intent_id
        )
        logger.info(f"Learned from success: {message[:30]} -> {intent_id}")

    async def learn_from_feedback(
        self,
        message: str,
        intent_id: str,
        is_positive: bool,
        user_id: str
    ):
        """Learn from user feedback"""
        if is_positive:
            await self.learn_from_success(message, intent_id, user_id)
        else:
            self.self_learning.learn_from_failure(
                message=message,
                attempted_agent=intent_id,
                error="user_feedback_negative"
            )
            logger.info(f"Learned from failure: {message[:30]}")

    async def get_suggestion(self, message: str):
        """Get routing suggestion based on learned patterns"""
        return self.self_learning.get_routing_suggestion(message)
```

**Deliverable**: Learning system integrated

---

## Phase 5: Testing & Optimization (Day 10-12)

### Tasks

#### Task 5.1: Unit Tests (Day 10)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 2 hours

**Files to test**:
- `src/router/menu_handler.py`
- `src/router/engine.py`
- `src/router/coordinator.py`
- `src/router/session_manager.py`

**Deliverable**: Unit tests created

---

#### Task 5.2: Integration Tests (Day 11)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 2 hours

**Test scenarios**:
1. Menu click → correct intent → correct response
2. Text message → keyword match → correct intent
3. Text message → LLM routing → correct intent
4. Multi-turn conversation context preserved
5. Feedback → learning update

**Deliverable**: Integration tests passed

---

#### Task 5.3: Performance Optimization (Day 11-12)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 2 hours

**Optimizations**:
1. [ ] Cache intent definitions
2. [ ] Async LLM calls with timeout
3. [ ] Redis connection pooling
4. [ ] Response caching for repeated queries

**Deliverable**: Performance targets met

---

#### Task 5.4: Documentation (Day 12)
**Status**: Waiting
**Owner**: Developer
**Estimated Time**: 1 hour

**Deliverables**:
- [ ] Update README with intent recognition usage
- [ ] Document API endpoints
- [ ] Document configuration options

---

## Implementation Summary

### Timeline

| Phase | Days | Key Deliverables |
|-------|------|------------------|
| Phase 0: Feishu Menu | 1-2 | Menu configured, handler implemented |
| Phase 1: Infrastructure | 2-4 | DB schema, data models, session manager |
| Phase 2: Core Router | 4-7 | Multi-level router, intent registry |
| Phase 3: Agent Execution | 7-9 | Agent coordinator, intent execution |
| Phase 4: Learning | 9-10 | Self-learning integration |
| Phase 5: Testing | 10-12 | Tests, optimization, docs |

### Dependencies

```
Phase 0 ─┬─> Phase 1 ─┬─> Phase 2 ─┬─> Phase 3 ─┬─> Phase 4 ─┬─> Phase 5
         │            │            │            │            │
         └────────────┴────────────┴────────────┴────────────┘
              Optional (can run in parallel)
```

### Key Files to Create/Modify

| File | Action | Phase |
|------|--------|-------|
| `src/router/menu_handler.py` | Create | 0 |
| `src/router/models.py` | Create | 1 |
| `src/router/session_manager.py` | Create | 1 |
| `src/router/registry.py` | Enhance | 2 |
| `src/router/engine.py` | Create | 2 |
| `src/router/coordinator.py` | Create | 3 |
| `src/router/learning.py` | Create | 4 |
| `src/adapters/feishu_adapter.py` | Modify | 0 |
| `src/gateway/dispatcher.py` | Modify | 2 |

### Reused Components

| Component | Location | Reuse Reason |
|-----------|----------|---------------|
| KeywordRouter | `src/router/keyword_router.py` | Level 1 routing |
| SelfLearningRouter | `src/router/self_learning.py` | Learning system |
| LLMAgent | `src/agents/llm_agent.py` | Conversation |
| SearchAgent | `src/agents/search_agent.py` | Web search |
| FeishuAdapter | `src/adapters/feishu_adapter.py` | Platform adapter |
| Dispatcher | `src/gateway/dispatcher.py` | Message routing |

---

## Success Criteria

- [ ] Menu clicks work correctly (100% accuracy)
- [ ] Intent recognition accuracy > 85%
- [ ] Average response time < 500ms
- [ ] Self-learning improves over time
- [ ] All tests pass
- [ ] Documentation complete

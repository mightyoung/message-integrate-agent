# 飞书消息设计规范

## 1. 当前实现分析

### 1.1 现有消息格式
```
当前: 纯文本/简单卡片
├── 标题: "🔥 今日热点情报"
├── 内容: 编号列表 + 分类标签 + 匹配度
└── 限制: 无交互、无法跳转、无法反馈
```

### 1.2 现有能力 (来自 feishu_adapter.py)
```python
capabilities = ChannelCapabilities(
    chat_types=[ChatType.DIRECT, ChatType.GROUP],
    reactions=True,      # ✅ 表情反应
    reply=True,          # ✅ 引用回复
    media=True,          # ✅ 图片/文件
    text_chunk_limit=4000,
    supports_webhook=True,
    supports_polling=False,
)
```

---

## 2. 消息类型设计

### 2.1 消息分类矩阵

| 场景 | 推荐类型 | 理由 |
|------|----------|------|
| 情报推送 | Interactive Card | 支持按钮交互、多媒体展示 |
| 用户咨询 | Text + Quick Reply | 快速响应、引导操作 |
| 确认提示 | Interactive Card | 按钮确认、取消 |
| 文件分享 | File/Image | 原生支持预览 |
| 群通知 | Post (mentions) | @指定人、引用上下文 |

### 2.2 Interactive Card 模板库

```python
# 模板: 情报推送卡片
INTELLIGENCE_CARD = {
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "🔥 今日热点情报"},
            "template": "blue"
        },
        "elements": [
            # 摘要区
            {"tag": "markdown", "content": "📊 共 {count} 条更新"},
            {"tag": "divider"},
            # 情报列表 (循环)
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔗 查看详情"},
                        "type": "primary",
                        "url": "{url}"
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "👍 有用"},
                        "type": "default"
                    }
                ]
            },
            # 分页/更多
            {"tag": "divider"},
            {
                "tag": "action",
                "actions": [
                    {"tag": "button", "text": "⬅️ 上一页", "type": "default"},
                    {"tag": "button", "text": "➡️ 下一页", "type": "default"}
                ]
            }
        ],
        "footer": {
            "tag": "rich_text",
            "elements": [
                {"tag": "plain_text", "content": "🤖 由 AI 助手推送"}
            ]
        }
    }
}
```

### 2.3 消息结构设计

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
import json

class MessageType(Enum):
    TEXT = "text"
    POST = "post"
    INTERACTIVE = "interactive"
    IMAGE = "image"
    FILE = "file"

class MessagePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class MessageAction:
    """消息动作按钮"""
    id: str
    label: str
    action_type: str  # "callback", "url", "reply"
    value: str = ""
    confirm: Optional[Dict] = None  # 确认对话框

@dataclass
class MessageElement:
    """消息元素"""
    tag: str  # "markdown", "divider", "action", "image", etc.
    content: Any = None
    actions: List[MessageAction] = field(default_factory=list)

@dataclass
class UnifiedMessage:
    """统一消息结构"""
    # 基础信息
    message_id: str
    message_type: MessageType
    priority: MessagePriority = MessagePriority.NORMAL

    # 内容
    title: str = ""
    content: str = ""
    elements: List[MessageElement] = field(default_factory=list)

    # 交互
    actions: List[MessageAction] = field(default_factory=list)

    # 来源信息
    source: str = ""  # "intelligence", "agent", "user"
    platform: str = "feishu"

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    references: List[str] = field(default_factory=list)  # 引用的消息ID
    mentions: List[str] = field(default_factory=list)    # @的用户

    def to_feishu_card(self) -> Dict:
        """转换为飞书 Interactive Card"""
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": self.title[:50]},
                    "template": self._get_template_by_priority()
                },
                "elements": self._build_elements(),
            }
        }

        if self.actions:
            card["card"]["actions"] = self._build_actions()

        return card

    def _get_template_by_priority(self) -> str:
        templates = {
            MessagePriority.LOW: "grey",
            MessagePriority.NORMAL: "blue",
            MessagePriority.HIGH: "orange",
            MessagePriority.URGENT: "red",
        }
        return templates.get(self.priority, "blue")

    def _build_elements(self) -> List[Dict]:
        elements = []

        # 内容区
        if self.content:
            elements.append({
                "tag": "markdown",
                "content": self.content[:500]
            })

        # 自定义元素
        for elem in self.elements:
            element = {"tag": elem.tag}
            if elem.content:
                element["content"] = elem.content
            if elem.actions:
                element["actions"] = [self._action_to_dict(a) for a in elem.actions]
            elements.append(element)

        return elements

    def _build_actions(self) -> List[Dict]:
        return [self._action_to_dict(a) for a in self.actions]

    def _action_to_dict(self, action: MessageAction) -> Dict:
        result = {
            "tag": "button",
            "text": {"tag": "plain_text", "content": action.label},
            "type": "default",
        }

        if action.action_type == "callback":
            result["value"] = {"action_id": action.id, "value": action.value}
        elif action.action_type == "url":
            result["url"] = action.value

        return result
```

---

## 3. 回复机制设计

### 3.1 会话上下文

```python
@dataclass
class ConversationContext:
    """会话上下文"""
    user_id: str
    platform: str

    # 会话链
    parent_message_id: Optional[str] = None  # 父消息ID (用于回复链)
    root_message_id: Optional[str] = None     # 根消息ID

    # 状态
    state: Dict[str, Any] = field(default_factory=dict)

    # 意图追踪
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)

    def create_reply(self, content: str) -> 'UnifiedMessage':
        """创建回复消息"""
        return UnifiedMessage(
            message_id=generate_message_id(),
            message_type=MessageType.INTERACTIVE,
            title="",
            content=content,
            platform=self.platform,
            references=[self.parent_message_id] if self.parent_message_id else [],
            metadata={"conversation_state": self.state}
        )
```

### 3.2 引用回复

```python
async def reply_to_message(
    adapter,
    chat_id: str,
    content: str,
    reply_message_id: str
) -> bool:
    """引用回复 (飞书 API)"""

    # 飞书支持在消息中引用
    message_content = {
        "text": content,
        "quote": reply_message_id  # 引用消息ID
    }

    return await adapter.send_message(
        chat_id=chat_id,
        content=json.dumps(message_content),
        msg_type="text",
        reply=reply_message_id  # 启用回复功能
    )
```

### 3.3 对话流程

```
用户发送消息
    │
    ▼
┌─────────────────┐
│  消息解析器      │
│  - 提取意图     │
│ - 提取实体      │
│ - 识别动作     │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  意图路由       │
│  - 查天气      │ ──→ 工具调用
│  - 聊聊天      │ ──→ LLM 对话
│  - 查情报      │ ──→ 知识库查询
│  - 反馈        │ ──→ 反馈处理
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  响应生成       │
│  - 选择模板     │
│  - 填充内容     │
│  - 添加按钮     │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  消息发送       │
│  - 构建卡片     │
│  - 添加引用    │
│  - 发送       │
└─────────────────┘
```

---

## 4. 反馈机制设计

### 4.1 交互按钮反馈

```python
class FeedbackHandler:
    """反馈处理器"""

    # 按钮动作映射
    ACTION_HANDLERS = {
        "intelligence_useful": self._handle_intelligence_feedback,
        "intelligence_not_useful": self._handle_intelligence_feedback,
        "show_more": self._handle_show_more,
        "subscribe": self._handle_subscribe,
        "unsubscribe": self._handle_unsubscribe,
    }

    async def handle_callback(self, callback: Dict) -> UnifiedMessage:
        """处理卡片按钮回调"""

        action_id = callback.get("action_id")
        value = callback.get("value", {})
        user_id = callback.get("user_id")

        # 查找处理器
        handler = self.ACTION_HANDLERS.get(action_id)
        if handler:
            return await handler(user_id, value)

        return UnifiedMessage(
            message_id=generate_message_id(),
            message_type=MessageType.TEXT,
            content="收到反馈，感谢您的参与！"
        )

    async def _handle_intelligence_feedback(
        self,
        user_id: str,
        value: Dict
    ) -> UnifiedMessage:
        """处理情报反馈"""

        # 记录反馈
        await self.feedback_service.record(
            user_id=user_id,
            item_id=value.get("item_id"),
            feedback="useful" if "useful" in value else "not_useful"
        )

        # 生成感谢消息
        return UnifiedMessage(
            message_id=generate_message_id(),
            message_type=MessageType.TEXT,
            content="感谢您的反馈！这将帮助我们优化推荐算法。",
            metadata={"feedback": value}
        )
```

### 4.2 反馈消息模板

```python
# 反馈请求卡片
FEEDBACK_REQUEST_CARD = {
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "📝 内容反馈"},
            "template": "blue"
        },
        "elements": [
            {
                "tag": "markdown",
                "content": "这篇内容对您有帮助吗？"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "👍 有用"},
                        "type": "primary",
                        "value": {"action": "useful"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "👎 没用"},
                        "type": "default",
                        "value": {"action": "not_useful"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "💬 提建议"},
                        "type": "default",
                        "value": {"action": "suggest"}
                    }
                ]
            }
        ]
    }
}
```

---

## 5. 消息模板库

### 5.1 情报推送模板

```python
class MessageTemplates:
    """消息模板库"""

    @staticmethod
    def intelligence_push(
        items: List[IntelligenceItem],
        user_preferences: Dict
    ) -> Dict:
        """情报推送模板"""

        # 构建列表元素
        item_elements = []
        for i, item in enumerate(items[:5]):
            item_elements.extend([
                {
                    "tag": "divider"
                },
                {
                    "tag": "rich_text",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"{i+1}. {item.title[:40]}",
                            "lines": 1
                        },
                        {
                            "tag": "plain_text",
                            "content": f"\n🏷️ {item.category} | ⭐ {item.score:.1f}",
                            "color": "grey"
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "🔗 原文"},
                            "type": "primary",
                            "url": item.url
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "👍"},
                            "type": "default",
                            "value": {"action": "useful", "item_id": item.id}
                        }
                    ]
                }
            ])

        # 构建完整卡片
        return {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"🔥 今日热点 ({len(items)}条)"
                    },
                    "template": "blue"
                },
                "elements": [
                    # 摘要
                    {
                        "tag": "markdown",
                        "content": f"📊 根据您的兴趣推荐 | 🕐 {datetime.now().strftime('%H:%M')}"
                    },
                    {"tag": "divider"}
                ] + item_elements + [
                    # 底部操作
                    {"tag": "divider"},
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "📬 订阅每日简报"},
                                "type": "default",
                                "value": {"action": "subscribe"}
                            },
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "⚙️ 设置偏好"},
                                "type": "default",
                                "value": {"action": "settings"}
                            }
                        ]
                    }
                ]
            }
        }

    @staticmethod
    def agent_response(
        response: str,
        actions: List[MessageAction],
        context: Optional[Dict] = None
    ) -> Dict:
        """Agent 响应模板"""

        elements = [
            {
                "tag": "markdown",
                "content": response
            }
        ]

        # 添加操作按钮
        if actions:
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": a.label},
                        "type": "default" if a.action_type == "callback" else "primary",
                        "value": {"action_id": a.id, "value": a.value} if a.action_type == "callback" else None,
                        "url": a.value if a.action_type == "url" else None
                    }
                    for a in actions
                ]
            })

        # 添加上下文引用
        if context and context.get("quoted_message"):
            elements.append({
                "tag": "divider"
            })
            elements.append({
                "tag": "rich_text",
                "elements": [
                    {
                        "tag": "quote",
                        "quote_id": context["quoted_message"]
                    }
                ]
            })

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "🤖 AI 助手"},
                    "template": "green"
                },
                "elements": elements
            }
        }
```

---

## 6. 配置项

```python
# 消息配置
MESSAGE_CONFIG = {
    # 飞书配置
    "feishu": {
        "max_card_elements": 50,
        "max_button_count": 10,
        "enable_quote_reply": True,
        "enable_action_feedback": True,
    },

    # 模板配置
    "templates": {
        "intelligence": {
            "items_per_card": 5,
            "show_pagination": True,
            "show_feedback_buttons": True,
        },
        "agent": {
            "show_actions": True,
            "default_action_type": "button",
        }
    },

    # 消息队列
    "queue": {
        "max_retries": 3,
        "retry_delay": 5,
        "batch_size": 10,
    }
}
```

---

## 7. 待实现功能清单

| 优先级 | 功能 | 状态 | 说明 |
|--------|------|------|------|
| P0 | Interactive Card 模板库 | ✅ 已完成 | feishu_templates.py |
| P0 | 消息按钮回调处理 | ✅ 已完成 | CallbackRouter |
| P1 | 引用回复机制 | ✅ 已完成 | send_reply() |
| P1 | 反馈收集按钮 | ✅ 已完成 | feedback_useful/not_useful |
| P2 | 消息状态追踪 | 🔄 待完善 | 已在 pusher.py |
| P2 | 批量消息处理 | 🔄 待完善 | 已有基础实现 |
| P3 | 消息动画效果 | 📋 待调研 | 低优先级 |

---

## 8. 已实现文件

```
src/adapters/
├── feishu_adapter.py      # 更新: send_card, send_reply, handle_callback
├── feishu_templates.py    # 新增: 卡片模板库 + 回调路由

tests/
└── test_feishu_messages.py  # 新增: 模板测试

docs/design/
└── feishu-message-design.md  # 更新: 设计规范
```

---

## 9. 使用示例

```python
from src.adapters.feishu_templates import (
    create_intelligence_card,
    create_feedback_card,
    get_callback_router,
)
from src.adapters.feishu_adapter import FeishuAdapter

# 1. 发送情报卡片
adapter = FeishuAdapter(config)
items = [IntelligenceItem(id="1", title="...", ...)]
card = create_intelligence_card(items)
await adapter.send_card(chat_id, card)

# 2. 处理回调
router = get_callback_router()
router.register("custom_action", my_handler)

# 3. 引用回复
await adapter.send_reply(chat_id, message_id, "这是回复内容")
```

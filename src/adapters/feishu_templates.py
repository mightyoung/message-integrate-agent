# coding=utf-8
"""
Feishu Message Templates - 飞书消息模板库

基于设计文档 docs/design/feishu-message-design.md

支持:
- Interactive Card 模板
- 按钮回调处理
- 引用回复
- 反馈收集
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable

from loguru import logger


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    POST = "post"
    INTERACTIVE = "interactive"
    IMAGE = "image"
    FILE = "file"


# ==================== 模板常量 ====================

# 优先级颜色映射
PRIORITY_TEMPLATE = {
    MessagePriority.LOW: "grey",
    MessagePriority.NORMAL: "blue",
    MessagePriority.HIGH: "orange",
    MessagePriority.URGENT: "red",
}

PRIORITY_ICONS = {
    MessagePriority.LOW: "💤",
    MessagePriority.NORMAL: "📢",
    MessagePriority.HIGH: "🔥",
    MessagePriority.URGENT: "🚨",
}


# ==================== 数据结构 ====================

@dataclass
class MessageAction:
    """消息动作按钮"""
    id: str
    label: str
    action_type: str = "callback"  # callback, url
    value: str = ""
    confirm: Optional[Dict] = None

    def to_dict(self) -> Dict:
        result = {
            "tag": "button",
            "text": {"tag": "plain_text", "content": self.label},
            "type": "default",
        }

        if self.action_type == "callback":
            result["value"] = {"action_id": self.id, "value": self.value}
        elif self.action_type == "url":
            result["url"] = self.value

        return result


@dataclass
class IntelligenceItem:
    """情报条目 (用于模板)"""
    id: str
    title: str
    url: str
    category: str = ""
    score: float = 0.0
    summary: str = ""
    source: str = ""
    thumbnail: Optional[str] = None
    translated_title: Optional[str] = None  # 翻译后的标题
    translated_summary: Optional[str] = None  # 翻译后的摘要


# ==================== 模板构建器 ====================

class FeishuCardBuilder:
    """飞书卡片构建器"""

    @staticmethod
    def build_intelligence_card(
        items: List[IntelligenceItem],
        priority: MessagePriority = MessagePriority.NORMAL,
        show_pagination: bool = True,
        show_feedback: bool = True,
        use_webhook: bool = False,  # Webhook 模式兼容
    ) -> Dict:
        """构建情报推送卡片

        Args:
            items: 情报列表
            priority: 消息优先级
            show_pagination: 显示分页
            show_feedback: 显示反馈按钮
            use_webhook: 是否使用 webhook (兼容模式)

        Returns:
            Dict: 飞书卡片 JSON
        """
        template = PRIORITY_TEMPLATE.get(priority, "blue")
        icon = PRIORITY_ICONS.get(priority, "📢")

        # 构建列表元素
        item_elements = []
        for i, item in enumerate(items[:5]):
            item_elements.extend(FeishuCardBuilder._build_item_element(i, item, use_webhook))

        # 构建完整卡片
        elements = [
            # 摘要区
            {
                "tag": "markdown",
                "content": f"📊 共 {len(items)} 条更新 | 🕐 {datetime.now().strftime('%H:%M')}"
            },
        ]

        # Webhook 模式不支持 divider，跳过
        if use_webhook:
            elements.append({"tag": "divider"})

        elements.extend(item_elements)

        # 底部操作
        if show_pagination or show_feedback:
            if use_webhook:
                elements.append({"tag": "divider"})
            action_elements = []

            if show_pagination:
                action_elements.extend([
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⬅️ 上一页"},
                        "type": "default",
                        "value": {"action_id": "page_prev"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "➡️ 下一页"},
                        "type": "default",
                        "value": {"action_id": "page_next"}
                    }
                ])

            if show_feedback:
                action_elements.extend([
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📬 订阅每日"},
                        "type": "default",
                        "value": {"action_id": "subscribe_daily"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚙️ 偏好设置"},
                        "type": "default",
                        "value": {"action_id": "open_settings"}
                    }
                ])

            elements.append({
                "tag": "action",
                "actions": action_elements
            })

        return {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"{icon} 今日热点 ({len(items)}条)"
                    },
                    "template": template
                },
                "elements": elements
            }
        }

    @staticmethod
    def _build_item_element(index: int, item: IntelligenceItem, use_webhook: bool = False) -> List[Dict]:
        """构建单个情报元素

        Args:
            index: 索引
            item: 情报条目
            use_webhook: Webhook 模式兼容
        """
        elements = []

        # 分割线 - 飞书卡片不支持 divider 元素，跳过所有模式
        # if index > 0:
        #     elements.append({"tag": "divider"})

        # 使用翻译后的标题 (优先) 或原标题
        display_title = item.translated_title or item.title
        title_text = f"{index + 1}. {display_title[:40]}"
        if len(display_title) > 40:
            title_text += "..."

        # 使用翻译后的摘要 (优先) 或原摘要
        display_summary = item.translated_summary or item.summary

        # 标题和摘要 - Webhook 模式使用 markdown
        if use_webhook:
            content_text = f"🏷️ {item.category or '综合'}"
            if item.source:
                content_text += f" | 📰 {item.source}"
            content_text += f" | ⭐ {item.score:.1f}"

            content = f"**{title_text}**\n{content_text}"
            if display_summary:
                content += f"\n\n{display_summary[:100]}..."

            elements.append({
                "tag": "markdown",
                "content": content
            })

            # Webhook 模式下只显示链接
            if item.url:
                elements.append({
                    "tag": "markdown",
                    "content": f"🔗 [查看原文]({item.url})"
                })
        else:
            content_text = f"🏷️ {item.category or '综合'}"
            if item.source:
                content_text += f" | 📰 {item.source}"
            content_text += f" | ⭐ {item.score:.1f}"

            # 使用 markdown 替代 rich_text (飞书 API 不支持 rich_text)
            elements.append({
                "tag": "markdown",
                "content": f"**{title_text}**\n{content_text}"
            })

            # 添加摘要 (如果有)
            if display_summary:
                elements.append({
                    "tag": "markdown",
                    "content": f"📝 {display_summary[:100]}..."
                })

            # 操作按钮
            actions = []
            if item.url:
                actions.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔗 原文"},
                    "type": "primary",
                    "url": item.url
                })

            actions.extend([
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "👍"},
                    "type": "default",
                    "value": {"action_id": "feedback_useful", "item_id": item.id}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "👎"},
                    "type": "default",
                    "value": {"action_id": "feedback_not_useful", "item_id": item.id}
                }
            ])

            elements.append({
                "tag": "action",
                "actions": actions
            })

        return elements

    @staticmethod
    def build_feedback_card(
        title: str = "📝 内容反馈",
        content: str = "这篇内容对您有帮助吗？",
        item_id: str = "",
        use_webhook: bool = False,
    ) -> Dict:
        """构建反馈请求卡片

        Args:
            title: 标题
            content: 描述
            item_id: 关联条目ID
            use_webhook: 是否使用 webhook (兼容模式)

        Returns:
            Dict: 飞书卡片 JSON
        """
        # Webhook 模式不支持交互按钮，回退到纯文本
        if use_webhook:
            return {
                "msg_type": "text",
                "content": {"text": f"{title}\n{content}"}
            }

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "👍 有用"},
                                "type": "primary",
                                "value": {"action_id": "feedback_useful", "item_id": item_id}
                            },
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "👎 没用"},
                                "type": "default",
                                "value": {"action_id": "feedback_not_useful", "item_id": item_id}
                            },
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "💬 提建议"},
                                "type": "default",
                                "value": {"action_id": "feedback_suggest", "item_id": item_id}
                            }
                        ]
                    }
                ]
            }
        }

    @staticmethod
    def build_agent_response(
        response: str,
        actions: Optional[List[MessageAction]] = None,
        quoted_content: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        use_webhook: bool = False,
    ) -> Dict:
        """构建 Agent 响应卡片

        Args:
            response: 响应内容
            actions: 操作按钮列表
            quoted_content: 引用内容
            priority: 优先级
            use_webhook: 是否使用 webhook (兼容模式)

        Returns:
            Dict: 飞书卡片 JSON
        """
        template = PRIORITY_TEMPLATE.get(priority, "green")

        elements = [
            {
                "tag": "markdown",
                "content": response
            }
        ]

        # 引用内容 - Webhook 模式不支持 quote
        if quoted_content and not use_webhook:
            # 使用 markdown 替代 rich_text + quote (飞书不支持)
            elements.append({
                "tag": "markdown",
                "content": f"> {quoted_content[:100]}"
            })

        # 操作按钮 - Webhook 模式跳过交互按钮
        if actions and not use_webhook:
            # elements.append({"tag": "divider"})  # 飞书不支持 divider
            elements.append({
                "tag": "action",
                "actions": [a.to_dict() for a in actions]
            })

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "🤖 AI 助手"},
                    "template": template
                },
                "elements": elements
            }
        }

    @staticmethod
    def build_confirm_card(
        title: str,
        content: str,
        confirm_action: MessageAction,
        cancel_label: str = "取消"
    ) -> Dict:
        """构建确认卡片

        Args:
            title: 标题
            content: 描述
            confirm_action: 确认操作
            cancel_label: 取消按钮文本

        Returns:
            Dict: 飞书卡片 JSON
        """
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "orange"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content
                    },
                    {
                        "tag": "action",
                        "actions": [
                            confirm_action.to_dict(),
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": cancel_label},
                                "type": "default",
                                "value": {"action_id": "cancel"}
                            }
                        ]
                    }
                ]
            }
        }

    @staticmethod
    def build_text_message(content: str) -> Dict:
        """构建纯文本消息"""
        return {
            "msg_type": "text",
            "content": {"text": content}
        }


# ==================== 回调处理器 ====================

CallbackHandler = Callable[[str, Dict, str], Awaitable[Dict]]
"""回调处理器类型: (user_id, value, message_id) -> response_dict"""


class CallbackRouter:
    """回调路由器 - 处理卡片按钮点击"""

    def __init__(self):
        self._handlers: Dict[str, CallbackHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认处理器"""
        # 反馈处理器
        self.register("feedback_useful", self._handle_feedback_useful)
        self.register("feedback_not_useful", self._handle_feedback_not_useful)
        self.register("feedback_suggest", self._handle_feedback_suggest)

        # 分页处理器
        self.register("page_prev", self._handle_page_prev)
        self.register("page_next", self._handle_page_next)

        # 设置处理器
        self.register("subscribe_daily", self._handle_subscribe_daily)
        self.register("open_settings", self._handle_open_settings)

    def register(self, action_id: str, handler: CallbackHandler):
        """注册回调处理器"""
        self._handlers[action_id] = handler
        logger.info(f"[CallbackRouter] 注册处理器: {action_id}")

    async def handle(self, action_id: str, value: Dict, user_id: str, message_id: str = "") -> Dict:
        """处理回调

        Args:
            action_id: 动作ID
            value: 传递的值
            user_id: 用户ID
            message_id: 消息ID

        Returns:
            Dict: 响应消息 (用于更新原消息)
        """
        handler = self._handlers.get(action_id)

        if handler:
            try:
                return await handler(user_id, value, message_id)
            except Exception as e:
                logger.error(f"[CallbackRouter] 处理回调失败: {action_id}, {e}")
                return FeishuCardBuilder.build_text_message("❌ 处理失败，请重试")
        else:
            logger.warning(f"[CallbackRouter] 未找到处理器: {action_id}")
            return FeishuCardBuilder.build_text_message("未知的操作")

    # 默认处理器实现

    async def _handle_feedback_useful(self, user_id: str, value: Dict, message_id: str) -> Dict:
        """处理点赞"""
        item_id = value.get("item_id", "")
        logger.info(f"[Feedback] 用户 {user_id} 点赞 item: {item_id}")

        return FeishuCardBuilder.build_text_message("感谢您的反馈！👍 您的支持是我们改进的动力")

    async def _handle_feedback_not_useful(self, user_id: str, value: Dict, message_id: str) -> Dict:
        """处理点踩"""
        item_id = value.get("item_id", "")
        logger.info(f"[Feedback] 用户 {user_id} 点踩 item: {item_id}")

        return FeishuCardBuilder.build_text_message("抱歉内容不符合您的期望 😔 我们会继续优化")

    async def _handle_feedback_suggest(self, user_id: str, value: Dict, message_id: str) -> Dict:
        """处理建议"""
        item_id = value.get("item_id", "")
        logger.info(f"[Feedback] 用户 {user_id} 建议 item: {item_id}")

        # 返回一个输入框卡片
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "💬 提交建议"},
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": "请告诉我们如何改进："
                    },
                    {
                        "tag": "input",
                        "label": "您的建议",
                        "element": {
                            "tag": "plain_text_input",
                            "placeholder": {"tag": "plain_text", "content": "输入您的建议..."},
                            "value": item_id  # 隐藏值携带item_id
                        }
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "提交"},
                                "type": "primary",
                                "value": {"action_id": "submit_suggestion"}
                            }
                        ]
                    }
                ]
            }
        }

    async def _handle_page_prev(self, user_id: str, value: Dict, message_id: str) -> Dict:
        """处理上一页"""
        logger.info(f"[Pagination] 用户 {user_id} 请求上一页")
        return FeishuCardBuilder.build_text_message("📄 已经是第一页了")

    async def _handle_page_next(self, user_id: str, value: Dict, message_id: str) -> Dict:
        """处理下一页"""
        logger.info(f"[Pagination] 用户 {user_id} 请求下一页")
        # TODO: 加载下一页数据
        return FeishuCardBuilder.build_text_message("📄 加载更多情报...")

    async def _handle_subscribe_daily(self, user_id: str, value: Dict, message_id: str) -> Dict:
        """处理订阅"""
        logger.info(f"[Subscribe] 用户 {user_id} 订阅每日简报")
        return FeishuCardBuilder.build_confirm_card(
            title="📬 订阅确认",
            content="您确定要订阅每日简报吗？我们将每天为您推送精选情报。",
            confirm_action=MessageAction(
                id="confirm_subscribe",
                label="确认订阅",
                action_type="callback",
                value=user_id
            )
        )

    async def _handle_open_settings(self, user_id: str, value: Dict, message_id: str) -> Dict:
        """处理打开设置"""
        logger.info(f"[Settings] 用户 {user_id} 打开设置")
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "⚙️ 偏好设置"},
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": "选择您感兴趣的类别："
                    },
                    {
                        "tag": "checkboxes",
                        "options": [
                            {"text": {"tag": "plain_text", "content": "🌍 地缘政治"}, "value": "geopolitics"},
                            {"text": {"tag": "plain_text", "content": "⚔️ 军事"}, "value": "military"},
                            {"text": {"tag": "plain_text", "content": "💻 科技"}, "value": "tech"},
                            {"text": {"tag": "plain_text", "content": "💰 经济"}, "value": "economy"},
                        ]
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "保存设置"},
                                "type": "primary",
                                "value": {"action_id": "save_settings"}
                            }
                        ]
                    }
                ]
            }
        }


# ==================== 便捷函数 ====================

# 全局回调路由器
_callback_router: Optional[CallbackRouter] = None


def get_callback_router() -> CallbackRouter:
    """获取全局回调路由器"""
    global _callback_router
    if _callback_router is None:
        _callback_router = CallbackRouter()
    return _callback_router


def create_intelligence_card(items: List[IntelligenceItem], **kwargs) -> Dict:
    """创建情报推送卡片"""
    return FeishuCardBuilder.build_intelligence_card(items, **kwargs)


def create_feedback_card(**kwargs) -> Dict:
    """创建反馈卡片"""
    return FeishuCardBuilder.build_feedback_card(**kwargs)


def create_agent_response(response: str, **kwargs) -> Dict:
    """创建 Agent 响应卡片"""
    return FeishuCardBuilder.build_agent_response(response, **kwargs)

"""
Feishu (Lark) message adapter

Implementation of the Feishu (飞书) platform adapter.
Supports both webhook and WebSocket long connection modes for receiving and sending messages.

飞书文档: https://open.feishu.cn/document/
消息设计规范: docs/design/feishu-message-design.md

长连接模式:
    - 使用飞书官方 SDK 的 WebSocket 功能
    - 只需要客户端能访问外网，不需要公网 IP
    - 配置方式: connection_mode = "websocket"
"""
import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

# 全局网关引用，用于处理 WebSocket 消息
_global_gateway = None


def set_gateway(gateway):
    """设置全局网关引用"""
    global _global_gateway
    _global_gateway = gateway


def get_gateway():
    """获取全局网关引用"""
    return _global_gateway

from src.adapters.base import AdapterMessage, BaseAdapter
from src.adapters.capabilities import (
    ChannelCapabilities,
    ChatType,
    StandardCapabilities,
)


# 飞书消息事件类型
FEISHU_EVENT_TYPES = {
    "im.message.receive_v1": "接收消息",
    "im.message.receive_at_v1": "接收@消息",
    "im.message.group_at_msg_receive_v1": "群聊@消息",
    "im.message.p2_msg_receive_v1": "消息事件",
}


class FeishuAdapter(BaseAdapter):
    """
    Adapter for Feishu (Lark) open platform.

    飞书 (Feishu/Lark) is an enterprise collaboration platform
    by ByteDance. Supports:
    - Webhook receiving (bot mode)
    - WebSocket long connection (recommended for internal network)
    - API sending (app mode)
    - Rich message types

    连接模式:
        - webhook: 需要公网 URL 暴露服务
        - websocket: 只需要能访问外网，SDK 自动建立长连接
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id = config.get("app_id")
        self.app_secret = config.get("app_secret")
        self.verification_token = config.get("verification_token")
        self.webhook_url = config.get("webhook_url")

        # 长连接模式配置
        self.connection_mode = config.get("connection_mode", "webhook")  # webhook 或 websocket
        self._ws_client = None
        self._ws_task = None

        self._tenant_access_token = None
        self._token_expires_at = 0
        self.api_base = "https://open.feishu.cn/open-apis"

    @property
    def platform_id(self) -> str:
        """Return platform identifier."""
        return "feishu"

    @property
    def capabilities(self) -> ChannelCapabilities:
        """
        Return Feishu channel capabilities.

        飞书支持:
        - 私聊 (direct)
        - 群聊 (group)
        - 表情 reactions
        - 引用回复
        - 图片/文件 media
        """
        return ChannelCapabilities(
            chat_types=[ChatType.DIRECT, ChatType.GROUP],
            reactions=True,
            reply=True,
            media=True,
            text_chunk_limit=4000,
            supports_webhook=True,
            supports_polling=True,  # 支持轮询获取消息
            supports_websocket=True,  # 支持 WebSocket 长连接
        )

    async def connect(self) -> bool:
        """Connect to Feishu API or WebSocket."""
        if not self.app_id or not self.app_secret:
            logger.error("Feishu app_id or app_secret not configured")
            return False

        try:
            # 获取 tenant access token (两种模式都需要)
            token = await self._get_tenant_access_token()
            if not token:
                logger.error("Failed to get Feishu access token")
                return False

            # 根据连接模式选择
            if self.connection_mode == "websocket":
                # WebSocket 长连接模式
                return await self._start_websocket()
            else:
                # Webhook 模式 (默认)
                self.enabled = True
                logger.info("Connected to Feishu (webhook mode)")
                return True

        except Exception as e:
            logger.error(f"Failed to connect to Feishu: {e}")
            return False

    async def _start_websocket(self) -> bool:
        """
        启动 WebSocket 长连接

        使用飞书官方 SDK 建立 WebSocket 长连接，
        实时接收消息事件。
        """
        try:
            from src.adapters.feishu_ws_client import FeishuWebSocketClient

            # 创建 WebSocket 客户端
            self._ws_client = FeishuWebSocketClient(
                app_id=self.app_id,
                app_secret=self.app_secret,
                on_message=self._handle_ws_message,
                on_connect=self._on_ws_connect,
                on_disconnect=self._on_ws_disconnect,
            )

            # 启动 WebSocket 客户端 (在后台线程运行)
            try:
                self._ws_client.start_async()
                logger.info("飞书 WebSocket 客户端已在后台启动")
            except Exception as e:
                logger.error(f"Failed to start Feishu WebSocket client: {e}")
                return False

            self.enabled = True
            logger.info("Connected to Feishu (WebSocket long connection)")
            return True

        except Exception as e:
            logger.error(f"Failed to start Feishu WebSocket: {e}")
            return False

    def _handle_ws_message(self, message_data: Dict[str, Any]):
        """处理 WebSocket 接收到的消息"""
        try:
            logger.info(f"WebSocket 收到消息: {message_data}")

            # 从 WebSocket 事件构建类似 webhook 的 payload
            # 飞书 WebSocket 事件格式: {"type": "im.message", "event": {...}}
            event_type = message_data.get("type", "")

            # 处理 p2 事件类型 (使用 builder 注册的事件)
            if event_type.startswith("p2."):
                actual_type = event_type[3:]  # 去掉 "p2." 前缀
                event = message_data.get("event", {})

                if actual_type == "im.message.receive_v1":
                    asyncio.create_task(self._handle_ws_message_event(message_data))
                elif actual_type == "application.bot.menu_v6":
                    asyncio.create_task(self._handle_ws_menu_event(message_data))
                elif actual_type == "im.chat.access_event.bot_p2p_chat_entered_v1":
                    asyncio.create_task(self._handle_ws_bot_entered_event(message_data))
                else:
                    logger.info(f"[Feishu WS] 未处理的 P2 事件类型: {actual_type}")
                return

            # 兼容旧的事件类型
            if event_type == "im.menu":
                # 菜单事件 - 异步处理
                asyncio.create_task(self._handle_ws_menu_event(message_data))
            elif event_type == "im.message":
                # 消息事件 - 异步处理
                asyncio.create_task(self._handle_ws_message_event(message_data))
            else:
                logger.info(f"[Feishu WS] 未处理的事件类型: {event_type}")

        except Exception as e:
            logger.error(f"处理 WebSocket 消息失败: {e}")

    async def _handle_ws_menu_event(self, message_data: Dict[str, Any]):
        """处理 WebSocket 菜单事件"""
        try:
            # lark_oapi SDK 返回的是对象，不是字典
            event_obj = message_data.get("event")

            if hasattr(event_obj, 'event') and event_obj.event:
                # SDK 对象格式
                event_data = event_obj.event
                operator = getattr(event_data, 'operator', None)
                event_key = getattr(event_data, 'event_key', "")

                user_id = ""
                if operator:
                    user_id = getattr(operator, 'user_id', "") if hasattr(operator, 'user_id') else str(operator)

                logger.info(f"[Feishu WS Menu] event_key={event_key}, user={user_id}")

                # 导入菜单处理器
                from src.router.menu_handler import get_menu_handler
                menu_handler = get_menu_handler()

                # 构建事件结构 (与 Webhook 格式一致)
                ws_event = {
                    "event": {
                        "type": "im.menu",
                        "menu_event": {
                            "menu_event_id": event_key,
                            "user_id": user_id,
                            "chat_id": ""
                        }
                    }
                }

                intent_result = await menu_handler.handle_menu_event(ws_event)
                if intent_result:
                    response = await self._execute_menu_intent(intent_result)
                    logger.info(f"[Feishu WS Menu] 处理完成: {intent_result.intent}")
                else:
                    logger.warning(f"[Feishu WS Menu] 无法处理菜单事件: {event_key}")
            else:
                # 字典格式 (兼容旧代码)
                event = message_data.get("event", {})
                menu_type = event.get("type", "")
                user_id = event.get("user_id", "")

                if menu_type == "im.menu":
                    menu_data = event.get("menu_event", {})
                    menu_event_id = menu_data.get("menu_event_id", "")
                    chat_id = menu_data.get("chat_id", "")

                    logger.info(f"[Feishu WS Menu] menu_event_id={menu_event_id}, user={user_id}")

                    # 导入菜单处理器
                    from src.router.menu_handler import get_menu_handler
                    menu_handler = get_menu_handler()

                    # 构建事件结构 (与 Webhook 格式一致)
                    ws_event = {
                        "event": {
                            "type": "im.menu",
                            "menu_event": {
                                "menu_event_id": menu_event_id,
                                "user_id": user_id,
                                "chat_id": chat_id
                            }
                        }
                    }

                    intent_result = await menu_handler.handle_menu_event(ws_event)
                    if intent_result:
                        response = await self._execute_menu_intent(intent_result)
                        logger.info(f"[Feishu WS Menu] 处理完成: {intent_result.intent}")
                    else:
                        logger.warning(f"[Feishu WS Menu] 无法处理菜单事件: {menu_event_id}")

        except Exception as e:
            logger.error(f"处理 WebSocket 菜单事件失败: {e}")

    async def _handle_ws_message_event(self, message_data: Dict[str, Any]):
        """处理 WebSocket 消息事件"""
        try:
            # lark_oapi SDK 返回的是对象，不是字典
            event_obj = message_data.get("event")

            if hasattr(event_obj, 'event') and event_obj.event:
                # SDK 对象格式
                event_data = event_obj.event
                message = getattr(event_data, 'message', None)
                sender = getattr(event_data, 'sender', None)

                message_id = getattr(message, 'message_id', "") if message else ""
                content = getattr(message, 'content', "") if message else ""
                chat_id = getattr(message, 'chat_id', "") if message else ""
                user_id = getattr(sender, 'sender_id', "") if sender else ""
                if user_id:
                    user_id = getattr(user_id, 'open_id', "") if hasattr(user_id, 'open_id') else str(user_id)
            else:
                # 字典格式 (兼容旧代码)
                event = message_data.get("event", {})
                message = event.get("message", {})
                message_id = message.get("message_id", "")
                content = message.get("content", "")
                user_id = event.get("user_id", "")
                chat_id = event.get("chat_id", "")

            logger.info(f"[Feishu WS Message] message_id={message_id}, user={user_id}, content={content}")

            # 解析消息内容 (飞书消息内容是 JSON 格式)
            try:
                import json
                content_obj = json.loads(content) if content else {}
                text = content_obj.get("text", "")
            except:
                text = content

            if not text:
                logger.info("[Feishu WS Message] 消息内容为空，跳过")
                return

            logger.info(f"[Feishu WS Message] 用户消息: {text}")

            # 通过网关处理消息 (意图识别 + 执行)
            gateway = get_gateway()

            if gateway:
                # 构建消息对象
                from dataclasses import dataclass

                @dataclass
                class WSAdapterMessage:
                    platform: str = "feishu"
                    message_id: str = ""
                    user_id: str = ""
                    content: str = ""
                    chat_id: str = ""

                msg = WSAdapterMessage(
                    platform="feishu",
                    message_id=message_id,
                    user_id=user_id,
                    content=text,
                    chat_id=chat_id
                )

                # 通过网关处理消息
                response = await gateway._process_platform_message(msg)
                logger.info(f"[Feishu WS Message] 意图识别完成，响应: {response}")

                # 发送响应给用户
                if response:
                    await self.send_message(
                        chat_id=chat_id,
                        content=response,
                        msg_type="text"
                    )
                    logger.info(f"[Feishu WS Message] 响应已发送")
            else:
                logger.warning("[Feishu WS Message] 网关未初始化")

        except Exception as e:
            logger.error(f"处理 WebSocket 消息事件失败: {e}")

    async def _handle_ws_bot_entered_event(self, message_data: Dict[str, Any]):
        """处理机器人进入私聊事件"""
        # 去重缓存：记录最近发送欢迎消息的 chat_id 和时间
        _welcome_cache: Dict[str, float] = {}
        _CACHE_DURATION = 60  # 60秒内不重复发送欢迎消息

        try:
            # lark_oapi SDK 返回的是对象，不是字典
            event_obj = message_data.get("event")

            if hasattr(event_obj, 'event') and event_obj.event:
                # SDK 对象格式
                event_data = event_obj.event
                chat_id = getattr(event_data, 'chat_id', "")
                operator_id = getattr(event_data, 'operator_id', None)

                user_id = ""
                if operator_id:
                    user_id = getattr(operator_id, 'open_id', "") if hasattr(operator_id, 'open_id') else str(operator_id)
            else:
                # 字典格式 (兼容旧代码)
                event = message_data.get("event", {})
                user_id = event.get("user_id", "")
                chat_id = event.get("chat_id", "")

            logger.info(f"[Feishu WS Bot Entered] user={user_id}, chat={chat_id}")

            # 去重检查：60秒内同一个 chat_id 不重复发送欢迎消息
            import time
            now = time.time()
            last_sent = _welcome_cache.get(chat_id, 0)
            if now - last_sent < _CACHE_DURATION:
                logger.info(f"[Feishu WS Bot Entered] 跳过欢迎消息 (缓存中), chat_id={chat_id}")
                return

            # 更新缓存
            _welcome_cache[chat_id] = now

            # 发送欢迎消息
            welcome_message = """👋 你好！我是消息通信中枢 Agent

我可以帮助你：
• 📰 获取热点新闻和资讯
• 🔍 搜索各类信息
• 📚 查找学术论文
• 💬 智能对话

直接发送消息开始使用吧！"""

            await self.send_message(
                chat_id=chat_id,
                content=welcome_message
            )
            logger.info(f"[Feishu WS Bot Entered] 欢迎消息已发送")

        except Exception as e:
            logger.error(f"处理机器人进入事件失败: {e}")

    def _on_ws_connect(self):
        """WebSocket 连接成功回调"""
        logger.info("飞书 WebSocket 长连接已建立")

    def _on_ws_disconnect(self):
        """WebSocket 断开连接回调"""
        logger.warning("飞书 WebSocket 长连接已断开，正在重连...")

    async def disconnect(self):
        """Disconnect from Feishu."""
        # 停止 WebSocket
        if self._ws_client:
            try:
                self._ws_client.stop()
            except Exception as e:
                logger.error(f"Error stopping WebSocket client: {e}")

        self.enabled = False
        self._tenant_access_token = None
        logger.info("Disconnected from Feishu")

    async def _get_tenant_access_token(self) -> Optional[str]:
        """Get Feishu tenant access token."""
        if self._tenant_access_token and time.time() < self._token_expires_at:
            return self._tenant_access_token

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/auth/v3/tenant_access_token/internal",
                    json={
                        "app_id": self.app_id,
                        "app_secret": self.app_secret,
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        self._tenant_access_token = data["tenant_access_token"]
                        # Token expires in ~2 hours, refresh after 1.5 hours
                        self._token_expires_at = time.time() + 5400
                        return self._tenant_access_token
                    else:
                        logger.error(f"Feishu token error: {data}")
        except Exception as e:
            logger.error(f"Failed to get Feishu token: {e}")

        return None

    async def send_message(
        self,
        chat_id: str,
        content: str,
        chat_type: str = "direct",
        **kwargs
    ) -> bool:
        """
        Send a message to a Feishu chat.

        Args:
            chat_id: The target chat ID
            content: Message content
            chat_type: Type of chat (direct, group)
        """
        # If webhook URL is configured, use it
        if self.webhook_url:
            return await self._send_via_webhook(content)

        # Otherwise use API
        token = await self._get_tenant_access_token()
        if not token:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/im/v1/messages",
                    params={"receive_id_type": "chat_id"},
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "receive_id": chat_id,
                        "msg_type": "text",
                        "content": f'{{"text": "{content}"}}',
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Feishu message: {e}")
            return False

    async def send_card(
        self,
        chat_id: str,
        card: Dict,
        chat_type: str = "direct",
    ) -> bool:
        """
        Send an Interactive Card message.

        Args:
            chat_id: The target chat ID
            card: Card JSON (from feishu_templates)
            chat_type: Type of chat (direct, group)

        Returns:
            bool: Success status
        """
        token = await self._get_tenant_access_token()
        if not token:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/im/v1/messages",
                    params={"receive_id_type": "chat_id"},
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "receive_id": chat_id,
                        "msg_type": "interactive",
                        "content": json.dumps(card, ensure_ascii=False),
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        logger.info(f"Card sent to {chat_id}")
                        return True
                    else:
                        logger.error(f"Card send error: {data}")
                return False
        except Exception as e:
            logger.error(f"Failed to send card: {e}")
            return False

    async def send_reply(
        self,
        chat_id: str,
        message_id: str,
        content: str,
        msg_type: str = "text",
    ) -> bool:
        """
        Send a reply to a message (quote reply).

        Args:
            chat_id: The target chat ID
            message_id: The message to reply to
            content: Reply content
            msg_type: Message type (text, interactive)

        Returns:
            bool: Success status
        """
        token = await self._get_tenant_access_token()
        if not token:
            return False

        try:
            # 构建引用内容
            if msg_type == "text":
                content_json = {"text": content}
            else:
                content_json = content  # Card JSON

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/im/v1/messages",
                    params={
                        "receive_id_type": "chat_id",
                        "msg_type": msg_type,
                    },
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "receive_id": chat_id,
                        "msg_type": msg_type,
                        "content": json.dumps(content_json, ensure_ascii=False) if msg_type == "interactive" else json.dumps(content_json),
                        "reply_id": message_id,  # 引用回复
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        logger.info(f"Reply sent to {message_id}")
                        return True
                    else:
                        logger.error(f"Reply send error: {data}")
                return False
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")
            return False

    async def update_card(
        self,
        message_id: str,
        card: Dict,
    ) -> bool:
        """
        Update an existing card message.

        Args:
            message_id: The message ID to update
            card: New card JSON

        Returns:
            bool: Success status
        """
        token = await self._get_tenant_access_token()
        if not token:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.api_base}/im/v1/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "msg_type": "interactive",
                        "content": json.dumps(card, ensure_ascii=False),
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to update card: {e}")
            return False

    async def handle_callback(
        self,
        callback_data: Dict,
    ) -> Optional[Dict]:
        """
        Handle card button callback.

        Args:
            callback_data: Callback data from webhook

        Returns:
            Optional[Dict]: Response card/message to send back
        """
        try:
            # 解析回调数据
            action_id = callback_data.get("action_id", "")
            value = callback_data.get("value", {})
            user_id = callback_data.get("user_id", "")
            message_id = callback_data.get("message_id", "")

            logger.info(f"[Feishu Callback] action={action_id}, user={user_id}")

            # 使用回调路由器处理
            from src.adapters.feishu_templates import get_callback_router
            router = get_callback_router()

            response = await router.handle(action_id, value, user_id, message_id)
            return response

        except Exception as e:
            logger.error(f"Callback handling error: {e}")
            return None

    async def _execute_menu_intent(
        self,
        intent_result,
    ) -> Optional[str]:
        """执行菜单意图

        根据用户点击的菜单项执行相应的操作。

        Args:
            intent_result: IntentResult from menu handler

        Returns:
            响应消息文本
        """
        intent = intent_result.intent
        params = intent_result.params

        try:
            # ==================== 情报类意图 ====================
            if intent == "view_hot_news":
                return "📰 正在获取热点新闻，请稍候...\n\n(功能开发中)"

            elif intent == "view_category_news":
                category = params.get("category", "tech")
                category_names = {
                    "tech": "科技",
                    "ai": "AI人工智能",
                    "investment": "投资并购",
                    "report": "行业报告"
                }
                category_name = category_names.get(category, category)
                return f"📰 正在获取{category_name}，请稍候...\n\n(功能开发中)"

            # ==================== 搜索类意图 ====================
            elif intent == "search_intelligence":
                search_type = params.get("type", "news")
                return f"🔍 请输入您想搜索的关键词，我将为您查找{search_type}...\n\n(功能开发中)"

            elif intent == "search_advanced":
                return """🔍 高级搜索功能

请提供以下信息：
• 关键词：
• 时间范围：
• 来源偏好：
• 其他筛选条件：

(功能开发中)"""

            # ==================== 系统类意图 ====================
            elif intent == "get_settings":
                return """⚙️ 当前配置

• 推送频率: 每日 2 次
• 推送时间: 09:00, 18:00
• 语言: 中文
• 消息格式: 卡片

回复"设置"可修改配置。"""

            elif intent == "change_settings":
                key = params.get("key", "unknown")
                if key == "frequency":
                    return """⚙️ 推送频率设置

当前: 每日 2 次

请选择:
1. 每日 1 次
2. 每日 2 次
3. 每日 3 次
4. 每周 1 次
5. 关闭推送

请回复数字或"取消"。"""
                elif key == "language":
                    return """⚙️ 语言设置

当前: 中文

请选择:
1. 中文
2. English

请回复数字或"取消"。"""
                else:
                    return f"⚙️ 正在修改设置: {key}\n\n(功能开发中)"

            elif intent == "clear_history":
                return "🗑️ 会话历史已清除，欢迎继续使用！"

            # ==================== 默认处理 ====================
            else:
                logger.warning(f"未知菜单意图: {intent}")
                return f"已收到您的操作: {intent}\n\n(功能开发中)"

        except Exception as e:
            logger.error(f"执行菜单意图失败: {e}")
            return "抱歉，处理您的请求时出现错误，请稍后重试。"

    async def get_message(self, message_id: str) -> Optional[AdapterMessage]:
        """Get a message by ID."""
        token = await self._get_tenant_access_token()
        if not token:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/im/v1/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        msg = data["data"]["message"]
                        return self._parse_message(msg)
        except Exception as e:
            logger.error(f"Failed to get Feishu message: {e}")

        return None

    async def get_chat_messages(
        self,
        chat_id: str,
        limit: int = 20,
        before_message_id: Optional[str] = None,
    ) -> List[AdapterMessage]:
        """获取群聊消息列表 (用于轮询)

        Args:
            chat_id: 群聊ID
            limit: 获取数量
            before_message_id: 用于分页的消息ID

        Returns:
            消息列表
        """
        token = await self._get_tenant_access_token()
        if not token:
            return []

        try:
            async with httpx.AsyncClient() as client:
                params = {"limit": limit}
                if before_message_id:
                    params["before_message_id"] = before_message_id

                response = await client.get(
                    f"{self.api_base}/im/v1/chats/{chat_id}/messages",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        items = data.get("data", {}).get("items", [])
                        return [self._parse_message(msg) for msg in items]
        except Exception as e:
            logger.error(f"Failed to get chat messages: {e}")

        return []

    async def poll_messages(
        self,
        chat_id: str,
        last_message_id: Optional[str] = None,
    ) -> List[AdapterMessage]:
        """轮询获取新消息

        Args:
            chat_id: 群聊ID
            last_message_id: 上次最后一条消息ID

        Returns:
            新消息列表
        """
        messages = await self.get_chat_messages(chat_id, limit=50)

        if not last_message_id:
            return messages  # 首次调用返回所有消息

        # 过滤新消息
        new_messages = []
        for msg in messages:
            if msg.message_id == last_message_id:
                break
            new_messages.append(msg)

        return new_messages

    async def _send_via_webhook(self, content: str) -> bool:
        """Send message via webhook URL."""
        if not self.webhook_url:
            logger.error("No webhook URL configured")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json={
                        "msg_type": "text",
                        "content": {"text": content}
                    }
                )
                if response.status_code == 200:
                    logger.info("Message sent via Feishu webhook")
                    return True
                else:
                    logger.error(f"Failed to send via webhook: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error sending via webhook: {e}")
            return False

    def _parse_message(self, raw: dict) -> AdapterMessage:
        """Parse Feishu message to AdapterMessage."""
        body = raw.get("body", {})
        sender = raw.get("sender", {})

        # Extract content
        content = ""
        msg_type = raw.get("msg_type", "text")
        raw_content = raw.get("content", {})

        if msg_type == "text":
            content = raw_content.get("text", "")
        elif msg_type == "post":
            # Handle post type messages
            content = str(raw_content)

        return AdapterMessage(
            platform="feishu",
            message_id=raw.get("message_id", ""),
            user_id=sender.get("sender_id", {}).get("open_id", ""),
            content=content,
            raw=raw,
            metadata={
                "msg_type": msg_type,
                "chat_id": raw.get("chat_id", ""),
            }
        )

    async def handle_webhook(self, payload: Dict[str, Any]) -> Optional[AdapterMessage]:
        """Handle incoming Feishu webhook."""
        try:
            # Verify verification token if provided
            if self.verification_token:
                challenge = payload.get("challenge")
                if challenge:
                    # This is a verification request
                    return None

            # 检查是否为回调事件 (卡片按钮点击)
            callback_type = payload.get("type")
            if callback_type == "callback":
                # 处理卡片按钮回调
                callback_data = payload.get("action_response", {}).get("value", {})
                action_id = callback_data.get("action_id", "")
                value = callback_data
                user_id = payload.get("operator_id", {}).get("user_id", "")
                message_id = payload.get("message_id", "")

                logger.info(f"[Feishu Callback] action={action_id}, user={user_id}")

                # 调用回调处理器
                response = await self.handle_callback({
                    "action_id": action_id,
                    "value": value,
                    "user_id": user_id,
                    "message_id": message_id
                })

                # 可以选择发送响应消息
                if response:
                    logger.info(f"[Feishu Callback] Response: {response}")

                return None  # 回调不需要返回消息

            # ==================== 处理菜单事件 ====================
            event_type = payload.get("type")
            if event_type == "im.menu":
                # 处理飞书自定义菜单点击事件
                menu_event = payload.get("event", {})
                menu_type = menu_event.get("type")

                if menu_type == "im.menu":
                    menu_data = menu_event.get("menu_event", {})
                    menu_event_id = menu_data.get("menu_event_id", "")
                    user_id = menu_data.get("user_id", "")
                    chat_id = menu_data.get("chat_id", "")

                    logger.info(f"[Feishu Menu] menu_event_id={menu_event_id}, user={user_id}")

                    # 导入菜单处理器
                    from src.router.menu_handler import get_menu_handler

                    menu_handler = get_menu_handler()

                    # 构建事件结构
                    event = {
                        "event": {
                            "menu_event": {
                                "menu_event_id": menu_event_id,
                                "user_id": user_id,
                                "chat_id": chat_id
                            }
                        }
                    }

                    # 获取意图结果
                    intent_result = await menu_handler.handle_menu_event(event)

                    if intent_result:
                        # 根据意图执行相应操作
                        response = await self._execute_menu_intent(intent_result)

                        # 发送响应消息给用户 (私聊)
                        if response:
                            await self.send_message(
                                chat_id=user_id,  # 私聊发送
                                content=response
                            )

                        logger.info(f"[Feishu Menu] Executed: {intent_result.intent}")

                return None  # 菜单事件不需要返回标准消息

            # Parse message event
            event = payload.get("event", {})
            if event.get("msg_type") == "text":
                message = event.get("message", {})
                if message:
                    # 检查是否为反馈消息
                    chat_id = message.get("chat_id", "")
                    user_id = message.get("sender_id", {}).get("open_id", "")
                    content = message.get("body", {}).get("content", "")
                    message_id = message.get("message_id", "")

                    # 解析文本内容
                    import json
                    try:
                        text_content = json.loads(content).get("text", "") if content else ""
                    except:
                        text_content = content

                    # 处理反馈消息
                    feedback_response = await self._handle_feedback_message(
                        text_content, user_id, chat_id, message_id
                    )

                    if feedback_response:
                        # 发送反馈响应消息
                        await self.send_message(chat_id, feedback_response)

                    return self._parse_message(message)

            # 处理回调类型的消息事件
            if event.get("msg_type") == "interactive":
                # 这是卡片消息的回调
                message = event.get("message", {})
                callback_value = message.get("callback_id", "")
                if callback_value:
                    logger.info(f"[Feishu] Card callback: {callback_value}")

        except Exception as e:
            logger.error(f"Error handling Feishu webhook: {e}")

        return None

    async def _handle_feedback_message(
        self,
        text: str,
        user_id: str,
        chat_id: str,
        message_id: str,
    ) -> Optional[str]:
        """处理反馈消息

        Args:
            text: 用户发送的文本
            user_id: 用户ID
            chat_id: 群聊ID
            message_id: 消息ID

        Returns:
            响应消息文本，如果不需要响应则返回 None
        """
        if not text:
            return None

        text_lower = text.lower().strip()

        # 定义反馈关键词映射
        feedback_keywords = {
            # 点赞
            "👍": "useful",
            "有用": "useful",
            "好": "useful",
            "不错": "useful",
            "喜欢": "useful",
            "good": "useful",
            "useful": "useful",
            # 点踩
            "👎": "not_useful",
            "没用": "not_useful",
            "不好": "not_useful",
            "差": "not_useful",
            "bad": "not_useful",
            "not useful": "not_useful",
            # 建议
            "建议": "suggest",
            "意见": "suggest",
            "反馈": "suggest",
            "suggest": "suggest",
        }

        # 检查是否匹配反馈关键词
        feedback_type = None
        for keyword, ftype in feedback_keywords.items():
            if keyword in text_lower:
                feedback_type = ftype
                break

        if feedback_type:
            logger.info(f"[Feedback] 用户 {user_id} 反馈类型: {feedback_type}, 内容: {text}")

            # 生成响应消息
            if feedback_type == "useful":
                return "感谢您的认可！🙏 您的支持是我们改进的动力。如有其他需求，欢迎随时告诉我。"
            elif feedback_type == "not_useful":
                return "抱歉内容不符合您的期望 😔 我们会继续优化。如果您有具体建议，请告诉我。"
            elif feedback_type == "suggest":
                return "感谢您的建议！💡 我们会认真考虑。如有更多想法，欢迎继续反馈。"

        # 检查是否是问询消息
        question_keywords = ["?", "？", "什么是", "怎么样", "如何", "怎么", "为什么", "?"
                           "what", "how", "why", "?"
                           "求助", "帮忙", "请问"]
        for keyword in question_keywords:
            if keyword in text_lower:
                logger.info(f"[Question] 用户 {user_id} 提问: {text}")
                return "收到您的提问！🤔 我正在思考中，请稍候..."

        return None

    def verify_webhook(self, payload: Dict[str, Any]) -> bool:
        """Verify Feishu webhook signature."""
        # Feishu uses verification token for webhook verification
        return payload.get("token") == self.verification_token

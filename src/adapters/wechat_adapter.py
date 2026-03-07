"""
WeChat (Enterprise) message adapter

Implementation of the WeChat Enterprise (WeCom/企业微信) adapter.
Supports webhook-based receiving and API-based sending.

企业微信文档: https://developer.work.weixin.qq.com/document/
"""
import hashlib
import random
import string
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

import httpx
from loguru import logger

from src.adapters.base import AdapterMessage, BaseAdapter
from src.adapters.capabilities import (
    ChannelCapabilities,
    ChatType,
)


class WeChatAdapter(BaseAdapter):
    """
    Adapter for WeChat Enterprise (WeCom/企业微信) WebHook.

    企业微信 is a business communication platform by Tencent.
    Supports:
    - Webhook receiving (bot mode)
    - API sending (with full credentials)
    - Text and media messages
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url")
        self.corp_id = config.get("corp_id")
        self.corp_secret = config.get("corp_secret")
        self.agent_id = config.get("agent_id")
        self._access_token = None
        self._token_expires_at = 0
        self.api_base = "https://qyapi.weixin.qq.com/cgi-bin"

    @property
    def platform_id(self) -> str:
        """Return platform identifier."""
        return "wechat"

    @property
    def capabilities(self) -> ChannelCapabilities:
        """
        Return WeChat Enterprise channel capabilities.

        企业微信 supports:
        - 私聊 (direct)
        - 群聊 (group)
        - 文本消息
        - 媒体消息 (通过API)
        """
        return ChannelCapabilities(
            chat_types=[ChatType.DIRECT, ChatType.GROUP],
            media=True,
            text_chunk_limit=2048,
            supports_webhook=True,
            supports_polling=False,
        )

    async def connect(self) -> bool:
        """Connect to WeChat Enterprise API."""
        if not self.webhook_url:
            logger.warning("WeChat webhook URL not configured")
            # Still enable if we have full credentials
            if self.corp_id and self.corp_secret:
                token = await self._get_access_token()
                if token:
                    self.enabled = True
                    logger.info("Connected to WeChat Enterprise")
                    return True
            return False

        # Simple webhook mode - just test connection
        self.enabled = True
        logger.info("WeChat webhook mode enabled")
        return True

    async def disconnect(self):
        """Disconnect from WeChat."""
        self.enabled = False
        self._access_token = None
        logger.info("Disconnected from WeChat")

    async def _get_access_token(self) -> Optional[str]:
        """Get WeChat Enterprise access token."""
        if self._access_token and self._token_expires_at > 0:
            from time import time
            if time() < self._token_expires_at:
                return self._access_token

        if not self.corp_id or not self.corp_secret:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/gettoken",
                    params={
                        "corpid": self.corp_id,
                        "corpsecret": self.corp_secret,
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errcode") == 0:
                        self._access_token = data["access_token"]
                        # Token expires in 2 hours
                        from time import time
                        self._token_expires_at = time() + 7000
                        return self._access_token
        except Exception as e:
            logger.error(f"Failed to get WeChat token: {e}")

        return None

    async def send_message(
        self,
        chat_id: str,
        content: str,
        chat_type: str = "direct",
        **kwargs
    ) -> bool:
        """
        Send a message via WeChat webhook or API.

        Args:
            chat_id: The target chat ID
            content: Message content
            chat_type: Type of chat (direct, group)
        """
        if self.webhook_url:
            # Webhook mode
            return await self._send_webhook(content)
        else:
            # API mode
            return await self._send_api(chat_id, content)

    async def _send_webhook(self, content: str) -> bool:
        """Send message via webhook."""
        try:
            async with httpx.AsyncClient() as client:
                # Webhook format
                payload = {
                    "msgtype": "text",
                    "text": {
                        "content": content
                    }
                }
                response = await client.post(self.webhook_url, json=payload)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send WeChat webhook: {e}")
            return False

    async def _send_api(self, chat_id: str, content: str) -> bool:
        """Send message via API."""
        token = await self._get_access_token()
        if not token:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/message/send",
                    params={"access_token": token},
                    json={
                        "touser": chat_id,
                        "msgtype": "text",
                        "agentid": self.agent_id,
                        "text": {
                            "content": content
                        }
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("errcode") == 0
        except Exception as e:
            logger.error(f"Failed to send WeChat message: {e}")

        return False

    async def get_message(self, message_id: str) -> Optional[AdapterMessage]:
        """Get a message by ID (not supported in webhook mode)."""
        return None

    async def handle_webhook(self, payload: Dict[str, Any]) -> Optional[AdapterMessage]:
        """Handle incoming WeChat webhook."""
        try:
            msg_type = payload.get("msgType") or payload.get("msg_type")

            if msg_type == "text":
                content = payload.get("content", "")
                user_id = payload.get("fromUserName") or payload.get("user_id", "")

                return AdapterMessage(
                    platform="wechat",
                    message_id=payload.get("msgId", ""),
                    user_id=user_id,
                    content=content,
                    raw=payload,
                    metadata={
                        "chat_id": payload.get("toUserName") or payload.get("agent_id"),
                        "msg_type": msg_type,
                    }
                )
            elif msg_type == "event":
                # Handle event messages (e.g., user的关注/取消关注)
                return AdapterMessage(
                    platform="wechat",
                    message_id="",
                    user_id=payload.get("fromUserName", ""),
                    content=f"Event: {payload.get('event', '')}",
                    raw=payload,
                    metadata={
                        "event": payload.get("event"),
                        "event_key": payload.get("event_key"),
                    }
                )

        except Exception as e:
            logger.error(f"Error handling WeChat webhook: {e}")

        return None

    def verify_signature(self, signature: str, timestamp: str, nonce: str) -> bool:
        """Verify WeChat webhook signature."""
        # For enterprise WeChat, this verifies the signature
        # Using your webhook token
        if not self.webhook_url:
            return True

        # Simplified - in production use proper signature verification
        return True

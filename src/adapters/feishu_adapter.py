"""
Feishu (Lark) message adapter

Implementation of the Feishu (飞书) platform adapter.
Supports both webhook and API modes for receiving and sending messages.

飞书文档: https://open.feishu.cn/document/
"""
import hashlib
import time
from typing import Any, Dict, Optional

import httpx
from loguru import logger

from src.adapters.base import AdapterMessage, BaseAdapter
from src.adapters.capabilities import (
    ChannelCapabilities,
    ChatType,
    StandardCapabilities,
)


class FeishuAdapter(BaseAdapter):
    """
    Adapter for Feishu (Lark) open platform.

    飞书 (Feishu/Lark) is an enterprise collaboration platform
    by ByteDance. Supports:
    - Webhook receiving (bot mode)
    - API sending (app mode)
    - Rich message types
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id = config.get("app_id")
        self.app_secret = config.get("app_secret")
        self.verification_token = config.get("verification_token")
        self.webhook_url = config.get("webhook_url")
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
            supports_polling=False,
        )

    async def connect(self) -> bool:
        """Connect to Feishu API."""
        if not self.app_id or not self.app_secret:
            logger.error("Feishu app_id or app_secret not configured")
            return False

        try:
            # Get tenant access token
            token = await self._get_tenant_access_token()
            if token:
                self.enabled = True
                logger.info("Connected to Feishu")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Feishu: {e}")
            return False

    async def disconnect(self):
        """Disconnect from Feishu."""
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

            # Parse message event
            event = payload.get("event", {})
            if event.get("msg_type") == "text":
                message = event.get("message", {})
                if message:
                    return self._parse_message(message)

        except Exception as e:
            logger.error(f"Error handling Feishu webhook: {e}")

        return None

    def verify_webhook(self, payload: Dict[str, Any]) -> bool:
        """Verify Feishu webhook signature."""
        # Feishu uses verification token for webhook verification
        return payload.get("token") == self.verification_token

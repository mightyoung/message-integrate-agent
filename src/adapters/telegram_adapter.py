"""
Telegram message adapter using aiogram

Implementation of the Telegram Bot API adapter.
Telegram is a full-featured messaging platform with support for:
- Private chats, groups, channels, and supergroups
- Rich media (photos, videos, documents, stickers)
- Polls, quizzes, and interactive buttons
- Bot commands and inline queries

Telegram Bot API: https://core.telegram.org/bots/api
"""
from typing import Any, Dict, Optional

from loguru import logger

from src.adapters.base import AdapterMessage, BaseAdapter
from src.adapters.capabilities import (
    ChannelCapabilities,
    ChatType,
    StandardCapabilities,
)


class TelegramAdapter(BaseAdapter):
    """
    Adapter for Telegram Bot API.

    Telegram is one of the most feature-rich messaging platforms,
    supporting:
    - All chat types (private, group, channel, supergroup)
    - Rich media, polls, quizzes
    - Inline queries and callbacks
    - Bot commands and keyboard buttons
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get("bot_token")
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        self._client = None

    @property
    def platform_id(self) -> str:
        """Return platform identifier."""
        return "telegram"

    @property
    def capabilities(self) -> ChannelCapabilities:
        """
        Return Telegram channel capabilities.

        Telegram is a full-featured platform with support for:
        - All chat types
        - Rich media
        - Polls and quizzes
        - Reactions and replies
        - And much more
        """
        return StandardCapabilities.FULL

    async def connect(self) -> bool:
        """Connect to Telegram API."""
        if not self.bot_token:
            logger.error("Telegram bot token not configured")
            return False

        try:
            # Test connection
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/getMe")
                if response.status_code == 200:
                    me = response.json()
                    logger.info(f"Connected to Telegram as @{me['result']['username']}")
                    self.enabled = True
                    return True
                else:
                    logger.error(f"Telegram API error: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False

    async def disconnect(self):
        """Disconnect from Telegram."""
        self.enabled = False
        logger.info("Disconnected from Telegram")

    async def send_message(
        self,
        chat_id: str,
        content: str,
        chat_type: str = "direct",
        **kwargs
    ) -> bool:
        """
        Send a message to a Telegram chat.

        Args:
            chat_id: The target chat ID
            content: Message content
            chat_type: Type of chat (direct, group, channel, thread)
        """
        import httpx

        payload = {
            "chat_id": chat_id,
            "text": content,
        }

        # Optional: add parse mode
        if kwargs.get("parse_mode"):
            payload["parse_mode"] = kwargs["parse_mode"]

        # Optional: add reply keyboard
        if kwargs.get("reply_markup"):
            payload["reply_markup"] = kwargs["reply_markup"]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/sendMessage",
                    json=payload
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def get_message(self, message_id: str) -> Optional[AdapterMessage]:
        """Get a message by ID (requires bot to be admin or in group)."""
        # Telegram doesn't support getting messages by ID for regular bots
        # This is a limitation of the Telegram Bot API
        return None

    async def handle_webhook(self, payload: Dict[str, Any]) -> Optional[AdapterMessage]:
        """Handle incoming Telegram webhook."""
        try:
            message = payload.get("message")
            if not message:
                callback_query = payload.get("callback_query")
                if callback_query:
                    message = callback_query.get("message")

            if not message:
                return None

            # Extract message data
            chat = message.get("chat", {})
            user = message.get("from", {})

            # Get text or caption (for images, etc.)
            content = message.get("text") or message.get("caption") or ""

            return AdapterMessage(
                platform="telegram",
                message_id=str(message.get("message_id", "")),
                user_id=str(user.get("id", "")),
                content=content,
                raw=payload,
                metadata={
                    "chat_id": str(chat.get("id", "")),
                    "chat_type": chat.get("type", "private"),
                    "user_name": user.get("username", ""),
                    "first_name": user.get("first_name", ""),
                }
            )
        except Exception as e:
            logger.error(f"Error handling Telegram webhook: {e}")
            return None

"""
API call and message sending tools for MCP
"""
import os
from typing import Any, Dict, Optional

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


def _get_proxies() -> dict:
    """Get proxy configuration from environment."""
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    proxies = {}
    if http_proxy:
        proxies["http://"] = http_proxy
    if https_proxy:
        proxies["https://"] = https_proxy

    return proxies if proxies else None


async def call_api(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> str:
    """
    Make HTTP API call.

    Args:
        url: Target URL
        method: HTTP method (GET, POST, PUT, DELETE)
        headers: Optional headers
        body: Request body (for POST/PUT)
        timeout: Request timeout in seconds

    Returns:
        Response text or error message
    """
    # Get proxy settings
    proxies = _get_proxies()

    # Build request headers
    request_headers = headers or {}
    if "User-Agent" not in request_headers:
        request_headers["User-Agent"] = "MessageHub/1.0"

    try:
        async with httpx.AsyncClient(proxies=proxies, timeout=timeout) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=request_headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=request_headers, json=body)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=request_headers, json=body)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=request_headers)
            else:
                return f"Error: Unsupported method {method}"

            # Try to parse JSON response
            try:
                data = response.json()
                import json
                return f"Status: {response.status_code}\n\n{json.dumps(data, indent=2, ensure_ascii=False)}"
            except Exception:
                # Return text response
                return f"Status: {response.status_code}\n\n{response.text[:2000]}"

    except httpx.TimeoutException:
        return f"Error: Request timed out after {timeout} seconds"
    except httpx.RequestError as e:
        return f"Error: Request failed - {str(e)}"
    except Exception as e:
        logger.error(f"API call error: {e}")
        return f"Error: {str(e)}"


async def send_message(
    platform: str,
    chat_id: str,
    content: str,
    **kwargs
) -> str:
    """
    Send message to a platform.

    Args:
        platform: Platform name (telegram, feishu, wechat)
        chat_id: Target chat ID
        content: Message content
        **kwargs: Additional platform-specific parameters

    Returns:
        Success or error message
    """
    from src.adapters.telegram_adapter import TelegramAdapter
    from src.adapters.feishu_adapter import FeishuAdapter
    from src.adapters.wechat_adapter import WeChatAdapter

    # Load platform config from environment
    if platform == "telegram":
        config = {
            "enabled": True,
            "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN"),
        }
        adapter = TelegramAdapter(config)
        success = await adapter.send_message(chat_id, content)
        return "Message sent to Telegram" if success else "Failed to send message to Telegram"

    elif platform == "feishu":
        config = {
            "enabled": True,
            "app_id": os.environ.get("FEISHU_APP_ID"),
            "app_secret": os.environ.get("FEISHU_APP_SECRET"),
        }
        adapter = FeishuAdapter(config)
        success = await adapter.send_message(chat_id, content)
        return "Message sent to Feishu" if success else "Failed to send message to Feishu"

    elif platform == "wechat":
        config = {
            "enabled": True,
            "webhook_url": os.environ.get("WECHAT_WEBHOOK_URL"),
        }
        adapter = WeChatAdapter(config)
        success = await adapter.send_message(chat_id, content)
        return "Message sent to WeChat" if success else "Failed to send message to WeChat"

    else:
        return f"Error: Unknown platform {platform}"

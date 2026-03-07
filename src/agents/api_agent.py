"""
API Agent implementation
"""
from typing import Any, Dict, Optional

from loguru import logger

from src.mcp.tools.api import call_api


class APIAgent:
    """
    Agent for making API calls.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)

    async def handle(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Handle an API request.

        Args:
            action: Action name (http_get, http_post, etc.)
            params: Action parameters

        Returns:
            API response
        """
        params = params or {}

        if action == "http_get":
            url = params.get("url", "")
            headers = params.get("headers")
            return await call_api(
                url=url,
                method="GET",
                headers=headers,
                timeout=self.timeout,
            )

        elif action == "http_post":
            url = params.get("url", "")
            body = params.get("body")
            headers = params.get("headers")
            return await call_api(
                url=url,
                method="POST",
                body=body,
                headers=headers,
                timeout=self.timeout,
            )

        elif action == "http_put":
            url = params.get("url", "")
            body = params.get("body")
            headers = params.get("headers")
            return await call_api(
                url=url,
                method="PUT",
                body=body,
                headers=headers,
                timeout=self.timeout,
            )

        elif action == "http_delete":
            url = params.get("url", "")
            headers = params.get("headers")
            return await call_api(
                url=url,
                method="DELETE",
                headers=headers,
                timeout=self.timeout,
            )

        else:
            return f"Unknown action: {action}"

    async def call_url(self, url: str, method: str = "GET") -> str:
        """Simple URL call."""
        return await call_api(url=url, method=method, timeout=self.timeout)

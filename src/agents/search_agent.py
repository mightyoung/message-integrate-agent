"""
Search Agent implementation
"""
from typing import Any, Dict, Optional

from loguru import logger

from src.mcp.tools.search import search_web


class SearchAgent:
    """
    Agent for handling web search queries.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.default_engine = self.config.get("default_engine", "tavily")
        self.max_results = self.config.get("max_results", 5)

    async def handle(
        self,
        message: str,
        action: Optional[str] = None,
    ) -> str:
        """
        Handle a search request.

        Args:
            message: Search query
            action: Specific action (weather, news, etc.)

        Returns:
            Search results
        """
        # Determine search parameters based on action
        engine = self.default_engine

        # Override engine based on action
        if action == "weather":
            # Weather-specific handling
            engine = "tavily"
            message = f"weather {message}"
        elif action == "news":
            engine = "google"

        logger.info(f"Searching with {engine}: {message}")

        try:
            results = await search_web(
                query=message,
                engine=engine,
                max_results=self.max_results,
            )
            return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Search failed: {str(e)}"

    async def search_with_proxy(
        self,
        query: str,
        engine: str = "tavily",
    ) -> str:
        """Search with explicit proxy configuration."""
        # This uses the built-in proxy support in search_web
        return await self.handle(query)

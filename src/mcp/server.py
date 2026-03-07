"""
MCP Server using FastMCP
"""
import asyncio
import threading
from typing import Any, Optional

from loguru import logger
from mcp.server.fastmcp import FastMCP


class MCPServer:
    """
    MCP Server that exposes tools for AI agents.
    """

    def __init__(self, name: str = "message-hub", config: Optional[dict] = None):
        self.name = name
        self.config = config or {}
        self.mcp = FastMCP(name)
        self._setup_tools()
        self._server_thread: Optional[threading.Thread] = None

    def _setup_tools(self):
        """Setup MCP tools."""
        from src.mcp.tools import search, llm, api

        # Register tools
        self.mcp.tool()(search.search_web)
        self.mcp.tool()(llm.chat_with_llm)
        self.mcp.tool()(api.call_api)
        self.mcp.tool()(api.send_message)

        logger.info("MCP tools registered")

    def run_stdio(self):
        """Run MCP server with stdio transport (blocking)."""
        logger.info(f"Starting MCP server ({self.name}) with stdio transport")
        self.mcp.run(transport="stdio")

    def _run_sse_thread(self, host: str, port: int):
        """Run SSE server in a separate thread using uvicorn."""
        import uvicorn

        logger.info(f"MCP server thread starting on {host}:{port}")
        try:
            # Get the SSE app directly from FastMCP
            sse_app = self.mcp.sse_app()

            # Run with uvicorn directly on the SSE app
            config = uvicorn.Config(sse_app, host=host, port=port, log_level="info")
            server = uvicorn.Server(config)
            server.run()
        except Exception as e:
            logger.error(f"MCP server error: {e}")

    async def run_sse(self, host: str = "0.0.0.0", port: int = 8081):
        """Run MCP server with SSE transport in background thread."""
        logger.info(f"Starting MCP server ({self.name}) on {host}:{port}")

        # Run in a separate thread with its own uvicorn server
        self._server_thread = threading.Thread(
            target=self._run_sse_thread,
            args=(host, port),
            daemon=True
        )
        self._server_thread.start()
        logger.info(f"MCP server started in background thread")

    async def stop(self):
        """Stop the MCP server."""
        logger.info("MCP server stop requested")

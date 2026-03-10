"""Router module - 消息路由"""
from src.router.keyword_router import KeywordRouter
from src.router.registry import AgentRegistry
from src.router.menu_handler import FeishuMenuHandler, IntentResult

# 延迟导入 ai_router (避免 mcp 依赖问题)
try:
    from src.router.ai_router import AIRouter
    __all__ = [
        "KeywordRouter",
        "AIRouter",
        "AgentRegistry",
        "FeishuMenuHandler",
        "IntentResult",
    ]
except ImportError:
    # mcp 未安装时跳过 AIRouter
    __all__ = [
        "KeywordRouter",
        "AgentRegistry",
        "FeishuMenuHandler",
        "IntentResult",
    ]

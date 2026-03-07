"""Router module - 消息路由"""
from src.router.keyword_router import KeywordRouter
from src.router.ai_router import AIRouter
from src.router.registry import AgentRegistry
from src.router.self_learning import SelfLearningRouter, get_self_learning_router

__all__ = [
    "KeywordRouter",
    "AIRouter",
    "AgentRegistry",
    "SelfLearningRouter",
    "get_self_learning_router",
]

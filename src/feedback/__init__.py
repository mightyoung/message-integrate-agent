"""
User Feedback System - 用户反馈系统

实现用户对AI回复质量的反馈收集：
- 显式反馈：评分、thumbs up/down
- 隐式反馈：用户行为分析
- 反馈存储与统计
- 反馈驱动的路由优化

设计参考：
- Datagrid: Safe feedback loop patterns
- 腾讯云: 用户反馈机制
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class FeedbackType(Enum):
    """反馈类型"""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"  # 1-5 stars
    COMMENT = "comment"
    CORRECTION = "correction"  # 用户纠正


class FeedbackSource(Enum):
    """反馈来源"""
    TELEGRAM = "telegram"
    FEISHU = "feishu"
    WECHAT = "wechat"
    WEBSOCKET = "websocket"
    API = "api"


@dataclass
class UserFeedback:
    """用户反馈"""
    id: str
    user_id: str
    platform: str
    message_id: str  # 被评价的消息ID
    feedback_type: FeedbackType
    value: Any  # rating: int, comment: str, correction: str
    agent_name: str  # 处理该消息的agent
    router_used: str  # 使用的路由
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackStats:
    """反馈统计"""
    total_count: int = 0
    thumbs_up_count: int = 0
    thumbs_down_count: int = 0
    avg_rating: float = 0.0
    comment_count: int = 0
    correction_count: int = 0
    by_agent: Dict[str, int] = field(default_factory=dict)
    by_router: Dict[str, int] = field(default_factory=dict)


class FeedbackStore:
    """反馈存储"""

    def __init__(self):
        self._feedbacks: Dict[str, UserFeedback] = {}
        self._user_feedbacks: Dict[str, List[str]] = {}  # user_id -> feedback_ids

    def add(self, feedback: UserFeedback) -> bool:
        """添加反馈"""
        self._feedbacks[feedback.id] = feedback

        if feedback.user_id not in self._user_feedbacks:
            self._user_feedbacks[feedback.user_id] = []
        self._user_feedbacks[feedback.user_id].append(feedback.id)

        logger.info(f"📝 收到反馈: {feedback.feedback_type.value} from {feedback.user_id}")
        return True

    def get(self, feedback_id: str) -> Optional[UserFeedback]:
        """获取反馈"""
        return self._feedbacks.get(feedback_id)

    def get_by_user(self, user_id: str) -> List[UserFeedback]:
        """获取用户的所有反馈"""
        feedback_ids = self._user_feedbacks.get(user_id, [])
        return [self._feedbacks[fid] for fid in feedback_ids if fid in self._feedbacks]

    def get_by_message(self, message_id: str) -> List[UserFeedback]:
        """获取对某消息的反馈"""
        return [f for f in self._feedbacks.values() if f.message_id == message_id]

    def get_stats(self) -> FeedbackStats:
        """获取统计信息"""
        stats = FeedbackStats()
        stats.total_count = len(self._feedbacks)

        for fb in self._feedbacks.values():
            if fb.feedback_type == FeedbackType.THUMBS_UP:
                stats.thumbs_up_count += 1
            elif fb.feedback_type == FeedbackType.THUMBS_DOWN:
                stats.thumbs_down_count += 1
            elif fb.feedback_type == FeedbackType.RATING:
                if isinstance(fb.value, (int, float)):
                    stats.avg_rating = (
                        (stats.avg_rating * (stats.comment_count) + fb.value)
                        / (stats.comment_count + 1)
                    )
                    stats.comment_count += 1
            elif fb.feedback_type == FeedbackType.COMMENT:
                stats.comment_count += 1
            elif fb.feedback_type == FeedbackType.CORRECTION:
                stats.correction_count += 1

            # 统计agent和router
            if fb.agent_name not in stats.by_agent:
                stats.by_agent[fb.agent_name] = 0
            stats.by_agent[fb.agent_name] += 1

            if fb.router_used not in stats.by_router:
                stats.by_router[fb.router_used] = 0
            stats.by_router[fb.router_used] += 1

        return stats


class FeedbackService:
    """
    用户反馈服务

    统一接口，处理反馈收集、存储、统计
    """

    def __init__(self, experience_logger=None):
        self.store = FeedbackStore()
        self.experience_logger = experience_logger

        # 反馈回调 - 当收到特定类型反馈时触发
        self._callbacks: Dict[FeedbackType, List[callable]] = {}

    def register_callback(self, feedback_type: FeedbackType, callback: callable):
        """注册反馈回调"""
        if feedback_type not in self._callbacks:
            self._callbacks[feedback_type] = []
        self._callbacks[feedback_type].append(callback)

    async def submit_feedback(
        self,
        user_id: str,
        platform: str,
        message_id: str,
        feedback_type: str,
        value: Any,
        agent_name: str = "unknown",
        router_used: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        提交反馈

        Args:
            user_id: 用户ID
            platform: 平台
            message_id: 消息ID
            feedback_type: 反馈类型 (thumbs_up, thumbs_down, rating, comment, correction)
            value: 反馈值
            agent_name: 处理的agent名称
            router_used: 使用的路由
            metadata: 额外数据

        Returns:
            反馈ID
        """
        # 验证反馈类型
        try:
            fb_type = FeedbackType(feedback_type)
        except ValueError:
            raise ValueError(f"Unknown feedback type: {feedback_type}")

        # 创建反馈
        feedback = UserFeedback(
            id=f"fb_{datetime.now().timestamp()}",
            user_id=user_id,
            platform=platform,
            message_id=message_id,
            feedback_type=fb_type,
            value=value,
            agent_name=agent_name,
            router_used=router_used,
            metadata=metadata or {},
        )

        # 存储
        self.store.add(feedback)

        # 触发回调
        await self._trigger_callbacks(feedback)

        # 如果是纠正类型，写入经验日志
        if fb_type == FeedbackType.CORRECTION and self.experience_logger:
            await self._log_correction(feedback)

        return feedback.id

    async def _trigger_callbacks(self, feedback: UserFeedback):
        """触发反馈回调"""
        callbacks = self._callbacks.get(feedback.feedback_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(feedback)
                else:
                    callback(feedback)
            except Exception as e:
                logger.error(f"反馈回调执行失败: {e}")

    async def _log_correction(self, feedback: UserFeedback):
        """将纠正写入经验日志"""
        if not self.experience_logger:
            return

        await self.experience_logger.log_error(
            error_type="user_correction",
            error_message=f"用户纠正: {feedback.value}",
            context={
                "message_id": feedback.message_id,
                "agent": feedback.agent_name,
                "router": feedback.router_used,
            },
            solution="根据用户纠正调整处理逻辑",
        )

    def get_feedback(self, feedback_id: str) -> Optional[UserFeedback]:
        """获取反馈详情"""
        return self.store.get(feedback_id)

    def get_user_feedback(self, user_id: str) -> List[UserFeedback]:
        """获取用户反馈历史"""
        return self.store.get_by_user(user_id)

    def get_stats(self) -> FeedbackStats:
        """获取反馈统计"""
        return self.store.get_stats()

    def get_agent_performance(self) -> Dict[str, Dict[str, Any]]:
        """获取各agent的表现"""
        stats = self.store.get_stats()
        performance = {}

        for agent, count in stats.by_agent.items():
            # 简化：只返回数量
            # 实际应计算成功率等
            performance[agent] = {
                "total_feedback": count,
            }

        return performance


class FeedbackAPI:
    """
    反馈API接口

    提供RESTful接口供各平台调用
    """

    def __init__(self, feedback_service: FeedbackService):
        self.service = feedback_service

    async def handle_feedback(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理反馈请求

        Request body:
        {
            "user_id": "user123",
            "platform": "telegram",
            "message_id": "msg_123",
            "feedback_type": "thumbs_up",  // or rating
            "value": 5,  // optional, for rating
            "agent_name": "llm_agent",
            "router_used": "ai_router"
        }
        """
        try:
            feedback_id = await self.service.submit_feedback(
                user_id=data["user_id"],
                platform=data["platform"],
                message_id=data["message_id"],
                feedback_type=data["feedback_type"],
                value=data.get("value"),
                agent_name=data.get("agent_name", "unknown"),
                router_used=data.get("router_used", "unknown"),
                metadata=data.get("metadata"),
            )

            return {
                "success": True,
                "feedback_id": feedback_id,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def handle_stats(self) -> Dict[str, Any]:
        """获取反馈统计"""
        stats = self.service.get_stats()
        return {
            "success": True,
            "stats": {
                "total_count": stats.total_count,
                "thumbs_up": stats.thumbs_up_count,
                "thumbs_down": stats.thumbs_down_count,
                "avg_rating": round(stats.avg_rating, 2),
                "comments": stats.comment_count,
                "corrections": stats.correction_count,
                "by_agent": stats.by_agent,
                "by_router": stats.by_router,
            },
        }


# 全局反馈服务
_feedback_service: Optional[FeedbackService] = None


def get_feedback_service(experience_logger=None) -> FeedbackService:
    """获取全局反馈服务"""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService(experience_logger)
    return _feedback_service


# FeedbackLoop exports
from src.feedback.loop import FeedbackLoop, FeedbackPattern, ReflectionResult

__all__ = [
    # Core
    "FeedbackService",
    "FeedbackStore",
    "FeedbackAPI",
    "FeedbackType",
    "FeedbackSource",
    "UserFeedback",
    "FeedbackStats",
    "get_feedback_service",
    # Loop
    "FeedbackLoop",
    "FeedbackPattern",
    "ReflectionResult",
]

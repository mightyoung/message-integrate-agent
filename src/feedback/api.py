"""
Feedback API - FastAPI endpoints for feedback collection

提供 RESTful 接口供各平台调用:
- POST /feedback - 提交反馈
- GET /feedback/{feedback_id} - 获取反馈
- GET /feedback/user/{user_id} - 用户反馈历史
- GET /feedback/stats - 反馈统计
- POST /feedback/webhook - Webhook 接收外部反馈
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """反馈请求"""
    user_id: str = Field(..., description="用户ID")
    platform: str = Field(..., description="平台: telegram/feishu/wechat")
    message_id: str = Field(..., description="被评价的消息ID")
    feedback_type: str = Field(..., description="反馈类型: thumbs_up/thumbs_down/rating/comment/correction")
    value: Optional[Any] = Field(None, description="反馈值 (rating: 1-5, comment: str)")
    agent_name: Optional[str] = Field("unknown", description="处理的agent名称")
    router_used: Optional[str] = Field("unknown", description="使用的路由")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外数据")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    feedback_id: Optional[str] = None
    error: Optional[str] = None


class StatsResponse(BaseModel):
    """统计响应"""
    success: bool
    stats: Optional[Dict[str, Any]] = None


def setup_feedback_routes(app, feedback_service):
    """
    Setup feedback routes with feedback service.

    Args:
        app: FastAPI app
        feedback_service: FeedbackService instance
    """

    @router.post("", response_model=FeedbackResponse)
    async def submit_feedback(request: FeedbackRequest):
        """
        提交用户反馈

        支持类型:
        - thumbs_up: 点赞
        - thumbs_down: 踩
        - rating: 评分 (1-5)
        - comment: 评价
        - correction: 纠正
        """
        try:
            feedback_id = await feedback_service.submit_feedback(
                user_id=request.user_id,
                platform=request.platform,
                message_id=request.message_id,
                feedback_type=request.feedback_type,
                value=request.value,
                agent_name=request.agent_name,
                router_used=request.router_used,
                metadata=request.metadata,
            )
            logger.info(f"✅ 反馈已提交: {feedback_id}")
            return FeedbackResponse(success=True, feedback_id=feedback_id)
        except Exception as e:
            logger.error(f"❌ 反馈提交失败: {e}")
            return FeedbackResponse(success=False, error=str(e))

    @router.get("/{feedback_id}", response_model=Dict[str, Any])
    async def get_feedback(feedback_id: str):
        """获取单条反馈详情"""
        feedback = feedback_service.get_feedback(feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        return {
            "id": feedback.id,
            "user_id": feedback.user_id,
            "platform": feedback.platform,
            "message_id": feedback.message_id,
            "feedback_type": feedback.feedback_type.value,
            "value": feedback.value,
            "agent_name": feedback.agent_name,
            "router_used": feedback.router_used,
            "timestamp": feedback.timestamp,
            "metadata": feedback.metadata,
        }

    @router.get("/user/{user_id}", response_model=Dict[str, Any])
    async def get_user_feedback(user_id: str):
        """获取用户的所有反馈"""
        feedbacks = feedback_service.get_user_feedback(user_id)
        return {
            "user_id": user_id,
            "count": len(feedbacks),
            "feedbacks": [
                {
                    "id": f.id,
                    "message_id": f.message_id,
                    "feedback_type": f.feedback_type.value,
                    "value": f.value,
                    "timestamp": f.timestamp,
                }
                for f in feedbacks
            ],
        }

    @router.get("/stats", response_model=StatsResponse)
    async def get_stats():
        """获取反馈统计"""
        try:
            stats = feedback_service.get_stats()
            return StatsResponse(
                success=True,
                stats={
                    "total_count": stats.total_count,
                    "thumbs_up": stats.thumbs_up_count,
                    "thumbs_down": stats.thumbs_down_count,
                    "avg_rating": round(stats.avg_rating, 2),
                    "comments": stats.comment_count,
                    "corrections": stats.correction_count,
                    "by_agent": stats.by_agent,
                    "by_router": stats.by_router,
                },
            )
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return StatsResponse(success=False, stats=None)

    @router.post("/webhook", response_model=FeedbackResponse)
    async def webhook_feedback(request: Dict[str, Any]):
        """
        Webhook 接收外部反馈

        支持多种格式:
        - Telegram inline keyboard callbacks
        - 飞书消息卡片回调
        - 微信模板消息回调
        """
        try:
            # 解析外部反馈格式
            feedback_type = request.get("feedback_type")
            user_id = request.get("user_id", request.get("from", {}).get("id"))
            platform = request.get("platform", "webhook")
            message_id = request.get("message_id", request.get("callback_query_id"))
            value = request.get("value")

            if not feedback_type or not user_id:
                raise ValueError("Missing required fields")

            feedback_id = await feedback_service.submit_feedback(
                user_id=str(user_id),
                platform=platform,
                message_id=str(message_id),
                feedback_type=feedback_type,
                value=value,
                metadata={"source": "webhook", "raw_request": request},
            )

            logger.info(f"📥 Webhook 反馈: {feedback_id}")
            return FeedbackResponse(success=True, feedback_id=feedback_id)

        except Exception as e:
            logger.error(f"❌ Webhook 处理失败: {e}")
            return FeedbackResponse(success=False, error=str(e))

    # Register routes with app
    app.include_router(router)
    logger.info("✅ Feedback routes registered")

    return router

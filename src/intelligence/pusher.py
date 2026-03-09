# coding=utf-8
"""
Intelligence Pusher - 情报推送

基于 TrendRadar NotificationDispatcher 重构:
- 多渠道推送支持
- 消息格式化
- 分批发送
- 推送反馈收集

参考: TrendRadar/notification/senders.py
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict

from loguru import logger


@dataclass
class PushRequest:
    """推送请求"""

    user_id: str
    title: str
    content: str
    channels: List[str]  # feishu, telegram, email, etc.
    metadata: Dict[str, Any]


@dataclass
class PushResult:
    """推送结果"""

    success: bool
    channel: str
    message: str
    error: Optional[str] = None


@dataclass
class PushRecord:
    """推送记录"""
    push_id: str
    user_id: str
    channel: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    delivered: bool = False
    opened: bool = False
    feedback: Optional[str] = None  # "useful", "not_useful"


class PushFeedbackTracker:
    """推送反馈追踪器"""

    def __init__(self):
        self._records: Dict[str, PushRecord] = {}
        self._user_engagement: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"sent": 0, "delivered": 0, "opened": 0, "useful": 0, "not_useful": 0}
        )

    def record_push(
        self,
        push_id: str,
        user_id: str,
        channel: str,
        content: str,
    ) -> PushRecord:
        """记录推送"""
        record = PushRecord(
            push_id=push_id,
            user_id=user_id,
            channel=channel,
            content=content,
        )
        self._records[push_id] = record
        self._user_engagement[user_id]["sent"] += 1
        return record

    def mark_delivered(self, push_id: str):
        """标记已送达"""
        if push_id in self._records:
            self._records[push_id].delivered = True
            user_id = self._records[push_id].user_id
            self._user_engagement[user_id]["delivered"] += 1

    def mark_opened(self, push_id: str):
        """标记已打开"""
        if push_id in self._records:
            self._records[push_id].opened = True
            user_id = self._records[push_id].user_id
            self._user_engagement[user_id]["opened"] += 1

    def record_feedback(self, push_id: str, feedback: str):
        """记录用户反馈"""
        if push_id in self._records:
            self._records[push_id].feedback = feedback
            user_id = self._records[push_id].user_id
            if feedback == "useful":
                self._user_engagement[user_id]["useful"] += 1
            elif feedback == "not_useful":
                self._user_engagement[user_id]["not_useful"] += 1

    def get_engagement_stats(self, user_id: str) -> Dict[str, float]:
        """获取用户参与度统计"""
        stats = self._user_engagement.get(user_id, {})
        sent = stats.get("sent", 0)
        delivered = stats.get("delivered", 0)
        opened = stats.get("opened", 0)

        return {
            "sent": sent,
            "delivered": delivered,
            "opened": opened,
            "delivery_rate": delivered / sent if sent > 0 else 0,
            "open_rate": opened / delivered if delivered > 0 else 0,
            "useful_count": stats.get("useful", 0),
            "not_useful_count": stats.get("not_useful", 0),
        }

    def get_recommended_time(self, user_id: str) -> str:
        """获取推荐推送时间 (简化实现)"""
        # 实际应基于历史数据学习最佳时间
        return "09:00"  # 默认上午9点


class IntelligencePusher:
    """情报推送器

    支持多渠道推送:
    - 飞书 (Feishu)
    - Telegram
    - Email
    - WebSocket
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化推送器

        Args:
            config: 配置信息
        """
        self.config = config or {}
        self._channel_handlers = {
            "feishu": self._push_to_feishu,
            "telegram": self._push_to_telegram,
            "email": self._push_to_email,
            "websocket": self._push_to_websocket,
        }
        # 推送反馈追踪
        self.feedback_tracker = PushFeedbackTracker()

    async def push(
        self,
        request: PushRequest,
    ) -> List[PushResult]:
        """推送情报

        Args:
            request: 推送请求

        Returns:
            List[PushResult]: 推送结果列表
        """
        results = []

        for channel in request.channels:
            handler = self._channel_handlers.get(channel)
            if handler:
                try:
                    result = await handler(request)
                    results.append(result)
                except Exception as e:
                    logger.error(f"推送失败 [{channel}]: {e}")
                    results.append(
                        PushResult(
                            success=False,
                            channel=channel,
                            message="",
                            error=str(e),
                        )
                    )
            else:
                logger.warning(f"未知渠道: {channel}")
                results.append(
                    PushResult(
                        success=False,
                        channel=channel,
                        message="",
                        error=f"未知渠道: {channel}",
                    )
                )

        return results

    async def push_batch(
        self,
        requests: List[PushRequest],
    ) -> Dict[str, List[PushResult]]:
        """批量推送

        Args:
            requests: 推送请求列表

        Returns:
            Dict[str, List[PushResult]]: 用户 ID -> 结果列表
        """
        all_results = {}

        for request in requests:
            results = await self.push(request)
            all_results[request.user_id] = results

        return all_results

    async def _push_to_feishu(self, request: PushRequest) -> PushResult:
        """推送到飞书

        Args:
            request: 推送请求

        Returns:
            PushResult: 推送结果
        """
        # 获取飞书配置
        webhook_url = self.config.get("feishu_webhook_url")

        if not webhook_url:
            # 尝试从环境变量获取
            import os
            webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")

        if not webhook_url:
            return PushResult(
                success=False,
                channel="feishu",
                message="",
                error="未配置飞书 Webhook URL",
            )

        # 构建飞书消息
        message = self._format_feishu_message(request)

        # 发送请求
        import httpx

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    webhook_url,
                    json=message,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return PushResult(
                        success=True,
                        channel="feishu",
                        message="推送成功",
                    )
                else:
                    return PushResult(
                        success=False,
                        channel="feishu",
                        message="",
                        error=f"HTTP {response.status_code}",
                    )

            except Exception as e:
                return PushResult(
                    success=False,
                    channel="feishu",
                    message="",
                    error=str(e),
                )

    async def _push_to_telegram(self, request: PushRequest) -> PushResult:
        """推送到 Telegram

        Args:
            request: 推送请求

        Returns:
            PushResult: 推送结果
        """
        import os

        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = self.config.get("telegram_chat_id")

        if not bot_token or not chat_id:
            return PushResult(
                success=False,
                channel="telegram",
                message="",
                error="未配置 Telegram",
            )

        # 构建消息
        message = f"*{request.title}*\n\n{request.content}"

        import httpx

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return PushResult(
                        success=True,
                        channel="telegram",
                        message="推送成功",
                    )
                else:
                    return PushResult(
                        success=False,
                        channel="telegram",
                        message="",
                        error=f"HTTP {response.status_code}",
                    )

            except Exception as e:
                return PushResult(
                    success=False,
                    channel="telegram",
                    message="",
                    error=str(e),
                )

    async def _push_to_email(self, request: PushRequest) -> PushResult:
        """推送邮件

        Args:
            request: 推送请求

        Returns:
            PushResult: 推送结果
        """
        # 邮件推送需要 SMTP 配置
        return PushResult(
            success=False,
            channel="email",
            message="",
            error="邮件推送待实现",
        )

    async def _push_to_websocket(self, request: PushRequest) -> PushResult:
        """通过 WebSocket 推送

        Args:
            request: 推送请求

        Returns:
            PushResult: 推送结果
        """
        # 需要从 Gateway 获取连接
        return PushResult(
            success=False,
            channel="websocket",
            message="",
            error="WebSocket 推送待实现",
        )

    def _format_feishu_message(self, request: PushRequest) -> Dict:
        """格式化飞书消息

        Args:
            request: 推送请求

        Returns:
            Dict: 飞书消息格式
        """
        # 飞书卡片消息
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": request.title[:50],
                    },
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": request.content[:500],
                    }
                ],
            },
        }

    def register_channel(self, name: str, handler):
        """注册自定义渠道

        Args:
            name: 渠道名称
            handler: 处理函数
        """
        self._channel_handlers[name] = handler
        logger.info(f"注册渠道: {name}")


# ==================== 便捷函数 ====================


def create_intelligence_pusher(
    feishu_webhook: Optional[str] = None,
    telegram_config: Optional[Dict] = None,
) -> IntelligencePusher:
    """创建情报推送器

    Args:
        feishu_webhook: 飞书 Webhook URL
        telegram_config: Telegram 配置

    Returns:
        IntelligencePusher: 推送器实例
    """
    config = {}
    if feishu_webhook:
        config["feishu_webhook_url"] = feishu_webhook
    if telegram_config:
        config.update(telegram_config)

    return IntelligencePusher(config=config)

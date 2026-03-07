"""
Active Push Module - 主动推送系统

实现主动向用户推送消息的能力：
- 用户状态管理
- 消息队列
- 推送策略引擎

设计参考：
- Firebase Cloud Messaging (FCM)
- Pusher
- Celery Task Queue
"""
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class PushPriority(Enum):
    """推送优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class PushStatus(Enum):
    """推送状态"""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PushMessage:
    """推送消息"""
    id: str
    content: str
    platform: str  # feishu, telegram, wechat
    user_id: str
    title: Optional[str] = None
    priority: PushPriority = PushPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: PushStatus = PushStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    sent_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class UserSession:
    """用户会话状态"""
    user_id: str
    platform: str
    last_seen: datetime = field(default_factory=datetime.now)
    online: bool = True
    notification_preferred: bool = True
    quiet_hours_start: Optional[int] = None  # 0-23
    quiet_hours_end: Optional[int] = None    # 0-23


class PushQueue:
    """推送消息队列"""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._handler: Optional[Callable] = None

    def set_handler(self, handler: Callable):
        """设置消息处理器"""
        self._handler = handler

    async def enqueue(self, message: PushMessage):
        """加入队列"""
        await self._queue.put(message)
        logger.debug(f"📬 消息加入推送队列: {message.id}")

    async def start(self):
        """启动队列处理"""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("📬 推送队列已启动")

    async def stop(self):
        """停止队列处理"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("📬 推送队列已停止")

    async def _worker(self):
        """队列工作器"""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )

                if self._handler:
                    try:
                        message.status = PushStatus.SENDING
                        await self._handler(message)
                        message.status = PushStatus.SENT
                        message.sent_at = datetime.now().isoformat()
                    except Exception as e:
                        message.status = PushStatus.FAILED
                        message.error = str(e)
                        logger.error(f"❌ 推送失败: {e}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"队列处理错误: {e}")


class UserStateManager:
    """
    用户状态管理器

    管理用户在线状态、偏好设置
    """

    def __init__(self):
        self._users: Dict[str, UserSession] = {}

    def register_user(
        self,
        user_id: str,
        platform: str,
        notification_preferred: bool = True
    ) -> UserSession:
        """注册用户"""
        key = f"{platform}:{user_id}"

        if key in self._users:
            session = self._users[key]
            session.last_seen = datetime.now()
            session.online = True
        else:
            session = UserSession(
                user_id=user_id,
                platform=platform,
                notification_preferred=notification_preferred
            )
            self._users[key] = session

        logger.info(f"👤 用户注册: {platform}/{user_id}")
        return session

    def get_user(self, platform: str, user_id: str) -> Optional[UserSession]:
        """获取用户状态"""
        key = f"{platform}:{user_id}"
        return self._users.get(key)

    def is_user_online(self, platform: str, user_id: str) -> bool:
        """检查用户是否在线"""
        session = self.get_user(platform, user_id)
        return session.online if session else False

    def is_quiet_hours(self, session: UserSession) -> bool:
        """检查是否在免打扰时段"""
        if session.quiet_hours_start is None or session.quiet_hours_end is None:
            return False

        now = datetime.now()
        current_hour = now.hour

        start = session.quiet_hours_start
        end = session.quiet_hours_end

        if start <= end:
            return start <= current_hour < end
        else:
            # 跨午夜
            return current_hour >= start or current_hour < end

    def set_quiet_hours(
        self,
        platform: str,
        user_id: str,
        start: int,
        end: int
    ):
        """设置免打扰时段"""
        session = self.get_user(platform, user_id)
        if session:
            session.quiet_hours_start = start
            session.quiet_hours_end = end
            logger.info(f"🔕 免打扰时段设置: {start}:00 - {end}:00")

    def user_offline(self, platform: str, user_id: str):
        """标记用户离线"""
        key = f"{platform}:{user_id}"
        if key in self._users:
            self._users[key].online = False

    def get_all_online_users(self, platform: Optional[str] = None) -> List[UserSession]:
        """获取所有在线用户"""
        users = [u for u in self._users.values() if u.online]
        if platform:
            users = [u for u in users if u.platform == platform]
        return users


class PushStrategy:
    """
    推送策略引擎

    决定何时、如何推送消息
    """

    def __init__(self, user_manager: UserStateManager):
        self.user_manager = user_manager
        self.max_retries = 3
        self.retry_delay = 5  # seconds

    def should_push(self, platform: str, user_id: str) -> bool:
        """
        判断是否应该推送

        考虑因素：
        - 用户在线状态
        - 免打扰时段
        - 用户偏好
        """
        session = self.user_manager.get_user(platform, user_id)

        if not session:
            # 未注册用户，默认推送
            return True

        if not session.online:
            logger.debug(f"👤 用户离线，不推送: {platform}/{user_id}")
            return False

        if not session.notification_preferred:
            logger.debug(f"👤 用户关闭通知，不推送: {platform}/{user_id}")
            return False

        if self.user_manager.is_quiet_hours(session):
            logger.debug(f"🔕 免打扰时段，不推送: {platform}/{user_id}")
            return False

        return True

    def get_priority(self, message: PushMessage) -> int:
        """获取推送优先级"""
        priority_map = {
            PushPriority.LOW: 1,
            PushPriority.NORMAL: 2,
            PushPriority.HIGH: 3,
            PushPriority.URGENT: 4,
        }
        return priority_map.get(message.priority, 2)


class PushService:
    """
    推送服务

    统一推送接口
    """

    def __init__(
        self,
        adapter_registry=None,
    ):
        self.adapter_registry = adapter_registry
        self.queue = PushQueue()
        self.user_manager = UserStateManager()
        self.strategy = PushStrategy(self.user_manager)

        # 消息历史
        self._message_history: Dict[str, PushMessage] = {}

    async def initialize(self):
        """初始化"""
        await self.queue.start()

        # 设置消息处理器
        self.queue.set_handler(self._send_message)

    async def shutdown(self):
        """关闭"""
        await self.queue.stop()

    async def push(
        self,
        content: str,
        platform: str,
        user_id: str,
        title: Optional[str] = None,
        priority: PushPriority = PushPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        推送消息

        Args:
            content: 消息内容
            platform: 平台 (feishu/telegram/wechat)
            user_id: 用户ID
            title: 标题
            priority: 优先级
            metadata: 额外数据

        Returns:
            消息ID
        """
        # 检查推送策略
        if not self.strategy.should_push(platform, user_id):
            logger.info(f"⏸️ 跳过推送 (策略): {platform}/{user_id}")
            return ""

        # 创建消息
        message = PushMessage(
            id=f"push_{datetime.now().timestamp()}",
            content=content,
            platform=platform,
            user_id=user_id,
            title=title,
            priority=priority,
            metadata=metadata or {}
        )

        # 保存到历史
        self._message_history[message.id] = message

        # 加入队列
        await self.queue.enqueue(message)

        return message.id

    async def push_to_multiple(
        self,
        content: str,
        platform: str,
        user_ids: List[str],
        title: Optional[str] = None,
        priority: PushPriority = PushPriority.NORMAL,
    ) -> List[str]:
        """批量推送"""
        tasks = []
        for user_id in user_ids:
            task = asyncio.create_task(
                self.push(content, platform, user_id, title, priority)
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if r]

    async def push_to_all_online(
        self,
        content: str,
        platform: Optional[str] = None,
        title: Optional[str] = None,
    ) -> int:
        """推送给所有在线用户"""
        online_users = self.user_manager.get_all_online_users(platform)

        if not online_users:
            logger.info("👥 没有在线用户")
            return 0

        tasks = []
        for user in online_users:
            task = asyncio.create_task(
                self.push(content, user.platform, user.user_id, title)
            )
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)
        return len(online_users)

    async def _send_message(self, message: PushMessage):
        """发送消息到平台"""
        if not self.adapter_registry:
            logger.warning("⚠️ 未配置适配器注册表")
            return

        adapter = self.adapter_registry.get_adapter(message.platform)
        if not adapter:
            raise ValueError(f"适配器未找到: {message.platform}")

        if not adapter.is_enabled():
            raise ValueError(f"适配器未启用: {message.platform}")

        await adapter.send_message(
            chat_id=message.user_id,
            content=message.content,
        )

        logger.info(f"✅ 推送成功: {message.platform}/{message.user_id}")

    def get_message_status(self, message_id: str) -> Optional[PushStatus]:
        """获取消息状态"""
        message = self._message_history.get(message_id)
        return message.status if message else None

    def register_user(
        self,
        user_id: str,
        platform: str,
        notification_preferred: bool = True
    ):
        """注册用户"""
        return self.user_manager.register_user(user_id, platform, notification_preferred)

    def set_quiet_hours(
        self,
        platform: str,
        user_id: str,
        start: int,
        end: int
    ):
        """设置免打扰时段"""
        self.user_manager.set_quiet_hours(platform, user_id, start, end)


# 全局推送服务
_push_service: Optional[PushService] = None


def get_push_service() -> PushService:
    """获取全局推送服务"""
    global _push_service
    if _push_service is None:
        _push_service = PushService()
    return _push_service

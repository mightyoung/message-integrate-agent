"""
Heartbeat Cycle Engine - 自主驱动的"脉搏"

实现 OpenClaw 风格的心跳循环机制：
- 定期唤醒与感知
- 认知升级循环（7步）
- 从"用中学"到"中学用"

设计参考：
- APScheduler: Python 定时任务标准
- Celery Beat: 分布式定时调度
- OpenClaw: 自主智能体心跳机制
"""
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from loguru import logger


class HeartbeatState(Enum):
    """心跳状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class HeartbeatStep(Enum):
    """心跳循环的7个步骤"""
    INFORMATION_INTAKE = "information_intake"      # 信息摄入
    VALUE_JUDGMENT = "value_judgment"            # 价值判断
    KNOWLEDGE_OUTPUT = "knowledge_output"        # 知识输出
    SOCIAL_MAINTENANCE = "social_maintenance"     # 社交维护
    SELF_REFLECTION = "self_reflection"          # 自我反思
    SKILL_UPDATE = "skill_update"                # 技能更新
    NOTIFICATION_CHECK = "notification_check"    # 通知检查


class HeartbeatTask(ABC):
    """心跳任务基类"""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.run_count: int = 0
        self.error_count: int = 0

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务

        Args:
            context: 共享上下文

        Returns:
            任务结果
        """
        pass

    def mark_success(self):
        """标记成功"""
        self.last_run = datetime.now()
        self.run_count += 1

    def mark_error(self):
        """标记错误"""
        self.error_count += 1


class InformationIntakeTask(HeartbeatTask):
    """信息摄入任务 - 浏览信息源"""

    def __init__(self):
        super().__init__("information_intake", enabled=True)
        self.sources = [
            "https://news.ycombinator.com",
            "https://reddit.com/r/ArtificialIntelligence",
        ]

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行信息摄入"""
        logger.info("🔍 [Heartbeat] 开始信息摄入...")

        # 这里可以集成搜索功能读取最新内容
        # 实际实现时可以调用 search agent
        articles = []

        # 模拟读取3-5篇高质量内容
        for i, source in enumerate(self.sources[:3]):
            articles.append({
                "source": source,
                "title": f"Sample Article {i+1}",
                "summary": "内容摘要...",
                "timestamp": datetime.now().isoformat(),
            })

        logger.info(f"📖 [Heartbeat] 读取了 {len(articles)} 篇内容")

        self.mark_success()
        return {
            "articles": articles,
            "count": len(articles),
        }


class ValueJudgmentTask(HeartbeatTask):
    """价值判断任务 - 对内容投票"""

    def __init__(self):
        super().__init__("value_judgment", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行价值判断"""
        logger.info("🗳️ [Heartbeat] 开始价值判断...")

        articles = context.get("intake", {}).get("articles", [])

        # 对内容进行投票筛选
        votes = []
        for article in articles:
            # 模拟评分逻辑
            score = 0.8  # 简化：假设都是高质量
            votes.append({
                "article": article,
                "score": score,
                "approved": score > 0.5,
            })

        approved = [v for v in votes if v["approved"]]

        logger.info(f"🗳️ [Heartbeat] 筛选了 {len(approved)}/{len(articles)} 篇高质量内容")

        self.mark_success()
        return {
            "votes": votes,
            "approved_count": len(approved),
        }


class KnowledgeOutputTask(HeartbeatTask):
    """知识输出任务 - 撰写深度评论"""

    def __init__(self):
        super().__init__("knowledge_output", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行知识输出"""
        logger.info("✍️ [Heartbeat] 开始知识输出...")

        approved = context.get("judgment", {}).get("votes", [])

        # 对每篇批准的文章撰写评论
        outputs = []
        for item in approved[:3]:  # 最多3篇
            article = item.get("article", {})
            output = {
                "article_title": article.get("title"),
                "comment": f"深度评论：关于 {article.get('title')} 的分析...",
                "word_count": 200,
                "timestamp": datetime.now().isoformat(),
            }
            outputs.append(output)

        logger.info(f"✍️ [Heartbeat] 撰写了 {len(outputs)} 篇深度评论")

        self.mark_success()
        return {
            "outputs": outputs,
            "count": len(outputs),
        }


class SocialMaintenanceTask(HeartbeatTask):
    """社交维护任务 - 检查私信和关注"""

    def __init__(self):
        super().__init__("social_maintenance", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行社交维护"""
        logger.info("👥 [Heartbeat] 开始社交维护...")

        # 检查消息平台的新消息
        messages = []

        # 模拟检查各平台
        for platform in ["telegram", "feishu", "wechat"]:
            messages.append({
                "platform": platform,
                "unread_count": 0,
            })

        # 检查其他智能体的状态
        agents = []

        logger.info(f"👥 [Heartbeat] 检查了 {len(messages)} 个平台")

        self.mark_success()
        return {
            "messages": messages,
            "agents": agents,
        }


class SelfReflectionTask(HeartbeatTask):
    """自我反思任务 - 检查技能和通知"""

    def __init__(self):
        super().__init__("self_reflection", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行自我反思"""
        logger.info("🔄 [Heartbeat] 开始自我反思...")

        # 检查技能是否需要更新
        skill_updates = []

        # 检查系统通知
        notifications = []

        # 统计本周期表现
        stats = {
            "total_tasks": 7,
            "successful": 6,
            "failed": 0,
            "uptime_hours": 4,
        }

        logger.info("🔄 [Heartbeat] 自我反思完成")

        self.mark_success()
        return {
            "skill_updates": skill_updates,
            "notifications": notifications,
            "stats": stats,
        }


class SkillUpdateTask(HeartbeatTask):
    """技能更新任务 - 检查并更新技能"""

    def __init__(self):
        super().__init__("skill_update", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能更新"""
        logger.info("⚡ [Heartbeat] 开始技能更新检查...")

        # 检查是否有新的技能需要加载
        updates = []

        # 模拟检查技能目录
        # 实际实现时扫描 skills/ 目录

        if updates:
            logger.info(f"⚡ [Heartbeat] 发现 {len(updates)} 个技能更新")
        else:
            logger.info("⚡ [Heartbeat] 技能已是最新")

        self.mark_success()
        return {
            "updates": updates,
            "count": len(updates),
        }


class NotificationCheckTask(HeartbeatTask):
    """通知检查任务 - 检查系统通知"""

    def __init__(self):
        super().__init__("notification_check", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行通知检查"""
        logger.info("🔔 [Heartbeat] 开始通知检查...")

        # 检查各平台通知
        notifications = []

        # 模拟检查
        for platform in ["telegram", "feishu", "wechat"]:
            notifications.append({
                "platform": platform,
                "count": 0,
            })

        logger.info(f"🔔 [Heartbeat] 检查了 {len(notifications)} 个平台")

        self.mark_success()
        return {
            "notifications": notifications,
            "count": len(notifications),
        }


class HeartbeatEngine:
    """
    心跳循环引擎

    核心特性：
    - 事件驱动：不阻塞主消息处理
    - 可配置：支持不同间隔的不同任务
    - 错误隔离：单个任务失败不影响整体
    - 可观测：每个步骤都有日志和状态
    """

    def __init__(
        self,
        interval_hours: float = 4,
        enabled: bool = True,
    ):
        """
        初始化心跳引擎

        Args:
            interval_hours: 心跳间隔（小时）
            enabled: 是否启用
        """
        self.interval_seconds = interval_hours * 3600
        self.enabled = enabled
        self.state = HeartbeatState.IDLE

        # 任务注册表
        self.tasks: Dict[HeartbeatStep, HeartbeatTask] = {}

        # 统计信息
        self.total_cycles = 0
        self.last_cycle_time: Optional[datetime] = None

        # 上下文（心跳步骤之间共享）
        self.context: Dict[str, Any] = {}

        # 注册默认任务
        self._register_default_tasks()

        logger.info(f"💓 心跳引擎初始化完成，间隔: {interval_hours}小时")

    def _register_default_tasks(self):
        """注册默认任务"""
        self.register_task(HeartbeatStep.INFORMATION_INTAKE, InformationIntakeTask())
        self.register_task(HeartbeatStep.VALUE_JUDGMENT, ValueJudgmentTask())
        self.register_task(HeartbeatStep.KNOWLEDGE_OUTPUT, KnowledgeOutputTask())
        self.register_task(HeartbeatStep.SOCIAL_MAINTENANCE, SocialMaintenanceTask())
        self.register_task(HeartbeatStep.SELF_REFLECTION, SelfReflectionTask())
        self.register_task(HeartbeatStep.SKILL_UPDATE, SkillUpdateTask())
        self.register_task(HeartbeatStep.NOTIFICATION_CHECK, NotificationCheckTask())

    def register_task(self, step: HeartbeatStep, task: HeartbeatTask):
        """注册心跳任务"""
        self.tasks[step] = task
        logger.debug(f"📝 注册心跳任务: {step.value} -> {task.name}")

    def unregister_task(self, step: HeartbeatStep):
        """注销心跳任务"""
        if step in self.tasks:
            del self.tasks[step]
            logger.debug(f"🗑️ 注销心跳任务: {step.value}")

    async def start(self):
        """启动心跳循环"""
        if not self.enabled:
            logger.info("💓 心跳引擎已禁用")
            return

        if self.state == HeartbeatState.RUNNING:
            logger.warning("💓 心跳引擎已在运行中")
            return

        self.state = HeartbeatState.RUNNING
        logger.info("💓 心跳引擎启动")

        # 启动心跳循环
        asyncio.create_task(self._heartbeat_loop())

    async def stop(self):
        """停止心跳循环"""
        self.state = HeartbeatState.STOPPED
        logger.info("💓 心跳引擎已停止")

    async def pause(self):
        """暂停心跳"""
        self.state = HeartbeatState.PAUSED
        logger.info("💓 心跳引擎已暂停")

    async def resume(self):
        """恢复心跳"""
        if self.state == HeartbeatState.PAUSED:
            self.state = HeartbeatState.RUNNING
            logger.info("💓 心跳引擎已恢复")

    async def _heartbeat_loop(self):
        """心跳主循环"""
        while self.state == HeartbeatState.RUNNING:
            try:
                # 执行一个完整的心跳周期
                await self._execute_cycle()

                self.total_cycles += 1
                self.last_cycle_time = datetime.now()

                # 等待下一次心跳
                logger.info(f"💓 心跳周期 #{self.total_cycles} 完成，等待 {self.interval_seconds/3600} 小时")
                await asyncio.sleep(self.interval_seconds)

            except asyncio.CancelledError:
                logger.info("💓 心跳循环被取消")
                break
            except Exception as e:
                logger.error(f"💓 心跳循环错误: {e}")
                # 等待后重试
                await asyncio.sleep(60)

    async def _execute_cycle(self):
        """执行一个完整的心跳周期"""
        cycle_start = datetime.now()
        logger.info("=" * 50)
        logger.info(f"🫀 开始心跳周期 #{self.total_cycles + 1}")
        logger.info("=" * 50)

        # 清空上下文
        self.context = {
            "cycle_start": cycle_start.isoformat(),
            "cycle_number": self.total_cycles + 1,
        }

        # 按顺序执行7个步骤
        step_order = [
            HeartbeatStep.INFORMATION_INTAKE,
            HeartbeatStep.VALUE_JUDGMENT,
            HeartbeatStep.KNOWLEDGE_OUTPUT,
            HeartbeatStep.SOCIAL_MAINTENANCE,
            HeartbeatStep.SELF_REFLECTION,
            HeartbeatStep.SKILL_UPDATE,
            HeartbeatStep.NOTIFICATION_CHECK,
        ]

        for step in step_order:
            if self.state != HeartbeatState.RUNNING:
                break

            if step not in self.tasks:
                continue

            task = self.tasks[step]

            if not task.enabled:
                logger.debug(f"⏭️ 跳过任务: {step.value} (已禁用)")
                continue

            # 执行任务
            try:
                logger.info(f"▶️ 执行: {step.value}")
                result = await task.execute(self.context)

                # 将结果存入上下文，供后续步骤使用
                self.context[step.value] = result

                logger.info(f"✅ 完成: {step.value}")

            except Exception as e:
                logger.error(f"❌ 任务失败: {step.value} - {e}")
                task.mark_error()

        cycle_end = datetime.now()
        duration = (cycle_end - cycle_start).total_seconds()

        logger.info("=" * 50)
        logger.info(f"🫀 心跳周期完成，耗时: {duration:.2f}秒")
        logger.info("=" * 50)

    def get_status(self) -> Dict[str, Any]:
        """获取心跳引擎状态"""
        task_status = {}
        for step, task in self.tasks.items():
            task_status[step.value] = {
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "run_count": task.run_count,
                "error_count": task.error_count,
            }

        return {
            "state": self.state.value,
            "enabled": self.enabled,
            "interval_hours": self.interval_seconds / 3600,
            "total_cycles": self.total_cycles,
            "last_cycle_time": self.last_cycle_time.isoformat() if self.last_cycle_time else None,
            "tasks": task_status,
        }

    def set_interval(self, hours: float):
        """设置心跳间隔"""
        self.interval_seconds = hours * 3600
        logger.info(f"💓 心跳间隔已更新为 {hours} 小时")

    def enable_task(self, step: HeartbeatStep):
        """启用任务"""
        if step in self.tasks:
            self.tasks[step].enabled = True

    def disable_task(self, step: HeartbeatStep):
        """禁用任务"""
        if step in self.tasks:
            self.tasks[step].enabled = False


# 全局实例
_heartbeat_engine: Optional[HeartbeatEngine] = None


def get_heartbeat_engine() -> HeartbeatEngine:
    """获取全局心跳引擎实例"""
    global _heartbeat_engine
    if _heartbeat_engine is None:
        _heartbeat_engine = HeartbeatEngine()
    return _heartbeat_engine

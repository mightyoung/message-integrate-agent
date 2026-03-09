"""
Heartbeat Integration - 心跳系统集成

集成所有 OpenClaw 风格的心跳组件：
- HeartbeatResponse
- HeartbeatChecklist
- CommandQueue
- Scheduler
- IdempotentExecutor
- MemoryCompactionTrigger

这个模块提供一个统一的入口来使用所有心跳组件。
"""
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

# 导入所有组件
from src.heartbeat.response import (
    HeartbeatResponse,
    HeartbeatStatus,
    Channel,
    create_idempotency_key,
    parse_channel,
)
from src.heartbeat.checklist import (
    HeartbeatChecklist,
    ChecklistItem,
    EvaluationResult,
    DEFAULT_CHECKLIST_PATH,
)
from src.heartbeat.queue import (
    CommandQueue,
    Command,
    CommandResult,
    LaneType,
    create_command,
)
from src.heartbeat.scheduler import (
    Scheduler,
    Job,
    ScheduleType,
    parse_cron_expression,
    format_interval,
)
from src.heartbeat.idempotent import (
    IdempotentExecutor,
    IdempotentResult,
    create_idempotent_key,
    create_user_action_key,
    create_session_key,
    get_idempotent_executor,
)
from src.heartbeat.memory import (
    MemoryCompactionTrigger,
    MemorySnapshot,
    create_memory_note,
    estimate_tokens,
)


class HeartbeatIntegration:
    """心跳系统集成

    提供统一的接口来使用所有心跳组件：
    1. CommandQueue: 命令队列管理
    2. Scheduler: 调度管理
    3. IdempotentExecutor: 幂等执行
    4. MemoryCompactionTrigger: 内存压缩
    5. HeartbeatChecklist: 检查清单
    """

    def __init__(
        self,
        interval_hours: float = 4,
        enable_queue: bool = True,
        enable_scheduler: bool = True,
        enable_memory_compaction: bool = True,
        enable_checklist: bool = True,
        checklist_path: Optional[Path] = None,
        memory_dir: Optional[Path] = None,
    ):
        """初始化集成

        Args:
            interval_hours: 心跳间隔（小时）
            enable_queue: 启用命令队列
            enable_scheduler: 启用调度器
            enable_memory_compaction: 启用内存压缩
            enable_checklist: 启用检查清单
            checklist_path: 检查清单路径
            memory_dir: 内存目录
        """
        self.interval_hours = interval_hours

        # 初始化组件
        self.queue = CommandQueue() if enable_queue else None
        self.scheduler = Scheduler() if enable_scheduler else None
        self.idempotent_executor = IdempotentExecutor() if enable_queue else None
        self.memory_compaction = MemoryCompactionTrigger(
            memory_dir=memory_dir
        ) if enable_memory_compaction else None
        self.checklist = HeartbeatChecklist(
            checklist_path=checklist_path
        ) if enable_checklist else None

        # 状态
        self._running = False

        logger.info(f"HeartbeatIntegration initialized (interval={interval_hours}h)")

    # ==================== 队列操作 ====================

    async def enqueue_command(
        self,
        name: str,
        args: Dict[str, Any],
        lane: LaneType = LaneType.GLOBAL,
        session_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """入队命令

        Args:
            name: 命令名称
            args: 命令参数
            lane: Lane 类型
            session_id: 会话 ID
            idempotency_key: 幂等性 key

        Returns:
            str: 命令 ID
        """
        if not self.queue:
            raise RuntimeError("Command queue is not enabled")

        command = create_command(
            name=name,
            args=args,
            lane=lane,
            session_id=session_id,
            idempotency_key=idempotency_key,
        )

        return await self.queue.enqueue(command)

    def register_command_handler(self, name: str, handler):
        """注册命令处理器

        Args:
            name: 命令名称
            handler: 处理器函数
        """
        if not self.queue:
            raise RuntimeError("Command queue is not enabled")

        self.queue.register_handler(name, handler)

    # ==================== 调度操作 ====================

    def schedule_interval(
        self,
        job_id: str,
        name: str,
        handler,
        seconds: Optional[int] = None,
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
    ) -> str:
        """添加间隔调度

        Args:
            job_id: 任务 ID
            name: 任务名称
            handler: 处理器
            seconds: 秒
            minutes: 分钟
            hours: 小时

        Returns:
            str: 任务 ID
        """
        if not self.scheduler:
            raise RuntimeError("Scheduler is not enabled")

        return self.scheduler.schedule_interval(
            job_id=job_id,
            name=name,
            handler=handler,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
        )

    def schedule_cron(
        self,
        job_id: str,
        name: str,
        handler,
        cron_expression: str,
    ) -> str:
        """添加 Cron 调度

        Args:
            job_id: 任务 ID
            name: 任务名称
            handler: 处理器
            cron_expression: Cron 表达式

        Returns:
            str: 任务 ID
        """
        if not self.scheduler:
            raise RuntimeError("Scheduler is not enabled")

        return self.scheduler.schedule_cron(
            job_id=job_id,
            name=name,
            handler=handler,
            cron_expression=cron_expression,
        )

    async def start_scheduler(self):
        """启动调度器"""
        if not self.scheduler:
            return

        await self.scheduler.start()
        self.scheduler.start_scheduler_loop()
        logger.info("Scheduler started")

    # ==================== 幂等执行 ====================

    async def execute_idempotent(
        self,
        key: str,
        handler,
        *args,
        ttl: Optional[int] = None,
        **kwargs
    ) -> IdempotentResult:
        """幂等执行

        Args:
            key: 幂等性 key
            handler: 处理器
            args: 位置参数
            ttl: 过期时间
            kwargs: 关键字参数

        Returns:
            IdempotentResult: 执行结果
        """
        if not self.idempotent_executor:
            raise RuntimeError("Idempotent executor is not enabled")

        return await self.idempotent_executor.execute(key, handler, *args, ttl=ttl, **kwargs)

    # ==================== 内存压缩 ====================

    def should_compact_memory(self, current_tokens: int) -> bool:
        """判断是否应该压缩内存

        Args:
            current_tokens: 当前 token 数

        Returns:
            bool: 是否应该压缩
        """
        if not self.memory_compaction:
            return False

        return self.memory_compaction.should_trigger(current_tokens)

    async def compact_memory(self, context: Dict[str, Any]) -> MemorySnapshot:
        """压缩内存

        Args:
            context: 上下文

        Returns:
            MemorySnapshot: 快照
        """
        if not self.memory_compaction:
            raise RuntimeError("Memory compaction is not enabled")

        return await self.memory_compaction.trigger(context)

    # ==================== 检查清单 ====================

    async def evaluate_checklist(self, context: Dict[str, Any]) -> HeartbeatResponse:
        """评估检查清单

        Args:
            context: 上下文

        Returns:
            HeartbeatResponse: 响应
        """
        if not self.checklist:
            raise RuntimeError("Checklist is not enabled")

        return await self.checklist.evaluate(context)

    async def load_checklist(self):
        """加载检查清单"""
        if self.checklist:
            await self.checklist.load()

    # ==================== 生命周期 ====================

    async def start(self):
        """启动所有组件"""
        self._running = True

        if self.scheduler:
            await self.start_scheduler()

        logger.info("HeartbeatIntegration started")

    async def stop(self):
        """停止所有组件"""
        self._running = False

        if self.scheduler:
            await self.scheduler.stop()

        if self.queue:
            await self.queue.shutdown()

        logger.info("HeartbeatIntegration stopped")

    def get_status(self) -> Dict[str, Any]:
        """获取状态

        Returns:
            Dict: 状态信息
        """
        status = {
            "running": self._running,
            "interval_hours": self.interval_hours,
        }

        if self.queue:
            status["queue"] = self.queue.get_status()

        if self.scheduler:
            status["scheduler"] = {
                "jobs": len(self.scheduler.list_jobs()),
                "next_runs": self.scheduler.get_next_run_times(3),
            }

        if self.idempotent_executor:
            status["idempotent"] = self.idempotent_executor.get_stats()

        if self.memory_compaction:
            status["memory_compaction"] = self.memory_compaction.get_stats()

        return status


# ==================== 全局实例 ====================

_default_integration: Optional[HeartbeatIntegration] = None


def get_heartbeat_integration() -> HeartbeatIntegration:
    """获取默认集成实例

    Returns:
        HeartbeatIntegration: 集成实例
    """
    global _default_integration
    if _default_integration is None:
        _default_integration = HeartbeatIntegration()
    return _default_integration


def create_heartbeat_integration(**kwargs) -> HeartbeatIntegration:
    """创建新的集成实例

    Args:
        **kwargs: 初始化参数

    Returns:
        HeartbeatIntegration: 集成实例
    """
    return HeartbeatIntegration(**kwargs)

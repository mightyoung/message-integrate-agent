"""
Scheduler - Cron 调度器

实现灵活的调度系统：
- Cron 表达式调度
- 一次性调度 (at)
- 间隔调度 (every)

参考:
- APScheduler: Python 定时任务标准
- Celery Beat: 分布式调度
- OpenClaw: Cron jobs support
"""
import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional
from loguru import logger

try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False


@dataclass
class Job:
    """调度任务"""
    id: str
    name: str
    handler: Callable[..., Awaitable[Any]]
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    schedule_type: str = "interval"  # interval/cron/once
    interval_seconds: Optional[int] = None
    cron_expression: Optional[str] = None
    run_at: Optional[datetime] = None
    enabled: bool = True
    max_runs: Optional[int] = None  # 最大运行次数，None 表示无限
    run_count: int = 0
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScheduleType(str, enum=str):
    """调度类型"""
    INTERVAL = "interval"  # 间隔调度
    CRON = "cron"         # Cron 表达式
    ONCE = "once"         # 一次性调度


class Scheduler:
    """调度器

    支持多种调度方式：
    - 间隔调度: every N seconds/minutes/hours
    - Cron 调度: 标准 cron 表达式
    - 一次性调度: 在指定时间执行一次
    """

    def __init__(self):
        """初始化调度器"""
        self._jobs: Dict[str, Job] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._lock = asyncio.Lock()

        logger.info("Scheduler initialized")

    async def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        logger.info("Scheduler started")

    async def stop(self):
        """停止调度器"""
        self._running = False

        # 取消所有任务
        for task in self._tasks:
            task.cancel()

        # 等待完成
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
        logger.info("Scheduler stopped")

    # ==================== 调度方法 ====================

    def schedule_interval(
        self,
        job_id: str,
        name: str,
        handler: Callable[..., Awaitable[Any]],
        seconds: Optional[int] = None,
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        max_runs: Optional[int] = None
    ) -> str:
        """添加间隔调度任务

        Args:
            job_id: 任务 ID
            name: 任务名称
            handler: 处理器
            seconds: 秒
            minutes: 分钟
            hours: 小时
            args: 位置参数
            kwargs: 关键字参数
            max_runs: 最大运行次数

        Returns:
            str: 任务 ID
        """
        # 计算总秒数
        total_seconds = 0
        if seconds:
            total_seconds += seconds
        if minutes:
            total_seconds += minutes * 60
        if hours:
            total_seconds += hours * 3600

        if total_seconds <= 0:
            raise ValueError("Interval must be > 0")

        job = Job(
            id=job_id,
            name=name,
            handler=handler,
            args=args,
            kwargs=kwargs or {},
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=total_seconds,
            max_runs=max_runs,
            next_run=datetime.now()
        )

        self._jobs[job_id] = job
        logger.info(f"Scheduled interval job: {job_id} every {total_seconds}s")

        return job_id

    def schedule_cron(
        self,
        job_id: str,
        name: str,
        handler: Callable[..., Awaitable[Any]],
        cron_expression: str,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        max_runs: Optional[int] = None
    ) -> str:
        """添加 Cron 调度任务

        Args:
            job_id: 任务 ID
            name: 任务名称
            handler: 处理器
            cron_expression: Cron 表达式
            args: 位置参数
            kwargs: 关键字参数
            max_runs: 最大运行次数

        Returns:
            str: 任务 ID
        """
        # 验证 Cron 表达式
        if not self._validate_cron(cron_expression):
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        job = Job(
            id=job_id,
            name=name,
            handler=handler,
            args=args,
            kwargs=kwargs or {},
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression,
            max_runs=max_runs,
            next_run=self._get_next_cron_time(cron_expression)
        )

        self._jobs[job_id] = job
        logger.info(f"Scheduled cron job: {job_id} with expression: {cron_expression}")

        return job_id

    def schedule_at(
        self,
        job_id: str,
        name: str,
        handler: Callable[..., Awaitable[Any]],
        run_at: datetime,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加一次性调度任务

        Args:
            job_id: 任务 ID
            name: 任务名称
            handler: 处理器
            run_at: 运行时间
            args: 位置参数
            kwargs: 关键字参数

        Returns:
            str: 任务 ID
        """
        if run_at <= datetime.now():
            raise ValueError("run_at must be in the future")

        job = Job(
            id=job_id,
            name=name,
            handler=handler,
            args=args,
            kwargs=kwargs or {},
            schedule_type=ScheduleType.ONCE,
            run_at=run_at,
            max_runs=1,
            next_run=run_at
        )

        self._jobs[job_id] = job
        logger.info(f"Scheduled one-time job: {job_id} at {run_at}")

        return job_id

    def unschedule(self, job_id: str) -> bool:
        """取消调度任务

        Args:
            job_id: 任务 ID

        Returns:
            bool: 是否成功取消
        """
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.enabled = False
            logger.info(f"Unscheduled job: {job_id}")
            return True
        return False

    def get_job(self, job_id: str) -> Optional[Job]:
        """获取任务

        Args:
            job_id: 任务 ID

        Returns:
            Optional[Job]: 任务
        """
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[Job]:
        """列出所有任务

        Returns:
            List[Job]: 任务列表
        """
        return list(self._jobs.values())

    def get_next_run_times(self, count: int = 5) -> List[Dict[str, Any]]:
        """获取下次运行时间

        Args:
            count: 数量

        Returns:
            List[Dict]: 下次运行时间列表
        """
        result = []
        for job in self._jobs.values():
            if job.enabled and job.next_run:
                result.append({
                    "job_id": job.id,
                    "name": job.name,
                    "next_run": job.next_run.isoformat(),
                    "schedule_type": job.schedule_type
                })

        # 按时间排序
        result.sort(key=lambda x: x["next_run"])
        return result[:count]

    # ==================== 内部方法 ====================

    def _validate_cron(self, expression: str) -> bool:
        """验证 Cron 表达式

        Args:
            expression: Cron 表达式

        Returns:
            bool: 是否有效
        """
        if not expression:
            return False

        # 简单验证：5 个字段
        parts = expression.split()
        if len(parts) != 5:
            return False

        if CRONITER_AVAILABLE:
            try:
                croniter(expression)
                return True
            except Exception:
                return False

        # 备用简单验证
        field_pattern = r"^[\d,\-\*/]+$"
        return all(re.match(field_pattern, p) for p in parts)

    def _get_next_cron_time(self, expression: str, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """获取下次 Cron 执行时间

        Args:
            expression: Cron 表达式
            from_time: 起始时间

        Returns:
            Optional[datetime]: 下次执行时间
        """
        from_time = from_time or datetime.now()

        if CRONITER_AVAILABLE:
            try:
                cron = croniter(expression, from_time)
                return cron.get_next(datetime)
            except Exception as e:
                logger.error(f"Failed to get next cron time: {e}")

        return None

    def _calculate_next_run(self, job: Job) -> Optional[datetime]:
        """计算下次运行时间

        Args:
            job: 任务

        Returns:
            Optional[datetime]: 下次运行时间
        """
        if job.schedule_type == ScheduleType.INTERVAL:
            if job.interval_seconds and job.last_run:
                return job.last_run + timedelta(seconds=job.interval_seconds)
            elif job.interval_seconds:
                return datetime.now() + timedelta(seconds=job.interval_seconds)

        elif job.schedule_type == ScheduleType.CRON:
            if job.cron_expression:
                return self._get_next_cron_time(job.cron_expression, job.last_run)

        elif job.schedule_type == ScheduleType.ONCE:
            if job.run_at and job.run_count == 0:
                return job.run_at

        return None

    async def _run_job(self, job: Job):
        """运行任务

        Args:
            job: 任务
        """
        if not job.enabled:
            return

        # 检查最大运行次数
        if job.max_runs and job.run_count >= job.max_runs:
            logger.info(f"Job {job.id} reached max runs, disabling")
            job.enabled = False
            return

        now = datetime.now()

        # 检查是否到时间
        if job.next_run and now >= job.next_run:
            try:
                logger.info(f"Running job: {job.id}")

                # 执行
                if asyncio.iscoroutinefunction(job.handler):
                    await job.handler(*job.args, **job.kwargs)
                else:
                    job.handler(*job.args, **job.kwargs)

                # 更新状态
                job.run_count += 1
                job.last_run = now

                # 计算下次运行时间
                job.next_run = self._calculate_next_run(job)

                logger.info(f"Job {job.id} completed, next run: {job.next_run}")

            except Exception as e:
                logger.error(f"Job {job.id} failed: {e}")

    async def _scheduler_loop(self):
        """调度循环"""
        while self._running:
            try:
                # 检查所有任务
                for job in self._jobs.values():
                    if job.enabled:
                        await self._run_job(job)

                # 等待一段时间
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(1)

    def start_scheduler_loop(self):
        """启动调度循环"""
        if not self._running:
            logger.warning("Scheduler not started, call start() first")
            return

        task = asyncio.create_task(self._scheduler_loop())
        self._tasks.append(task)
        logger.info("Scheduler loop started")


# ==================== 便捷函数 ====================

def parse_cron_expression(expression: str) -> Dict[str, Any]:
    """解析 Cron 表达式

    Args:
        expression: Cron 表达式

    Returns:
        Dict: 解析结果
    """
    parts = expression.split()

    if len(parts) != 5:
        raise ValueError("Cron expression must have 5 fields")

    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "weekday": parts[4]
    }


def format_interval(seconds: int) -> str:
    """格式化间隔

    Args:
        seconds: 秒数

    Returns:
        str: 格式化后的字符串
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}m"
        return f"{hours}h"


# ==================== 测试 ====================

if __name__ == "__main__":
    async def test():
        scheduler = Scheduler()
        await scheduler.start()

        # 测试间隔调度
        counter = {"value": 0}

        async def increment():
            counter["value"] += 1
            print(f"Counter: {counter['value']}")

        scheduler.schedule_interval(
            "increment",
            "Increment Counter",
            increment,
            seconds=1,
            max_runs=3
        )

        # 启动调度循环
        scheduler.start_scheduler_loop()

        # 等待
        await asyncio.sleep(5)

        # 停止
        await scheduler.stop()

        print(f"Final counter: {counter['value']}")

    asyncio.run(test())

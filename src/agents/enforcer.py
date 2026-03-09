"""
TodoEnforcer - 任务监督系统

实现任务监督机制：
- 任务队列管理
- 超时检测
- 优先级调度
- 失败重试
- 进度跟踪

参考:
- oh-my-openagent TodoEnforcer
- Celery Task Queue
- Airflow DAG Monitoring
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class TaskPriority(int, Enum):
    """任务优先级"""
    CRITICAL = 1    # 关键任务
    HIGH = 2        # 高优先级
    NORMAL = 3     # 普通
    LOW = 4         # 低优先级
    IDLE = 5        # 空闲时执行


class TodoStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class TodoItem:
    """待办事项"""
    id: str
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    status: TodoStatus = TodoStatus.PENDING
    assigned_to: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    deadline: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 300.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None


@dataclass
class EnforcerConfig:
    """监督配置"""
    max_concurrent_tasks: int = 5
    default_timeout: float = 300.0
    default_max_retries: int = 3
    check_interval: float = 1.0
    enable_deadline_check: bool = True
    enable_timeout_check: bool = True
    enable_dependency_check: bool = True


class TodoEnforcer:
    """任务监督器

    负责：
    - 任务队列管理
    - 优先级调度
    - 超时检测
    - 失败重试
    - 进度跟踪
    """

    def __init__(self, config: Optional[EnforcerConfig] = None):
        """初始化监督器

        Args:
            config: 监督配置
        """
        self.config = config or EnforcerConfig()

        # 任务存储
        self._tasks: Dict[str, TodoItem] = {}
        self._pending_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_tasks: Dict[str, asyncio.Task] = {}

        # 回调
        self._task_handlers: Dict[str, Callable] = {}

        # 统计
        self._stats = {
            "total_created": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
            "total_retries": 0,
        }

        # 控制
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

        logger.info("TodoEnforcer initialized")

    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理器

        Args:
            task_type: 任务类型
            handler: 处理函数
        """
        self._task_handlers[task_type] = handler
        logger.debug(f"Registered handler for: {task_type}")

    async def create_todo(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        task_type: str = "default",
        depends_on: Optional[List[str]] = None,
        deadline: Optional[datetime] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """创建待办事项

        Args:
            title: 标题
            description: 描述
            priority: 优先级
            task_type: 任务类型
            depends_on: 依赖任务
            deadline: 截止时间
            timeout_seconds: 超时时间
            max_retries: 最大重试次数
            metadata: 元数据

        Returns:
            str: 任务 ID
        """
        task_id = f"todo_{uuid.uuid4().hex[:8]}"

        todo = TodoItem(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            depends_on=depends_on or [],
            deadline=deadline.isoformat() if deadline else None,
            timeout_seconds=timeout_seconds or self.config.default_timeout,
            max_retries=max_retries if max_retries is not None else self.config.default_max_retries,
            metadata=metadata or {},
        )

        self._tasks[task_id] = todo
        self._stats["total_created"] += 1

        # 加入优先级队列
        await self._pending_queue.put((priority.value, task_id))

        logger.info(f"Created todo: {task_id} - {title}")
        return task_id

    async def execute(self, task_id: str) -> Any:
        """执行任务

        Args:
            task_id: 任务 ID

        Returns:
            Any: 执行结果
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")

        todo = self._tasks[task_id]

        # 检查依赖
        if self.config.enable_dependency_check:
            if not self._check_dependencies(todo):
                raise RuntimeError(f"Dependencies not met for {task_id}")

        # 检查是否已在运行
        if task_id in self._running_tasks:
            raise RuntimeError(f"Task {task_id} already running")

        # 更新状态
        todo.status = TodoStatus.RUNNING
        todo.started_at = datetime.now().isoformat()

        # 创建异步任务
        async_task = asyncio.create_task(self._run_task(todo))
        self._running_tasks[task_id] = async_task

        try:
            result = await async_task
            return result
        except asyncio.CancelledError:
            todo.status = TodoStatus.CANCELLED
            raise
        finally:
            self._running_tasks.pop(task_id, None)

    async def _run_task(self, todo: TodoItem) -> Any:
        """运行任务

        Args:
            todo: 待办事项

        Returns:
            Any: 执行结果
        """
        task_type = todo.metadata.get("task_type", "default")
        handler = self._task_handlers.get(task_type)

        try:
            # 执行处理函数
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    todo.result = await handler(todo)
                else:
                    todo.result = handler(todo)
            else:
                # 默认处理
                todo.result = await self._default_handler(todo)

            # 成功
            todo.status = TodoStatus.COMPLETED
            todo.completed_at = datetime.now().isoformat()
            self._stats["total_completed"] += 1

            logger.info(f"Task {todo.id} completed")
            return todo.result

        except asyncio.TimeoutError:
            todo.status = TodoStatus.TIMEOUT
            todo.error = "Task timeout"
            todo.completed_at = datetime.now().isoformat()

            # 重试
            if todo.retry_count < todo.max_retries:
                todo.retry_count += 1
                self._stats["total_retries"] += 1
                todo.status = TodoStatus.PENDING

                # 重新加入队列
                await self._pending_queue.put((todo.priority.value, todo.id))
                logger.warning(f"Task {todo.id} timeout, retry {todo.retry_count}/{todo.max_retries}")
            else:
                self._stats["total_failed"] += 1
                logger.error(f"Task {todo.id} failed after {todo.max_retries} retries")

            raise

        except Exception as e:
            todo.error = str(e)
            todo.completed_at = datetime.now().isoformat()

            # 重试
            if todo.retry_count < todo.max_retries:
                todo.retry_count += 1
                self._stats["total_retries"] += 1
                todo.status = TodoStatus.PENDING

                await self._pending_queue.put((todo.priority.value, todo.id))
                logger.warning(f"Task {todo.id} failed, retry {todo.retry_count}/{todo.max_retries}: {e}")
            else:
                todo.status = TodoStatus.FAILED
                self._stats["total_failed"] += 1
                logger.error(f"Task {todo.id} failed after {todo.max_retries} retries: {e}")

            raise

    async def _default_handler(self, todo: TodoItem) -> Dict[str, Any]:
        """默认处理函数

        Args:
            todo: 待办事项

        Returns:
            Dict: 处理结果
        """
        # 模拟处理
        await asyncio.sleep(0.1)

        return {
            "status": "completed",
            "task_id": todo.id,
            "message": f"Processed: {todo.title}",
        }

    def _check_dependencies(self, todo: TodoItem) -> bool:
        """检查依赖是否满足

        Args:
            todo: 待办事项

        Returns:
            bool: 是否满足
        """
        for dep_id in todo.depends_on:
            if dep_id not in self._tasks:
                return False

            dep_task = self._tasks[dep_id]
            if dep_task.status not in [TodoStatus.COMPLETED, TodoStatus.CANCELLED]:
                return False

        return True

    async def cancel(self, task_id: str) -> bool:
        """取消任务

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功
        """
        if task_id not in self._tasks:
            return False

        todo = self._tasks[task_id]

        # 如果在运行，取消它
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            self._running_tasks.pop(task_id)

        todo.status = TodoStatus.CANCELLED
        todo.completed_at = datetime.now().isoformat()
        self._stats["total_cancelled"] += 1

        logger.info(f"Cancelled task: {task_id}")
        return True

    async def get_task(self, task_id: str) -> Optional[TodoItem]:
        """获取任务

        Args:
            task_id: 任务 ID

        Returns:
            Optional[TodoItem]: 任务
        """
        return self._tasks.get(task_id)

    async def list_tasks(
        self,
        status: Optional[TodoStatus] = None,
        assigned_to: Optional[str] = None,
        limit: int = 100,
    ) -> List[TodoItem]:
        """列出任务

        Args:
            status: 状态过滤
            assigned_to: 分配给
            limit: 数量限制

        Returns:
            List[TodoItem]: 任务列表
        """
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]

        # 按优先级和创建时间排序
        tasks.sort(key=lambda t: (t.priority.value, t.created_at))

        return tasks[:limit]

    async def start_monitoring(self):
        """启动监控循环"""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info("TodoEnforcer monitoring started")

    async def stop_monitoring(self):
        """停止监控循环"""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("TodoEnforcer monitoring stopped")

    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 检查超时任务
                await self._check_timeouts()

                # 检查截止时间
                if self.config.enable_deadline_check:
                    await self._check_deadlines()

                # 自动执行队列中的任务
                await self._process_queue()

                await asyncio.sleep(self.config.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(self.config.check_interval)

    async def _check_timeouts(self):
        """检查超时任务"""
        if not self.config.enable_timeout_check:
            return

        now = datetime.now()

        for task_id, async_task in list(self._running_tasks.items()):
            todo = self._tasks.get(task_id)
            if not todo:
                continue

            if todo.started_at:
                started = datetime.fromisoformat(todo.started_at)
                elapsed = (now - started).total_seconds()

                if elapsed > todo.timeout_seconds:
                    logger.warning(f"Task {task_id} timeout after {elapsed:.1f}s")
                    async_task.cancel()

    async def _check_deadlines(self):
        """检查截止时间"""
        now = datetime.now()

        for todo in self._tasks.values():
            if todo.status != TodoStatus.PENDING:
                continue

            if todo.deadline:
                deadline = datetime.fromisoformat(todo.deadline)
                if now > deadline:
                    # 超过截止时间
                    overdue = (now - deadline).total_seconds()
                    logger.warning(f"Task {todo.id} overdue by {overdue:.1f}s")

    async def _process_queue(self):
        """处理队列"""
        # 检查并发限制
        if len(self._running_tasks) >= self.config.max_concurrent_tasks:
            return

        # 获取任务
        while not self._pending_queue.empty() and len(self._running_tasks) < self.config.max_concurrent_tasks:
            try:
                _, task_id = self._pending_queue.get_nowait()

                todo = self._tasks.get(task_id)
                if todo and todo.status == TodoStatus.PENDING:
                    # 检查依赖
                    if self._check_dependencies(todo):
                        asyncio.create_task(self.execute(task_id))

            except asyncio.QueueEmpty:
                break

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        return {
            "total_tasks": len(self._tasks),
            "pending": len([t for t in self._tasks.values() if t.status == TodoStatus.PENDING]),
            "running": len(self._running_tasks),
            "completed": self._stats["total_completed"],
            "failed": self._stats["total_failed"],
            "cancelled": self._stats["total_cancelled"],
            "retries": self._stats["total_retries"],
        }


# ==================== 便捷函数 ====================


def create_enforcer(
    max_concurrent: int = 5,
    default_timeout: float = 300.0,
) -> TodoEnforcer:
    """创建任务监督器

    Args:
        max_concurrent: 最大并发数
        default_timeout: 默认超时

    Returns:
        TodoEnforcer: 监督器实例
    """
    config = EnforcerConfig(
        max_concurrent_tasks=max_concurrent,
        default_timeout=default_timeout,
    )
    return TodoEnforcer(config)


# ==================== 测试 ====================

if __name__ == "__main__":
    async def test():
        # 创建监督器
        enforcer = create_enforcer()

        # 注册处理器
        enforcer.register_handler("test", lambda t: {"result": f"Done: {t.title}"})

        # 创建任务
        task1 = await enforcer.create_todo(
            title="Task 1",
            description="First task",
            priority=TaskPriority.HIGH,
            task_type="test",
        )

        task2 = await enforcer.create_todo(
            title="Task 2",
            description="Second task",
            priority=TaskPriority.NORMAL,
            task_type="test",
        )

        # 启动监控
        await enforcer.start_monitoring()

        # 执行任务
        result1 = await enforcer.execute(task1)
        print(f"Task 1 result: {result1}")

        # 列出任务
        tasks = await enforcer.list_tasks()
        print(f"Tasks: {len(tasks)}")

        # 统计
        stats = enforcer.get_stats()
        print(f"Stats: {stats}")

        # 停止监控
        await enforcer.stop_monitoring()

    asyncio.run(test())

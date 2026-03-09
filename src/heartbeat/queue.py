"""
Command Queue - Lane-based 命令队列

实现 OpenClaw 风格的 Lane-based 命令队列：
- global: 全局队列，最大并发 4
- session: 会话队列，串行执行
- sub_agent: 子 Agent 队列，最大并发 8
- cron: Cron 作业队列，并行执行

参考:
- OpenClaw: Lane-based FIFO ordering
- https://gist.github.com/royosherove/971c7b4a350a30ac8a8dad41604a95a0
"""
import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Awaitable
from loguru import logger


class LaneType(str, Enum):
    """Lane 类型"""
    GLOBAL = "global"
    SESSION = "session"
    SUB_AGENT = "sub_agent"
    CRON = "cron"


# Lane 配置
LANE_CONFIG = {
    LaneType.GLOBAL: {
        "max_concurrent": 4,
        "fifo": True,
        "description": "全局队列，用于一般命令"
    },
    LaneType.SESSION: {
        "max_concurrent": 1,
        "fifo": True,
        "description": "会话队列，串行执行确保顺序"
    },
    LaneType.SUB_AGENT: {
        "max_concurrent": 8,
        "fifo": True,
        "description": "子 Agent 队列，支持并行"
    },
    LaneType.CRON: {
        "max_concurrent": 10,
        "fifo": False,
        "description": "Cron 作业队列，并行执行"
    },
}


@dataclass
class Command:
    """命令"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    lane: LaneType = LaneType.GLOBAL
    session_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    side_effecting: bool = True
    priority: int = 0  # 更高优先级更早执行
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """用于优先级队列排序"""
        if self.priority != other.priority:
            return self.priority > other.priority  # 更高优先级在前
        return self.created_at < other.created_at  # 更早创建在前


@dataclass
class CommandResult:
    """命令执行结果"""
    command_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CommandQueue:
    """Lane-based 命令队列

    类似 OpenClaw 的命令队列实现：
    - Lane 隔离：不同类型的命令在不同 Lane 中执行
    - 并发控制：每个 Lane 有独立的并发限制
    - FIFO 排序：同 Lane 内按创建时间顺序执行
    - 幂等支持：使用 idempotency_key 防止重复执行
    """

    def __init__(self):
        """初始化命令队列"""
        # Lane 队列
        self._lanes: Dict[LaneType, asyncio.PriorityQueue] = {
            lane: asyncio.PriorityQueue() for lane in LaneType
        }

        # 执行中的命令
        self._running: Dict[str, asyncio.Task] = {}

        # 完成的命令缓存（用于幂等检查）
        self._completed: Dict[str, CommandResult] = {}

        # Lane 并发控制
        self._lane_semaphores: Dict[LaneType, asyncio.Semaphore] = {
            lane: asyncio.Semaphore(config["max_concurrent"])
            for lane, config in LANE_CONFIG.items()
        }

        # 回调
        self._handlers: Dict[str, Callable[[Command], Awaitable[Any]]] = {}

        logger.info(f"CommandQueue initialized with lanes: {list(LANE_CONFIG.keys())}")

    def register_handler(self, command_name: str, handler: Callable[[Command], Awaitable[Any]]):
        """注册命令处理器

        Args:
            command_name: 命令名称
            handler: 异步处理器函数
        """
        self._handlers[command_name] = handler
        logger.debug(f"Registered handler for command: {command_name}")

    async def enqueue(self, command: Command) -> str:
        """将命令加入队列

        Args:
            command: 命令

        Returns:
            str: 命令 ID
        """
        lane = command.lane

        # 检查幂等性
        if command.idempotency_key:
            if command.idempotency_key in self._completed:
                logger.info(f"Command {command.id} is idempotent, returning cached result")
                return command.id
            if command.idempotency_key in self._running:
                logger.info(f"Command {command.id} is already running")
                return command.id

        # 加入对应 Lane 的队列
        queue = self._lanes[lane]
        await queue.put((command.priority, command))
        logger.debug(f"Enqueued command {command.id} to lane {lane.value}")

        # 如果Lane未运行，开始运行
        asyncio.create_task(self._run_lane(lane))

        return command.id

    async def enqueue_batch(self, commands: List[Command]) -> List[str]:
        """批量加入队列

        Args:
            commands: 命令列表

        Returns:
            List[str]: 命令 ID 列表
        """
        return [await self.enqueue(cmd) for cmd in commands]

    async def _run_lane(self, lane: LaneType):
        """运行指定 Lane 的队列

        Args:
            lane: Lane 类型
        """
        queue = self._lanes[lane]
        semaphore = self._lane_semaphores[lane]
        config = LANE_CONFIG[lane]

        while True:
            try:
                # 获取信号量（并发控制）
                async with semaphore:
                    # 从队列获取命令
                    try:
                        priority, command = await asyncio.wait_for(
                            queue.get(),
                            timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        # 队列为空，退出
                        if queue.empty():
                            break
                        continue

                    # 检查是否已存在运行中
                    if command.id in self._running:
                        continue

                    # 执行命令
                    task = asyncio.create_task(self._execute(command))
                    self._running[command.id] = task

                    # 如果是 FIFO，等待完成
                    if config["fifo"]:
                        await task

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in lane {lane.value}: {e}")

        logger.debug(f"Lane {lane.value} stopped")

    async def _execute(self, command: Command) -> CommandResult:
        """执行命令

        Args:
            command: 命令

        Returns:
            CommandResult: 执行结果
        """
        start_time = asyncio.get_event_loop().time()

        # 标记运行中
        if command.idempotency_key:
            self._running[command.idempotency_key] = asyncio.current_task()

        logger.info(f"Executing command {command.id} ({command.name})")

        try:
            # 查找处理器
            handler = self._handlers.get(command.name)
            if not handler:
                raise ValueError(f"No handler for command: {command.name}")

            # 执行
            result = await handler(command)

            execution_time = asyncio.get_event_loop().time() - start_time

            cmd_result = CommandResult(
                command_id=command.id,
                success=True,
                result=result,
                execution_time=execution_time,
                metadata=command.metadata
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time

            cmd_result = CommandResult(
                command_id=command.id,
                success=False,
                error=str(e),
                execution_time=execution_time,
                metadata=command.metadata
            )

            logger.error(f"Command {command.id} failed: {e}")

        finally:
            # 清理状态
            self._running.pop(command.id, None)

            # 缓存结果（用于幂等）
            if command.idempotency_key:
                self._completed[command.idempotency_key] = cmd_result

            # 清理旧缓存（保留 1000 条）
            if len(self._completed) > 1000:
                keys_to_remove = list(self._completed.keys())[:500]
                for key in keys_to_remove:
                    self._completed.pop(key, None)

        return cmd_result

    async def get_result(self, command_id: str, timeout: float = 30.0) -> Optional[CommandResult]:
        """获取命令结果

        Args:
            command_id: 命令 ID
            timeout: 超时时间

        Returns:
            Optional[CommandResult]: 命令结果
        """
        # 等待命令完成
        start = asyncio.get_event_loop().time()
        while command_id in self._running:
            if asyncio.get_event_loop().time() - start > timeout:
                return None
            await asyncio.sleep(0.1)

        # 返回缓存结果
        for result in self._completed.values():
            if result.command_id == command_id:
                return result

        return None

    def get_status(self) -> Dict[str, Any]:
        """获取队列状态

        Returns:
            Dict: 状态信息
        """
        status = {
            "lanes": {},
            "running_count": len(self._running),
            "completed_count": len(self._completed)
        }

        for lane in LaneType:
            queue = self._lanes[lane]
            config = LANE_CONFIG[lane]
            semaphore = self._lane_semaphores[lane]

            status["lanes"][lane.value] = {
                "queue_size": queue.qsize(),
                "max_concurrent": config["max_concurrent"],
                "available_slots": semaphore._value,
                "running": sum(
                    1 for cmd_id in self._running
                    if self._lanes[lane]._queue  # 检查命令所属 Lane
                )
            }

        return status

    async def cancel(self, command_id: str) -> bool:
        """取消命令

        Args:
            command_id: 命令 ID

        Returns:
            bool: 是否成功取消
        """
        task = self._running.get(command_id)
        if task:
            task.cancel()
            self._running.pop(command_id, None)
            return True
        return False

    async def shutdown(self):
        """关闭队列"""
        logger.info("Shutting down CommandQueue...")

        # 取消所有运行中的任务
        for task in self._running.values():
            task.cancel()

        # 等待完成
        if self._running:
            await asyncio.gather(*self._running.values(), return_exceptions=True)

        logger.info("CommandQueue shutdown complete")


# ==================== 便捷函数 ====================

def create_command(
    name: str,
    args: Optional[Dict[str, Any]] = None,
    lane: LaneType = LaneType.GLOBAL,
    session_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    priority: int = 0
) -> Command:
    """创建命令

    Args:
        name: 命令名称
        args: 命令参数
        lane: Lane 类型
        session_id: 会话 ID
        idempotency_key: 幂等性 key
        priority: 优先级

    Returns:
        Command: 命令
    """
    return Command(
        name=name,
        args=args or {},
        lane=lane,
        session_id=session_id,
        idempotency_key=idempotency_key,
        priority=priority
    )


# ==================== 测试 ====================

if __name__ == "__main__":
    async def test():
        queue = CommandQueue()

        # 注册处理器
        async def echo_handler(cmd: Command):
            await asyncio.sleep(0.1)  # 模拟处理
            return f"Echo: {cmd.args.get('message', '')}"

        queue.register_handler("echo", echo_handler)

        # 添加命令
        commands = [
            create_command("echo", {"message": "hello"}, priority=1),
            create_command("echo", {"message": "world"}, priority=2),
            create_command("echo", {"message": "test"}, lane=LaneType.SESSION),
        ]

        for cmd in commands:
            await queue.enqueue(cmd)

        # 等待执行
        await asyncio.sleep(0.5)

        # 检查状态
        status = queue.get_status()
        print(f"Queue status: {status}")

    asyncio.run(test())

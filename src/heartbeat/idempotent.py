"""
Idempotent Command - 幂等命令

实现幂等性命令执行：
- 幂等性 key 生成
- 缓存执行结果
- 安全重试机制

参考:
- OpenClaw: Idempotency keys for side-effecting methods
- https://gist.github.com/royosherove/971c7b4a350a30ac8a8dad41604a95a0
"""
import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Awaitable

from loguru import logger


@dataclass
class IdempotentResult:
    """幂等执行结果"""
    key: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    created_at: float = field(default_factory=time.time)
    executed_at: Optional[float] = None


class IdempotentExecutor:
    """幂等执行器

    确保命令只执行一次：
    1. 使用唯一 key 标识命令
    2. 缓存结果防止重复执行
    3. 支持 TTL 自动过期
    """

    def __init__(
        self,
        max_cache_size: int = 1000,
        default_ttl: int = 3600  # 1小时
    ):
        """初始化执行器

        Args:
            max_cache_size: 最大缓存数量
            default_ttl: 默认过期时间（秒）
        """
        self.max_cache_size = max_cache_size
        self.default_ttl = default_ttl

        # 缓存: key -> IdempotentResult
        self._cache: Dict[str, IdempotentResult] = {}

        # 锁: key -> asyncio.Lock
        self._locks: Dict[str, asyncio.Lock] = {}

        # 统计
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }

        logger.info(f"IdempotentExecutor initialized (max_cache={max_cache_size}, ttl={default_ttl}s)")

    async def execute(
        self,
        key: str,
        handler: Callable[..., Awaitable[Any]],
        *args,
        ttl: Optional[int] = None,
        **kwargs
    ) -> IdempotentResult:
        """幂等执行

        Args:
            key: 幂等性 key
            handler: 处理器
            *args: 位置参数
            ttl: 过期时间（秒）
            **kwargs: 关键字参数

        Returns:
            IdempotentResult: 执行结果
        """
        # 检查缓存
        cached = self._cache.get(key)
        if cached and not self._is_expired(cached, ttl):
            self._stats["hits"] += 1
            logger.debug(f"Idempotent cache hit: {key}")
            return cached

        self._stats["misses"] += 1

        # 获取或创建锁
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock

        # 使用锁防止并发执行
        async with lock:
            # 双重检查（获取锁后再次检查缓存）
            cached = self._cache.get(key)
            if cached and not self._is_expired(cached, ttl):
                return cached

            # 执行
            start_time = time.time()
            try:
                logger.info(f"Executing idempotent command: {key}")

                if asyncio.iscoroutinefunction(handler):
                    result = await handler(*args, **kwargs)
                else:
                    result = handler(*args, **kwargs)

                execution_time = time.time() - start_time

                idempotent_result = IdempotentResult(
                    key=key,
                    success=True,
                    result=result,
                    execution_time=execution_time,
                    executed_at=time.time()
                )

            except Exception as e:
                execution_time = time.time() - start_time
                self._stats["errors"] += 1

                logger.error(f"Idempotent command failed: {key} - {e}")

                idempotent_result = IdempotentResult(
                    key=key,
                    success=False,
                    error=str(e),
                    execution_time=execution_time,
                    executed_at=time.time()
                )

            # 缓存结果
            self._cache[key] = idempotent_result
            self._cleanup()

            return idempotent_result

    def _is_expired(self, result: IdempotentResult, ttl: Optional[int] = None) -> bool:
        """检查是否过期

        Args:
            result: 结果
            ttl: 过期时间

        Returns:
            bool: 是否过期
        """
        ttl = ttl or self.default_ttl

        if result.executed_at is None:
            return False

        return (time.time() - result.executed_at) > ttl

    def _cleanup(self):
        """清理过期缓存"""
        if len(self._cache) > self.max_cache_size:
            # 按时间排序，删除最老的
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1].created_at
            )

            # 删除一半
            keys_to_delete = [k for k, _ in sorted_items[:len(sorted_items) // 2]]
            for key in keys_to_delete:
                del self._cache[key]
                self._locks.pop(key, None)

            logger.debug(f"Cleaned up {len(keys_to_delete)} expired cache entries")

    def get_result(self, key: str) -> Optional[IdempotentResult]:
        """获取缓存结果

        Args:
            key: 幂等性 key

        Returns:
            Optional[IdempotentResult]: 结果
        """
        result = self._cache.get(key)
        if result and not self._is_expired(result):
            return result
        return None

    def invalidate(self, key: str) -> bool:
        """使缓存失效

        Args:
            key: 幂等性 key

        Returns:
            bool: 是否成功
        """
        if key in self._cache:
            del self._cache[key]
            self._locks.pop(key, None)
            return True
        return False

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._locks.clear()
        logger.info("Idempotent cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0

        return {
            **self._stats,
            "total": total,
            "hit_rate": hit_rate,
            "cache_size": len(self._cache)
        }


# ==================== 幂等性 Key 生成 ====================

def create_idempotent_key(
    command: str,
    args: Dict[str, Any],
    namespace: str = "default",
    time_window: int = 3600  # 1小时窗口
) -> str:
    """创建幂等性 key

    Args:
        command: 命令名称
        args: 命令参数
        namespace: 命名空间
        time_window: 时间窗口（秒）

    Returns:
        str: 幂等性 key
    """
    # 排序参数确保一致性
    sorted_args = json.dumps(args, sort_keys=True, default=str)

    # 计算小时级时间窗口
    window = int(time.time() // time_window)

    # 构建 key 数据
    key_data = f"{namespace}:{command}:{sorted_args}:{window}"

    # 生成 hash
    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


def create_user_action_key(
    user_id: str,
    action: str,
    resource: Optional[str] = None
) -> str:
    """创建用户动作幂等 key

    Args:
        user_id: 用户 ID
        action: 动作
        resource: 资源

    Returns:
        str: 幂等性 key
    """
    parts = [user_id, action]
    if resource:
        parts.append(resource)

    # 使用时间戳（天级）
    day = datetime.now().strftime("%Y-%m-%d")

    key_data = f"user_action:{':'.join(parts)}:{day}"

    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


def create_session_key(
    session_id: str,
    operation: str,
    params: Optional[Dict[str, Any]] = None
) -> str:
    """创建会话幂等 key

    Args:
        session_id: 会话 ID
        operation: 操作
        params: 参数

    Returns:
        str: 幂等性 key
    """
    params_str = json.dumps(params or {}, sort_keys=True, default=str)
    key_data = f"session:{session_id}:{operation}:{params_str}"

    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


# ==================== 全局实例 ====================

_default_executor: Optional[IdempotentExecutor] = None


def get_idempotent_executor() -> IdempotentExecutor:
    """获取默认执行器

    Returns:
        IdempotentExecutor: 执行器
    """
    global _default_executor
    if _default_executor is None:
        _default_executor = IdempotentExecutor()
    return _default_executor


# ==================== 测试 ====================

if __name__ == "__main__":
    async def test():
        executor = IdempotentExecutor()

        # 测试处理器
        async def slow_operation(value: int) -> int:
            await asyncio.sleep(0.1)
            return value * 2

        # 第一次执行
        key = create_idempotent_key("test_op", {"value": 10})
        result1 = await executor.execute(key, slow_operation, 10)
        print(f"First execution: {result1.result}, success: {result1.success}")

        # 第二次执行（应该使用缓存）
        result2 = await executor.execute(key, slow_operation, 10)
        print(f"Second execution (cached): {result2.result}, success: {result2.success}")

        # 统计
        stats = executor.get_stats()
        print(f"Stats: {stats}")

    asyncio.run(test())

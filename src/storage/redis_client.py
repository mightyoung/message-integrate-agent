# coding=utf-8
"""
Redis Client - 缓存和会话管理
"""
import os
import json
from typing import Any, Optional, List

import redis
from loguru import logger


class RedisClient:
    """Redis 客户端"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = None,
        password: str = None,
    ):
        """初始化 Redis 客户端

        Args:
            host: 主机地址
            port: 端口
            db: 数据库编号
            password: 密码
        """
        self.host = host or os.environ.get("REDIS_HOST", "localhost")
        self.port = port or int(os.environ.get("REDIS_PORT", "6379"))
        self.db = db or int(os.environ.get("REDIS_DB", "0"))
        self.password = password or os.environ.get("REDIS_PASSWORD")

        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True,
        )

        logger.info(f"RedisClient initialized: {self.host}:{self.port}/{self.db}")

    def set(self, key: str, value: Any, expire: int = None) -> bool:
        """设置值

        Args:
            key: 键
            value: 值
            expire: 过期时间(秒)

        Returns:
            是否成功
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)

        result = self.client.set(key, value, ex=expire)
        return bool(result)

    def get(self, key: str, default: Any = None) -> Any:
        """获取值

        Args:
            key: 键
            default: 默认值

        Returns:
            值或默认值
        """
        value = self.client.get(key)
        if value is None:
            return default

        # 尝试解析 JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def delete(self, *keys: str) -> int:
        """删除键

        Args:
            *keys: 键列表

        Returns:
            删除的数量
        """
        return self.client.delete(*keys)

    def exists(self, key: str) -> bool:
        """检查键是否存在

        Args:
            key: 键

        Returns:
            是否存在
        """
        return bool(self.client.exists(key))

    def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间

        Args:
            key: 键
            seconds: 秒数

        Returns:
            是否成功
        """
        return bool(self.client.expire(key, seconds))

    def ttl(self, key: str) -> int:
        """获取剩余过期时间

        Args:
            key: 键

        Returns:
            秒数 (-2 表示不存在, -1 表示永不过期)
        """
        return self.client.ttl(key)

    def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配的键

        Args:
            pattern: 匹配模式

        Returns:
            键列表
        """
        return self.client.keys(pattern)

    def incr(self, key: str, amount: int = 1) -> int:
        """递增

        Args:
            key: 键
            amount: 增量

        Returns:
            新值
        """
        return self.client.incr(key, amount)

    def hset(self, name: str, key: str, value: Any) -> int:
        """设置哈希字段

        Args:
            name: 哈希名
            key: 字段
            value: 值

        Returns:
            新增/更新的字段数
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        return self.client.hset(name, key, value)

    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """获取哈希字段

        Args:
            name: 哈希名
            key: 字段
            default: 默认值

        Returns:
            值或默认值
        """
        value = self.client.hget(name, key)
        if value is None:
            return default

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def hgetall(self, name: str) -> dict:
        """获取所有哈希字段

        Args:
            name: 哈希名

        Returns:
            字典
        """
        result = self.client.hgetall(name)
        # 尝试解析 JSON 值
        for key, value in result.items():
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def hdel(self, name: str, *keys: str) -> int:
        """删除哈希字段

        Args:
            name: 哈希名
            *keys: 字段列表

        Returns:
            删除的字段数
        """
        return self.client.hdel(name, *keys)

    def publish(self, channel: str, message: Any) -> int:
        """发布消息

        Args:
            channel: 频道
            message: 消息

        Returns:
            订阅者数量
        """
        if not isinstance(message, str):
            message = json.dumps(message, ensure_ascii=False)
        return self.client.publish(channel, message)

    def ping(self) -> bool:
        """检查连接

        Returns:
            是否成功
        """
        return self.client.ping()

    def close(self):
        """关闭连接"""
        self.client.close()
        logger.info("Redis connection closed")


def create_redis_client() -> RedisClient:
    """创建 Redis 客户端的便捷函数"""
    return RedisClient()

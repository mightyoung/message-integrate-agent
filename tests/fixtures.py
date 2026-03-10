# coding=utf-8
"""
Test Fixtures - 测试夹具

提供测试所需的 fixtures:
- Redis 隔离客户端
- 唯一测试数据生成器
- Mock 配置
"""
import pytest
import os
from typing import Optional
import redis

from .test_config import (
    TEST_REDIS_DB,
    generate_unique_test_id,
    get_test_url,
    get_test_title,
)

# 导入 RedisClient 用于适配
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.storage.redis_client import RedisClient as StorageRedisClient


class TestRedisClient:
    """测试用 Redis 客户端

    使用独立的测试数据库，避免污染生产数据
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
    ):
        self.host = host or os.environ.get("REDIS_HOST", "localhost")
        self.port = port or int(os.environ.get("REDIS_PORT", "6379"))
        self.db = db or TEST_REDIS_DB
        self._client = None

    @property
    def client(self):
        """获取Redis客户端"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
            )
        return self._client

    def flushdb(self):
        """清空当前测试数据库"""
        self.client.flushdb()

    def exists(self, key: str) -> bool:
        """检查key是否存在"""
        return self.client.exists(key) > 0

    def set(self, key: str, value: str, expire: Optional[int] = None):
        """设置key-value"""
        if expire:
            self.client.setex(key, expire, value)
        else:
            self.client.set(key, value)

    def get(self, key: str) -> Optional[str]:
        """获取value"""
        return self.client.get(key)

    def delete(self, key: str):
        """删除key"""
        self.client.delete(key)

    def to_storage_redis_client(self) -> StorageRedisClient:
        """转换为 Storage 使用的 RedisClient 格式

        返回一个适配器，使 StorageManager 可以使用测试 Redis
        """
        return TestRedisAdapter(self)


class TestRedisAdapter:
    """测试 Redis 适配器

    适配测试 Redis 客户端以匹配 StorageManager 的 RedisClient 接口
    """

    def __init__(self, test_client: TestRedisClient):
        self._client = test_client

    def exists(self, key: str) -> bool:
        """检查key是否存在"""
        return self._client.exists(key)

    def set(self, key: str, value: str, expire: Optional[int] = None):
        """设置key-value"""
        if expire:
            self._client.set(key, value, expire)
        else:
            self._client.set(key, value)

    def get(self, key: str) -> Optional[str]:
        """获取value"""
        return self._client.get(key)

    def delete(self, key: str):
        """删除key"""
        self._client.delete(key)


@pytest.fixture
def test_redis():
    """测试Redis客户端 fixture"""
    client = TestRedisClient()

    # 测试前清理
    client.flushdb()

    yield client

    # 测试后清理
    client.flushdb()


@pytest.fixture
def test_storage_manager(test_redis):
    """测试用 StorageManager fixture

    使用隔离的测试 Redis 数据库
    """
    from src.storage.storage_manager import StorageManager

    # 创建适配器
    redis_adapter = test_redis.to_storage_redis_client()

    # 创建使用测试 Redis 的 StorageManager
    storage = StorageManager(
        enable_postgres=False,
        enable_s3=False,
        enable_redis=True,
        redis_client=redis_adapter,
    )

    yield storage


@pytest.fixture
def unique_url():
    """生成唯一测试URL"""
    return get_test_url()


@pytest.fixture
def unique_title():
    """生成唯一测试标题"""
    return get_test_title()


@pytest.fixture
def unique_test_id():
    """生成唯一测试ID"""
    return generate_unique_test_id()

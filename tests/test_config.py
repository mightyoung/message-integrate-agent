# coding=utf-8
"""
Test Configuration - 测试配置

提供测试环境的隔离配置:
- Redis 隔离数据库
- 测试环境变量
- Mock 配置
"""
import os
import uuid
from typing import Optional

# 测试Redis数据库 - 使用独立db避免污染生产数据
TEST_REDIS_DB = int(os.environ.get("TEST_REDIS_DB", "1"))

# 测试数据过期时间 (秒)
TEST_DEDUP_EXPIRE = 3600  # 1小时

# 测试超时配置
TEST_TIMEOUT = 30  # 秒

# Mock配置
USE_MOCK_EXTERNAL = os.environ.get("USE_MOCK_EXTERNAL", "false").lower() == "true"


def generate_unique_test_id() -> str:
    """生成唯一测试ID"""
    return str(uuid.uuid4())[:8]


def get_test_url(prefix: str = "test") -> str:
    """生成唯一测试URL"""
    return f"https://{prefix}-{generate_unique_test_id()}.com/article"


def get_test_title(prefix: str = "Test") -> str:
    """生成唯一测试标题"""
    return f"{prefix} Title {generate_unique_test_id()}"

# coding=utf-8
"""
Pytest Configuration - pytest 配置

注册全局 fixtures 和配置
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入 fixtures
from tests.fixtures import (
    test_redis,
    test_storage_manager,
    unique_url,
    unique_title,
    unique_test_id,
)


# Pytest 配置
def pytest_configure(config):
    """Pytest 配置"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "unit: 单元测试标记"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试标记"
    )
    config.addinivalue_line(
        "markers", "e2e: 端到端测试标记"
    )


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

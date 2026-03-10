# 情报流水线测试重新设计方案

**日期**: 2026-03-10
**版本**: v1.0
**状态**: 已批准

---

## 1. 背景与目标

### 1.1 当前问题

| 问题 | 影响 | 优先级 |
|-----|------|-------|
| Redis测试数据残留 | 去重测试失败 | P0 |
| 外部API依赖不稳定 | 测试跳过过多 | P1 |
| 评估标准不完善 | 无法量化质量 | P2 |

### 1.2 目标

- [ ] 解决Redis隔离问题
- [ ] 改进外部依赖测试策略
- [ ] 完善评估标准体系
- [ ] 实现分层次测试架构

---

## 2. 测试架构设计

### 2.1 分层测试模型

```
┌──────────────────────────────────────────────┐
│  端到端测试 (E2E)                            │
│  - 真实完整环境                              │
│  - 无Mock                                    │
│  - 验证完整数据流                           │
└──────────────────────────────────────────────┘
                      ↑
┌──────────────────────────────────────────────┐
│  集成测试 (Integration)                      │
│  - 存储层真实调用                           │
│  - 外部API降级处理                          │
│  - 验证组件交互                             │
└──────────────────────────────────────────────┘
                      ↑
┌──────────────────────────────────────────────┐
│  单元测试 (Unit)                             │
│  - 完全隔离环境                             │
│  - Mock所有外部依赖                          │
│  - 验证单一组件逻辑                          │
└──────────────────────────────────────────────┘
```

### 2.2 测试用例分类

| 类别 | 位置 | 外部依赖 | 隔离级别 |
|-----|------|---------|---------|
| test_redis_dedup_* | Unit | Mock Redis | 完全隔离 |
| test_*_fetcher | Integration | 真实网络/降级 | 部分隔离 |
| test_storage_* | Integration | 真实存储 | 组件隔离 |
| test_pipeline_* | E2E | 真实环境 | 无隔离 |

---

## 3. Redis隔离方案

### 3.1 独立测试数据库

```python
# 配置测试Redis数据库
TEST_REDIS_DB = int(os.environ.get("TEST_REDIS_DB", "1"))

class TestRedisClient:
    """测试用Redis客户端"""
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = redis.Redis(
                host=os.environ.get("REDIS_HOST", "localhost"),
                port=int(os.environ.get("REDIS_PORT", "6379")),
                db=TEST_REDIS_DB,  # 使用独立db
                decode_responses=True
            )
        return self._client

    def flush_test_db(self):
        """清空测试数据库"""
        self.client.flushdb()
```

### 3.2 测试Fixture

```python
@pytest.fixture(autouse=True)
def clean_redis_test_db(redis_client):
    """每个测试前后清理测试数据库"""
    redis_client.flush_test_db()
    yield
    redis_client.flush_test_db()

@pytest.fixture
def redis_client():
    """测试Redis客户端"""
    return TestRedisClient()
```

---

## 4. 外部依赖处理

### 4.1 Mock策略

| 依赖类型 | 策略 | 实现方式 |
|---------|-----|---------|
| HTTP请求 | Mock响应 | pytest-responses |
| LLM API | Mock响应 | unittest.mock |
| 数据库 | 隔离连接 | 测试数据库 |

### 4.2 网络测试降级

```python
def fetcher_with_fallback(fetcher_class, *args, **kwargs):
    """带降级的获取器"""
    try:
        return fetcher_class(*args, **kwargs)
    except NetworkError:
        # 返回空结果而不是跳过测试
        return EmptyFetcher()
```

---

## 5. 评估标准体系

### 5.1 功能评估

| 指标 | 定义 | 计算方式 | 阈值 |
|-----|------|---------|-----|
| **采集覆盖率** | 成功采集的数据源比例 | 成功源数/总源数 | ≥80% |
| **去重准确率** | 正确识别重复的比例 | 正确去重/总重复 | 100% |
| **存储成功率** | 成功存储的比例 | 成功数/总数 | ≥95% |
| **分析成功率** | 成功分析的比例 | 成功数/总数 | ≥90% |

### 5.2 性能评估

| 指标 | 定义 | 计算方式 | 阈值 |
|-----|------|---------|-----|
| **采集延迟** | 获取数据耗时 | time.time()差值 | <30s |
| **分析延迟** | 单条分析耗时 | 总时间/条数 | <5s |
| **存储延迟** | 单条存储耗时 | 总时间/条数 | <2s |

### 5.3 可靠性评估

| 指标 | 定义 | 计算方式 | 阈值 |
|-----|------|---------|-----|
| **失败恢复率** | 自动恢复比例 | 恢复数/失败数 | ≥90% |
| **超时率** | 超时比例 | 超时数/总数 | <5% |
| **数据新鲜度** | 数据时效性 | 时间差 | <24h |

---

## 6. 测试用例改进

### 6.1 修复去重测试

```python
class TestDeduplication:
    """去重测试 - 单元测试级别"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with clean Redis"""
        self.redis = TestRedisClient()
        self.redis.flush_test_db()
        self.storage = create_storage_manager(
            redis_client=self.redis
        )

    @pytest.mark.unit
    async def test_redis_dedup_by_url(self):
        """URL去重 - 隔离环境测试"""
        # 使用唯一的测试URL
        unique_url = f"https://test-{uuid.uuid4()}.com/article"

        is_dup = self.storage.check_duplicate(unique_url, "Test", "test")
        assert is_dup == False

        self.storage.mark_processed(unique_url, "Test", "test")

        is_dup = self.storage.check_duplicate(unique_url, "Test", "test")
        assert is_dup == True
```

### 6.2 改进跳过逻辑

```python
def is_retryable_error(error: Exception) -> bool:
    """判断错误是否可重试"""
    retryable = (
        isinstance(error, TimeoutError),
        isinstance(error, ConnectionError),
        "timeout" in str(error).lower(),
        "connection" in str(error).lower(),
    )
    return any(retryable)

def is_permanent_error(error: Exception) -> bool:
    """判断错误是否永久性"""
    permanent = (
        isinstance(error, AuthError),
        isinstance(error, NotFoundError),
        "unauthorized" in str(error).lower(),
        "not found" in str(error).lower(),
    )
    return any(permanent)

@pytest.mark.skipif(
    not is_retryable_error(last_error),
    reason="Permanent failure: {error}"
)
async def test_weibo_fetcher():
    """只有可重试错误才跳过"""
    ...
```

---

## 7. 实施计划

### Phase 1: 基础设施 (1小时)
- [ ] 创建测试Redis配置
- [ ] 添加测试Fixture
- [ ] 配置测试数据库

### Phase 2: 单元测试 (2小时)
- [ ] 修复Redis去重测试
- [ ] 添加Mock配置
- [ ] 改进跳过逻辑

### Phase 3: 集成测试 (2小时)
- [ ] 改进存储测试
- [ ] 添加降级处理
- [ ] 完善评估标准

### Phase 4: E2E测试 (1小时)
- [ ] 改进端到端测试
- [ ] 添加性能测试
- [ ] 生成评估报告

---

## 8. 预期结果

| 指标 | 当前 | 目标 |
|-----|------|-----|
| 测试通过率 | 65% | ≥90% |
| 跳过率 | 24% | <10% |
| 失败率 | 11% | <5% |
| 评估覆盖率 | 60% | 100% |

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| 测试环境差异 | 本地通过，生产失败 | 使用Docker镜像 |
| Mock不准确 | 测试通过但实际失败 | 定期同步真实响应 |
| 维护成本 | 更新需要改Mock | 录制真实响应文件 |

---

**批准**: 2026-03-10
**下一步**: 实施计划

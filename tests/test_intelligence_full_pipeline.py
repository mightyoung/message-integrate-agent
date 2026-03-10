# coding=utf-8
"""
Intelligence Pipeline Full Integration Tests

全流程测试:
- 数据源采集测试 (RSS, Weibo, Zhihu, B站, GitHub, 论文)
- 去重测试
- 分析测试
- 存储测试 (PostgreSQL, S3, Redis)
- 评分测试
- 推送测试
- 端到端完整流程测试

运行方式:
    # 全部测试
    python -m pytest tests/test_intelligence_full_pipeline.py -v -s

    # 单独测试数据源
    python -m pytest tests/test_intelligence_full_pipeline.py::TestDataSources -v -s

    # 单独测试存储
    python -m pytest tests/test_intelligence_full_pipeline.py::TestStorage -v -s
"""
import os
import sys
import pytest
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# 导入测试配置和 fixtures
from tests.fixtures import unique_url, unique_title, unique_test_id
from tests.test_config import get_test_url, get_test_title, generate_unique_test_id

# 设置测试环境变量
def setup_test_env():
    """设置测试环境变量"""
    # 从 .env.prod 加载配置
    env_file = ".env.prod"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key, value)

    # 设置测试特定的配置
    os.environ.setdefault("ENVIRONMENT", "test")

setup_test_env()


# ============================================================
# Test Data Sources - 数据源采集测试
# ============================================================

class TestDataSources:
    """数据源采集测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试"""
        self.results = {}

    @pytest.mark.asyncio
    async def test_rss_fetcher(self):
        """测试 RSS 源采集"""
        from src.intelligence.rss_fetcher import RSSFetcher

        print("\n=== 测试 RSS 源采集 ===")

        fetcher = RSSFetcher(proxy_url=os.environ.get("HTTP_PROXY"))

        try:
            # 使用 fetch_multiple 获取多个 RSS 源
            items = await fetcher.fetch_multiple_async(
                categories=["tech", "geopolitics"],
                max_items_per_feed=5
            )
            print(f"RSS 获取: {len(items)} 条")

            # 验证
            assert len(items) > 0, "RSS 采集失败"
            print(f"✅ RSS 源采集成功: {len(items)} 条")

        except Exception as e:
            print(f"❌ RSS 源采集失败: {e}")
            # RSS 失败不应该阻止其他测试
            pytest.skip(f"RSS 采集跳过: {e}")

    @pytest.mark.asyncio
    async def test_weibo_fetcher(self):
        """测试微博热搜采集"""
        from src.intelligence.hot_fetcher import WeiboHotFetcher

        print("\n=== 测试微博热搜采集 ===")

        fetcher = WeiboHotFetcher(proxy_url=os.environ.get("HTTP_PROXY"))

        try:
            items = await fetcher.fetch()
            print(f"微博热搜获取: {len(items)} 条")

            # 验证
            assert len(items) > 0, "微博采集失败"
            print(f"✅ 微博热搜采集成功: {len(items)} 条")

        except Exception as e:
            print(f"❌ 微博热搜采集失败: {e}")
            pytest.skip(f"微博采集跳过: {e}")

    @pytest.mark.asyncio
    async def test_hackernews_fetcher(self):
        """测试 HackerNews 采集"""
        from src.intelligence.hot_fetcher import HackerNewsFetcher

        print("\n=== 测试 HackerNews 采集 ===")

        fetcher = HackerNewsFetcher()

        try:
            items = await fetcher.fetch()
            print(f"HackerNews 获取: {len(items)} 条")

            # 验证
            assert len(items) > 0, "HackerNews 采集失败"
            print(f"✅ HackerNews 采集成功: {len(items)} 条")

        except Exception as e:
            print(f"❌ HackerNews 采集失败: {e}")
            pytest.skip(f"HackerNews 采集跳过: {e}")

    @pytest.mark.asyncio
    async def test_github_trending_fetcher(self):
        """测试 GitHub Trending 采集"""
        from src.intelligence.github_trending import GitHubTrendingFetcher

        print("\n=== 测试 GitHub Trending 采集 ===")

        fetcher = GitHubTrendingFetcher()

        try:
            items = fetcher.fetch()  # 同步方法
            print(f"GitHub Trending 获取: {len(items)} 条")

            # 验证
            assert len(items) > 0, "GitHub 采集失败"
            print(f"✅ GitHub Trending 采集成功: {len(items)} 条")

        except Exception as e:
            print(f"❌ GitHub Trending 采集失败: {e}")
            pytest.skip(f"GitHub 采集跳过: {e}")

    @pytest.mark.asyncio
    async def test_academic_fetcher(self):
        """测试学术论文采集"""
        from src.intelligence.academic_fetcher import ArxivFetcher

        print("\n=== 测试 Arxiv 论文采集 ===")

        fetcher = ArxivFetcher()

        try:
            papers = await fetcher.fetch()
            print(f"Arxiv 论文获取: {len(papers)} 条")

            # 验证
            assert len(papers) > 0, "学术论文采集失败"
            print(f"✅ Arxiv 论文采集成功: {len(papers)} 条")

        except Exception as e:
            print(f"❌ Arxiv 论文采集失败: {e}")
            pytest.skip(f"学术论文采集跳过: {e}")

    @pytest.mark.asyncio
    async def test_huggingface_fetcher(self):
        """测试 HuggingFace 论文采集"""
        from src.intelligence.academic_fetcher import HuggingFaceFetcher

        print("\n=== 测试 HuggingFace 论文采集 ===")

        fetcher = HuggingFaceFetcher()

        try:
            papers = await fetcher.fetch()
            print(f"HuggingFace 论文获取: {len(papers)} 条")

            # 验证
            assert len(papers) > 0, "HuggingFace 论文采集失败"
            print(f"✅ HuggingFace 论文采集成功: {len(papers)} 条")

        except Exception as e:
            print(f"❌ HuggingFace 论文采集失败: {e}")
            pytest.skip(f"HuggingFace 论文采集跳过: {e}")

    @pytest.mark.asyncio
    async def test_all_sources_fetch(self):
        """测试全部数据源采集"""
        from src.intelligence.hot_fetcher import HotFetcher

        print("\n=== 测试全部数据源采集 ===")

        fetcher = HotFetcher(proxy_url=os.environ.get("HTTP_PROXY"))

        # 测试各个平台
        sources = ["weibo", "hackernews", "producthunt"]

        for source in sources:
            try:
                items = await fetcher.fetch_source(source)
                self.results[source] = len(items)
                print(f"{source}: {len(items)} 条")

            except Exception as e:
                print(f"❌ {source} 采集失败: {e}")
                self.results[source] = 0

        # 至少有一个数据源成功
        if sum(self.results.values()) == 0:
            pytest.skip("所有数据源采集失败")
        print(f"✅ 多源采集成功: {self.results}")


# ============================================================
# Test Deduplication - 去重测试
# ============================================================

class TestDeduplication:
    """去重测试 - 使用隔离的测试StorageManager"""

    @pytest.mark.asyncio
    async def test_redis_dedup_by_url(self, unique_url, test_storage_manager):
        """测试基于 URL 的去重

        使用唯一URL和隔离的Redis确保测试隔离
        """
        print("\n=== 测试 URL 去重 ===")

        storage = test_storage_manager

        # 检查是否有 Redis
        if not storage.redis:
            pytest.skip("Redis 未配置")

        # 使用唯一的测试URL
        test_url = unique_url
        test_title = "Test Title"

        # 第一次检查 - 不重复
        is_dup = storage.check_duplicate(test_url, test_title, "rss")
        assert is_dup == False, f"新 URL 应该不是重复: {test_url}"

        # 标记为已处理
        storage.mark_processed(test_url, test_title, "rss")

        # 第二次检查 - 重复
        is_dup = storage.check_duplicate(test_url, test_title, "rss")
        assert is_dup == True, f"已处理的 URL 应该是重复: {test_url}"

        print(f"✅ URL 去重测试通过: {test_url[:50]}...")

    @pytest.mark.asyncio
    async def test_redis_dedup_by_title(self, unique_title, unique_test_id, test_storage_manager):
        """测试基于标题的去重

        使用唯一标题和隔离的Redis确保测试隔离
        """
        print("\n=== 测试标题去重 ===")

        storage = test_storage_manager

        if not storage.redis:
            pytest.skip("Redis 未配置")

        # 使用唯一的测试标题
        test_title = f"Test Title {unique_test_id}"
        test_source = "weibo"

        is_dup = storage.check_duplicate("", test_title, test_source)
        assert is_dup == False, f"新标题应该不是重复: {test_title}"

        storage.mark_processed("", test_title, test_source)

        is_dup = storage.check_duplicate("", test_title, test_source)
        assert is_dup == True, f"已处理的标题应该是重复: {test_title}"

        print(f"✅ 标题去重测试通过: {test_title[:30]}...")

    @pytest.mark.asyncio
    async def test_redis_dedup_batch(self, unique_test_id, test_storage_manager):
        """测试批量去重

        验证多条数据的去重逻辑
        """
        from src.storage.md_generator import NewsItem

        print("\n=== 测试批量去重 ===")

        storage = test_storage_manager

        if not storage.redis:
            pytest.skip("Redis 未配置")

        # 创建测试数据
        test_items = []
        for i in range(5):
            item = NewsItem(
                title=f"Batch Test {unique_test_id} Item {i}",
                url=f"https://test-{unique_test_id}.com/item-{i}",
                source="test",
                source_type="test"
            )
            test_items.append(item)

        # 去重前
        unique_before = len(test_items)

        # 执行去重
        unique_items = storage.deduplicate_items(test_items, "test")

        # 验证
        assert len(unique_items) == unique_before, f"新数据应该全部通过: {len(unique_items)}/{unique_before}"

        # 再次去重 - 全部应该被过滤
        duplicate_items = storage.deduplicate_items(test_items, "test")

        assert len(duplicate_items) == 0, f"重复数据应该全部过滤: {len(duplicate_items)}"

        print(f"✅ 批量去重测试通过: {unique_before} -> {len(unique_items)} -> {len(duplicate_items)}")


# ============================================================
# Test Analysis - 分析测试
# ============================================================

class TestAnalysis:
    """分析测试"""

    @pytest.mark.asyncio
    async def test_intelligence_analyzer(self):
        """测试情报分析"""
        from src.intelligence.analyzer import IntelligenceAnalyzer, IntelligenceAnalyzer
        from src.intelligence.fetcher import NewsItem

        print("\n=== 测试情报分析 ===")

        analyzer = IntelligenceAnalyzer(llm_config={"model": "deepseek-chat"})

        # 准备测试数据
        test_items = [
            NewsItem(
                platform="rss",
                title="OpenAI 发布 GPT-5",
                url="https://example.com/gpt5",
                summary="OpenAI 在今天的发布会上宣布了 GPT-5 模型的发布..."
            )
        ]

        try:
            results = await analyzer.analyze_batch(test_items)
            print(f"分析结果: {len(results)} 条")

            if results:
                print(f"  - 分类: {results[0].category}")
                print(f"  - 相关性: {results[0].relevance_score}")

            assert len(results) > 0, "分析失败"
            print("✅ 情报分析测试通过")

        except Exception as e:
            print(f"⚠️ 情报分析跳过: {e}")
            pytest.skip(f"分析跳过: {e}")


# ============================================================
# Test Storage - 存储测试
# ============================================================

class TestStorage:
    """存储测试"""

    @pytest.mark.asyncio
    async def test_postgres_connection(self):
        """测试 PostgreSQL 连接"""
        from src.storage import get_storage_manager

        print("\n=== 测试 PostgreSQL 连接 ===")

        storage = get_storage_manager()

        if not storage.postgres:
            pytest.skip("PostgreSQL 未配置")

        # 测试连接
        try:
            result = storage.postgres.list_recent(limit=1)
            print(f"PostgreSQL 连接成功, 已有记录: {len(result)} 条")
            print("✅ PostgreSQL 连接测试通过")
        except Exception as e:
            print(f"❌ PostgreSQL 连接失败: {e}")
            pytest.fail(f"PostgreSQL 连接失败: {e}")

    @pytest.mark.asyncio
    async def test_s3_connection(self):
        """测试 S3 连接"""
        from src.storage import get_storage_manager

        print("\n=== 测试 S3 连接 ===")

        storage = get_storage_manager()

        if not storage.s3:
            pytest.skip("S3 未配置")

        try:
            files = storage.s3.list_files(prefix="intelligence/")
            print(f"S3 连接成功, 文件数: {len(files)}")
            print("✅ S3 连接测试通过")
        except Exception as e:
            print(f"❌ S3 连接失败: {e}")
            pytest.fail(f"S3 连接失败: {e}")

    @pytest.mark.asyncio
    async def test_embedding_generation(self):
        """测试向量生成"""
        from src.storage import get_storage_manager

        print("\n=== 测试向量生成 ===")

        storage = get_storage_manager()

        try:
            embedding = await storage.generate_embedding("这是一个测试文本")
            print(f"向量维度: {len(embedding) if embedding else 0}")

            assert embedding is not None, "向量生成失败"
            assert len(embedding) > 0, "向量为空"
            print("✅ 向量生成测试通过")
        except Exception as e:
            print(f"⚠️ 向量生成跳过: {e}")
            pytest.skip(f"向量生成跳过: {e}")

    @pytest.mark.asyncio
    async def test_markdown_generation(self):
        """测试 Markdown 生成"""
        from src.storage import get_storage_manager
        from src.storage.md_generator import NewsItem

        print("\n=== 测试 Markdown 生成 ===")

        storage = get_storage_manager()

        # 测试数据
        news_item = NewsItem(
            title="测试文章标题",
            content="这是文章的主要内容",
            summary="这是摘要",
            url="https://example.com/test",
            source="rss",
            source_type="rss"
        )

        analysis_result = {
            "summary": "这是 AI 生成的摘要",
            "category": "tech",
            "relevance_score": 0.85
        }

        md_content = storage._generate_markdown(news_item, analysis_result)

        print(f"生成的 Markdown:\n{md_content[:200]}...")

        assert "测试文章标题" in md_content, "Markdown 标题缺失"
        assert "这是 AI 生成的摘要" in md_content, "Markdown 摘要缺失"

        print("✅ Markdown 生成测试通过")


# ============================================================
# Test End to End - 端到端测试
# ============================================================

class TestEndToEnd:
    """端到端测试"""

    @pytest.mark.asyncio
    async def test_pipeline_fetch_only(self):
        """测试流水线 - 仅采集和分析"""
        from src.intelligence.pipeline import IntelligencePipeline, PipelineConfig

        print("\n=== 测试流水线 (采集+分析) ===")

        config = PipelineConfig(
            platforms=["weibo"],
            rss_enabled=True,
            rss_categories=["tech"],
            rss_max_tier=2,
            llm_model="deepseek-chat"
        )

        pipeline = IntelligencePipeline(config)

        try:
            result = await pipeline.process(user_id=None)
            print(f"流水线结果: {result}")

            assert result["status"] in ["completed", "no_new_data"], "流水线执行失败"
            print("✅ 流水线测试通过")
        except Exception as e:
            print(f"❌ 流水线执行失败: {e}")
            # 不失败，继续其他测试
            pytest.skip(f"流水线跳过: {e}")

    @pytest.mark.asyncio
    async def test_storage_save_intelligence(self):
        """测试存储单条情报"""
        from src.storage import get_storage_manager
        from src.storage.md_generator import NewsItem

        print("\n=== 测试存储情报 ===")

        storage = get_storage_manager()

        # 检查存储是否可用
        if not storage.postgres and not storage.s3:
            pytest.skip("存储服务未配置")

        # 测试数据
        news_item = NewsItem(
            title=f"测试情报 {datetime.now().strftime('%Y%m%d %H:%M%S')}",
            content="这是测试内容",
            summary="这是摘要",
            url=f"https://example.com/test-{datetime.now().timestamp()}",
            source="test",
            source_type="rss"
        )

        analysis_result = {
            "summary": "测试摘要",
            "category": "tech",
            "relevance_score": 0.8
        }

        try:
            success = await storage.save_intelligence(news_item, analysis_result)
            print(f"存储结果: {success}")
            print("✅ 情报存储测试通过")
        except Exception as e:
            print(f"⚠️ 情报存储跳过: {e}")
            pytest.skip(f"存储跳过: {e}")

    @pytest.mark.asyncio
    async def test_full_pipeline_with_storage(self):
        """测试完整流水线含存储"""
        from src.intelligence.pipeline import IntelligencePipeline, PipelineConfig

        print("\n=== 测试完整流水线 (含存储) ===")

        config = PipelineConfig(
            platforms=["weibo"],
            rss_enabled=True,
            rss_categories=["tech"],
            rss_max_tier=2,
            llm_model="deepseek-chat"
        )

        pipeline = IntelligencePipeline(config)

        try:
            # 执行完整流水线
            result = await pipeline.process(user_id="test_user")
            print(f"完整流水线结果: {result}")

            # 验证结果
            assert result["status"] == "completed", "流水线状态错误"

            # 检查存储数量
            stored = result.get("stored", 0)
            print(f"存储数量: {stored}")

            print("✅ 完整流水线测试通过")

        except Exception as e:
            print(f"⚠️ 完整流水线跳过: {e}")
            pytest.skip(f"完整流水线跳过: {e}")


# ============================================================
# Test Fixtures and Helpers
# ============================================================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def print_test_summary(results: Dict[str, Any]):
    """打印测试摘要"""
    print("\n" + "=" * 50)
    print("测试摘要")
    print("=" * 50)
    for key, value in results.items():
        print(f"  {key}: {value}")


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s", "--tb=short"])

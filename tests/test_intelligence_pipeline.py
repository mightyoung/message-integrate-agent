#!/usr/bin/env python3
# coding=utf-8
"""
Intelligence Pipeline Integration Test

执行全流程真实测试:
1. IntelligenceFetcher - 获取国内情报 (微博/知乎/B站)
2. IntelligenceAnalyzer - AI 分析 (使用 DeepSeek)
3. IntelligenceScorer - 用户匹配评分
4. IntelligencePusher - 推送测试

使用方式:
    python -m tests.test_intelligence_pipeline

环境变量 (从 .env 读取):
    OPENAI_API_KEY - DeepSeek API Key
    OPENAI_BASE_URL - API 基础地址
    DEFAULT_MODEL - 使用的模型
    FEISHU_WEBHOOK_URL - 飞书 Webhook (用于推送测试)
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)


class IntegrationTest:
    """集成测试类"""

    def __init__(self):
        self.results = {}
        self.config = self._load_config()

    def _load_config(self):
        """加载配置"""
        return {
            "openai_api_key": os.environ.get("OPENAI_API_KEY"),
            "openai_base_url": os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
            "default_model": os.environ.get("DEFAULT_MODEL", "deepseek-chat"),
            "feishu_webhook_url": os.environ.get("FEISHU_WEBHOOK_URL"),
            "tavily_api_key": os.environ.get("TAVILY_API_KEY"),
        }

    def print_config(self):
        """打印配置 (隐藏敏感信息)"""
        logger.info("=" * 60)
        logger.info("📋 测试配置:")
        logger.info(f"  - OPENAI_BASE_URL: {self.config['openai_base_url']}")
        logger.info(f"  - DEFAULT_MODEL: {self.config['default_model']}")
        logger.info(f"  - OPENAI_API_KEY: {self.config['openai_api_key'][:10]}..." if self.config['openai_api_key'] else "  - OPENAI_API_KEY: NOT SET")
        logger.info(f"  - FEISHU_WEBHOOK_URL: {'SET' if self.config['feishu_webhook_url'] else 'NOT SET'}")
        logger.info(f"  - TAVILY_API_KEY: {'SET' if self.config['tavily_api_key'] else 'NOT SET'}")
        logger.info("=" * 60)

    async def test_1_fetcher(self):
        """测试 1: IntelligenceFetcher - 获取国内情报"""
        logger.info("\n🧪 测试 1: IntelligenceFetcher - 情报获取")
        logger.info("-" * 40)

        try:
            from src.intelligence.fetcher import IntelligenceFetcher

            fetcher = IntelligenceFetcher()

            # 测试获取微博数据
            logger.info("📡 获取微博热点...")
            data, platform, status = fetcher.fetch_data("weibo")
            logger.info(f"  平台: {platform}, 状态: {status}")

            if data:
                items = fetcher._parse_data(data, platform)
                logger.info(f"  ✅ 获取到 {len(items)} 条微博热点")

                # 打印前3条
                for i, item in enumerate(items[:3], 1):
                    logger.info(f"    {i}. {item.title[:50]}...")
                self.results["fetcher"] = {"status": "PASS", "items": len(items)}
            else:
                logger.warning("  ⚠️ 未获取到数据")
                self.results["fetcher"] = {"status": "WARN", "items": 0}

        except Exception as e:
            logger.error(f"  ❌ 测试失败: {e}")
            self.results["fetcher"] = {"status": "FAIL", "error": str(e)}

    async def test_2_analyzer(self):
        """测试 2: IntelligenceAnalyzer - AI 分析"""
        logger.info("\n🧪 测试 2: IntelligenceAnalyzer - AI 分析")
        logger.info("-" * 40)

        if not self.config["openai_api_key"]:
            logger.warning("  ⏭️ 跳过: 未配置 OPENAI_API_KEY")
            self.results["analyzer"] = {"status": "SKIP"}
            return

        try:
            from src.intelligence.fetcher import NewsItem
            from src.intelligence.analyzer import IntelligenceAnalyzer

            analyzer = IntelligenceAnalyzer(llm_config={"model": self.config["default_model"]})

            # 创建测试新闻
            test_news = NewsItem(
                platform="test",
                title="OpenAI 发布 GPT-5 带来重大突破",
                url="https://example.com/gpt5",
                timestamp="2024-01-15",
            )

            logger.info(f"📝 分析新闻: {test_news.title[:30]}...")
            result = await analyzer.analyze(test_news)

            logger.info(f"  ✅ 分析完成:")
            logger.info(f"    - 相关性: {result.relevance_score}")
            logger.info(f"    - 重要性: {result.importance_score}")
            logger.info(f"    - 分类: {result.category}")
            logger.info(f"    - 摘要: {result.summary[:50]}...")
            logger.info(f"    - 关键词: {result.keywords}")

            self.results["analyzer"] = {
                "status": "PASS",
                "relevance": result.relevance_score,
                "importance": result.importance_score,
            }

        except Exception as e:
            logger.error(f"  ❌ 测试失败: {e}")
            self.results["analyzer"] = {"status": "FAIL", "error": str(e)}

    async def test_3_scorer(self):
        """测试 3: IntelligenceScorer - 用户匹配评分"""
        logger.info("\n🧪 测试 3: IntelligenceScorer - 用户匹配评分")
        logger.info("-" * 40)

        if not self.config["openai_api_key"]:
            logger.warning("  ⏭️ 跳过: 未配置 OPENAI_API_KEY")
            self.results["scorer"] = {"status": "SKIP"}
            return

        try:
            from src.intelligence.fetcher import NewsItem
            from src.intelligence.analyzer import AnalysisResult
            from src.intelligence.scorer import IntelligenceScorer, UserProfile

            scorer = IntelligenceScorer()

            # 注册测试用户
            test_user = UserProfile(
                user_id="test_user",
                interests=["AI", "科技", "大模型", "互联网"],
                preferred_categories=["AI突破", "产品发布", "行业动态"],
                notification_channels=["feishu"],
                notify_frequency="daily",
            )
            scorer.register_user(test_user)
            logger.info(f"  👤 注册测试用户: {test_user.user_id}")
            logger.info(f"    - 兴趣: {test_user.interests}")
            logger.info(f"    - 偏好分类: {test_user.preferred_categories}")

            # 创建测试数据
            news_items = [
                NewsItem(
                    platform="weibo",
                    title="OpenAI 发布 GPT-5 重大突破",
                    url="https://example.com/1",
                    timestamp="2024-01-15",
                ),
                NewsItem(
                    platform="zhihu",
                    title="如何在家做红烧肉",
                    url="https://example.com/2",
                    timestamp="2024-01-15",
                ),
            ]

            analysis_results = [
                AnalysisResult(
                    news_id="1",
                    relevance_score=0.9,
                    importance_score=0.8,
                    summary="AI领域重大突破",
                    category="AI突破",
                    keywords=["AI", "GPT-5", "OpenAI"],
                    sentiment="positive",
                ),
                AnalysisResult(
                    news_id="2",
                    relevance_score=0.1,
                    importance_score=0.3,
                    summary="美食教程",
                    category="生活",
                    keywords=["红烧肉", "烹饪"],
                    sentiment="neutral",
                ),
            ]

            # 评分
            logger.info("  📊 批量评分...")
            scored = await scorer.score_batch(news_items, analysis_results, "test_user", min_score=0.3)

            logger.info(f"  ✅ 评分完成: {len(scored)} 条通过阈值")
            for s in scored:
                logger.info(f"    - {s.news_item.title[:30]}... | 分数: {s.total_score:.2f}")

            self.results["scorer"] = {"status": "PASS", "scored": len(scored)}

        except Exception as e:
            logger.error(f"  ❌ 测试失败: {e}")
            self.results["scorer"] = {"status": "FAIL", "error": str(e)}

    async def test_4_worldmonitor_adapter(self):
        """测试 4: WorldMonitor Adapter"""
        logger.info("\n🧪 测试 4: WorldMonitor Adapter")
        logger.info("-" * 40)

        # 检查 WorldMonitor 配置
        worldmonitor_enabled = os.environ.get("WORLDMONITOR_ENABLED", "false").lower() == "true"
        worldmonitor_api_url = os.environ.get("WORLDMONITOR_API_URL", "")
        worldmonitor_api_key = os.environ.get("WORLDMONITOR_API_KEY", "")

        logger.info(f"  📍 WorldMonitor 状态: {'启用' if worldmonitor_enabled else '未启用'}")
        logger.info(f"  📍 API URL: {worldmonitor_api_url or '默认'}")
        logger.info(f"  📍 API Key: {'已配置' if worldmonitor_api_key else '未配置'}")

        if not worldmonitor_enabled:
            logger.warning("  ⏭️ 跳过: 未启用 WorldMonitor (设置 WORLDMONITOR_ENABLED=true)")
            self.results["worldmonitor"] = {"status": "SKIP"}
            return

        try:
            from src.intelligence.worldmonitor_adapter import WorldMonitorAdapter, WorldMonitorConfig

            config = WorldMonitorConfig(
                api_url=worldmonitor_api_url or "https://worldmonitor.app",
                api_key=worldmonitor_api_key,
                categories=["geopolitics", "tech"],
            )
            adapter = WorldMonitorAdapter(config)

            logger.info("  📡 获取 geopolitics 类别新闻...")
            items = await adapter.fetch_news("geopolitics", limit=5)
            logger.info(f"  ✅ 获取到 {len(items)} 条全球情报")

            self.results["worldmonitor"] = {"status": "PASS", "items": len(items)}

        except Exception as e:
            logger.error(f"  ❌ 测试失败: {e}")
            self.results["worldmonitor"] = {"status": "FAIL", "error": str(e)}

    async def test_5_full_pipeline(self):
        """测试 5: 完整流水线"""
        logger.info("\n🧪 测试 5: 完整 IntelligencePipeline")
        logger.info("-" * 40)

        if not self.config["openai_api_key"]:
            logger.warning("  ⏭️ 跳过: 未配置 OPENAI_API_KEY")
            self.results["pipeline"] = {"status": "SKIP"}
            return

        try:
            from src.intelligence.pipeline import IntelligencePipeline, PipelineConfig

            # 创建流水线配置
            config = PipelineConfig(
                platforms=["weibo", "zhihu"],
                llm_model=self.config["default_model"],
                worldmonitor_enabled=False,  # 暂时禁用 WorldMonitor
                default_channels=["feishu"],
                min_score_threshold=0.3,
            )

            pipeline = IntelligencePipeline(config=config)

            # 注册测试用户
            from src.intelligence.scorer import UserProfile
            pipeline.register_user(
                UserProfile(
                    user_id="test_user",
                    interests=["AI", "科技", "大模型"],
                    preferred_categories=["AI突破", "产品发布"],
                    notification_channels=["feishu"],
                    notify_frequency="daily",
                )
            )

            # 执行流水线
            logger.info("  🚀 执行完整流水线...")
            result = await pipeline.process(user_id="test_user")

            logger.info(f"  ✅ 流水线执行完成:")
            logger.info(f"    - 获取: {result.get('fetched', 0)} 条")
            logger.info(f"    - 分析: {result.get('analyzed', 0)} 条")
            logger.info(f"    - 评分: {result.get('scored', 0)} 条")
            logger.info(f"    - 推送: {result.get('pushed', 0)} 条")

            if result.get("top_items"):
                logger.info("  📊 Top 5 情报:")
                for item in result["top_items"]:
                    logger.info(f"    - {item['title'][:40]}... | {item['score']:.2f}")

            self.results["pipeline"] = {"status": "PASS", "result": result}

        except Exception as e:
            logger.error(f"  ❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            self.results["pipeline"] = {"status": "FAIL", "error": str(e)}

    async def test_6_push_service(self):
        """测试 6: 推送服务 (飞书)"""
        logger.info("\n🧪 测试 6: 推送服务 (飞书)")
        logger.info("-" * 40)

        if not self.config["feishu_webhook_url"]:
            logger.warning("  ⏭️ 跳过: 未配置 FEISHU_WEBHOOK_URL")
            self.results["push"] = {"status": "SKIP"}
            return

        try:
            import httpx

            # 发送测试消息 - 使用正确的飞书卡片格式
            test_message = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "🧪 测试消息"
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": "Intelligence Pipeline 集成测试"
                        }
                    ]
                }
            }

            logger.info(f"  📤 发送测试消息到飞书...")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.config["feishu_webhook_url"],
                    json=test_message,
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        logger.info(f"  ✅ 推送成功! MsgId: {result.get('msg_id')}")
                        self.results["push"] = {"status": "PASS"}
                    else:
                        logger.warning(f"  ⚠️ 推送返回错误: {result}")
                        self.results["push"] = {"status": "WARN", "detail": result}
                else:
                    logger.error(f"  ❌ HTTP 错误: {response.status_code}")
                    self.results["push"] = {"status": "FAIL", "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"  ❌ 测试失败: {e}")
            self.results["push"] = {"status": "FAIL", "error": str(e)}

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("\n" + "=" * 60)
        logger.info("🚀 Intelligence Pipeline 集成测试开始")
        logger.info("=" * 60)

        self.print_config()

        # 执行所有测试
        await self.test_1_fetcher()
        await self.test_2_analyzer()
        await self.test_3_scorer()
        await self.test_4_worldmonitor_adapter()
        await self.test_5_full_pipeline()
        await self.test_6_push_service()

        # 打印测试结果汇总
        self.print_summary()

    def print_summary(self):
        """打印测试结果汇总"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 测试结果汇总")
        logger.info("=" * 60)

        passed = 0
        failed = 0
        skipped = 0

        for name, result in self.results.items():
            status = result.get("status", "UNKNOWN")
            status_icon = {
                "PASS": "✅",
                "FAIL": "❌",
                "SKIP": "⏭️",
                "WARN": "⚠️",
            }.get(status, "❓")

            logger.info(f"  {status_icon} {name}: {status}")
            if status == "PASS":
                passed += 1
            elif status == "FAIL":
                failed += 1
            else:
                skipped += 1

        logger.info("-" * 40)
        logger.info(f"  总计: {len(self.results)} | 通过: {passed} | 失败: {failed} | 跳过: {skipped}")
        logger.info("=" * 60)


async def main():
    """主函数"""
    test = IntegrationTest()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

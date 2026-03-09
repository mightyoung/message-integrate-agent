# coding=utf-8
"""
Intelligence Pipeline - 情报处理流水线

整合情报获取、分析、评分、推送的全流程:

获取 → 分析 → 评分 → 推送

支持多数据源:
- IntelligenceFetcher: 国内平台 (微博/知乎/哔哩哔哩)
- RSSFetcher: 全球 RSS 源 (路透/BBC/彭博等) - 基于 WorldMonitor
- WorldMonitor: 全球新闻源 (需要自托管)

参考: Microsoft Azure Intelligence Pipeline
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from .fetcher import IntelligenceFetcher, NewsItem
from .analyzer import IntelligenceAnalyzer, AnalysisResult
from .scorer import IntelligenceScorer, ScoredIntelligence, UserProfile
from .pusher import IntelligencePusher, PushRequest


@dataclass
class PipelineConfig:
    """流水线配置"""

    # 获取配置
    platforms: List[str] = field(default_factory=lambda: ["weibo", "zhihu", "bilibili"])
    proxy_url: Optional[str] = None

    # RSS Fetcher 配置 (基于 WorldMonitor)
    rss_enabled: bool = True
    rss_categories: List[str] = field(default_factory=lambda: ["geopolitics", "military", "tech"])
    rss_lang: str = "en"
    rss_max_tier: int = 2  # 1=通讯社, 2=主流媒体, 3=专业来源

    # WorldMonitor 配置 (可选,需要自托管)
    worldmonitor_enabled: bool = False
    worldmonitor_api_url: str = "https://worldmonitor.app"
    worldmonitor_api_key: str = ""
    worldmonitor_categories: List[str] = field(default_factory=lambda: ["geopolitics", "military", "economy", "tech"])

    # 分析配置
    llm_model: str = "deepseek-chat"

    # 评分配置
    min_score_threshold: float = 0.5

    # 推送配置
    default_channels: List[str] = field(default_factory=lambda: ["feishu"])


class IntelligencePipeline:
    """情报处理流水线

    完整流程:
    1. IntelligenceFetcher: 获取情报 (国内平台: 微博/知乎/B站)
    2. RSSFetcher: 获取情报 (全球 RSS: 路透/BBC/彭博等)
    3. WorldMonitorAdapter: 获取情报 (全球源,需要自托管)
    4. IntelligenceAnalyzer: AI 分析
    5. IntelligenceScorer: 用户匹配评分
    6. IntelligencePusher: 推送给用户
    """

    def __init__(self, config: Optional[Any] = None):
        """初始化流水线

        Args:
            config: 流水线配置，可以是 PipelineConfig 或字典
        """
        # 支持字典或 PipelineConfig
        if config is None:
            self.config = PipelineConfig()
        elif isinstance(config, dict):
            # 从字典创建 PipelineConfig，并保存额外属性
            self.config = PipelineConfig(
                platforms=config.get("platforms", ["weibo", "zhihu", "bilibili"]),
                proxy_url=config.get("proxy_url"),
                rss_enabled=config.get("rss_enabled", True),
                rss_categories=config.get("rss_categories", ["geopolitics", "military", "tech"]),
                rss_lang=config.get("rss_lang", "en"),
                rss_max_tier=config.get("rss_max_tier", 2),
            )
            # 保存字典中额外的属性
            self.config.llm_model = config.get("llm_model", "deepseek-chat")
            self.config.worldmonitor_enabled = config.get("worldmonitor_enabled", False)
            self.config.worldmonitor_api_url = config.get("worldmonitor_api_url")
            self.config.worldmonitor_api_key = config.get("worldmonitor_api_key")
            self.config.worldmonitor_categories = config.get("worldmonitor_categories", ["geopolitics", "military", "economy", "tech"])
            self.config.default_channels = config.get("default_channels", ["feishu"])
            self.config.min_score_threshold = config.get("min_score_threshold", 0.5)
        else:
            self.config = config

        # 初始化各组件
        self.fetcher = IntelligenceFetcher(
            proxy_url=self.config.proxy_url,
        )

        # RSS Fetcher (基于 WorldMonitor)
        self.rss_fetcher = None
        if self.config.rss_enabled:
            try:
                from .rss_fetcher import RSSFetcher
                self.rss_fetcher = RSSFetcher(proxy_url=self.config.proxy_url)
                logger.info(f"📰 RSS Fetcher 启用: {self.config.rss_categories}, lang={self.config.rss_lang}, tier≤{self.config.rss_max_tier}")
            except Exception as e:
                logger.warning(f"RSS Fetcher 初始化失败: {e}")

        self.analyzer = IntelligenceAnalyzer(
            llm_config={"model": self.config.llm_model},
        )
        self.scorer = IntelligenceScorer()
        self.pusher = IntelligencePusher()

        # WorldMonitor 适配器 (可选,需要自托管)
        self.worldmonitor_adapter = None
        if self.config.worldmonitor_enabled:
            from .worldmonitor_adapter import create_worldmonitor_adapter
            self.worldmonitor_adapter = create_worldmonitor_adapter(
                api_url=self.config.worldmonitor_api_url,
                api_key=self.config.worldmonitor_api_key,
                categories=self.config.worldmonitor_categories,
            )
            logger.info("🌍 WorldMonitor 适配器已启用")

        logger.info("IntelligencePipeline 初始化完成")

    def register_user(self, profile: UserProfile):
        """注册用户

        Args:
            profile: 用户画像
        """
        self.scorer.register_user(profile)

    async def process(
        self,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行完整流水线

        Args:
            user_id: 目标用户 ID (可选)

        Returns:
            Dict: 处理结果统计
        """
        logger.info(f"开始处理情报流水线 (user_id={user_id})")

        # Step 1: 获取情报
        news_items = await self._fetch_intelligence()
        if not news_items:
            return {"status": "no_data", "fetched": 0}

        # Step 2: 分析情报
        analysis_results = await self._analyze_intelligence(news_items)

        # Step 3: 评分
        if user_id:
            scored_items = await self._score_intelligence(
                news_items, analysis_results, user_id
            )
        else:
            # 无用户，返回所有
            scored_items = [
                ScoredIntelligence(
                    news_item=item,
                    analysis_result=result,
                    total_score=result.relevance_score,
                    match_reasons=[],
                )
                for item, result in zip(news_items, analysis_results)
            ]

        # Step 4: 推送
        if user_id and scored_items:
            push_results = await self._push_intelligence(scored_items, user_id)
        else:
            push_results = []

        # 返回统计
        return {
            "status": "completed",
            "fetched": len(news_items),
            "analyzed": len(analysis_results),
            "scored": len(scored_items),
            "pushed": len(push_results),
            "top_items": [
                {
                    "title": s.news_item.title[:50],
                    "score": s.total_score,
                    "category": s.analysis_result.category,
                }
                for s in scored_items[:5]
            ],
        }

    async def _fetch_intelligence(self) -> List[NewsItem]:
        """获取情报

        从多个来源获取:
        1. IntelligenceFetcher: 国内平台 (微博/知乎/哔哩哔哩)
        2. RSSFetcher: 全球 RSS 源 (路透/BBC/彭博等)
        3. WorldMonitor: 全球新闻源 (可选,需要自托管)

        Returns:
            List[NewsItem]: 新闻列表
        """
        platforms = self.config.platforms or ["weibo"]
        all_items = []

        try:
            # 1. 获取国内平台情报
            news_items = self.fetcher.fetch_multiple(platforms)
            all_items.extend(news_items)
            logger.info(f"📥 获取国内情报: {len(news_items)} 条")

        except Exception as e:
            logger.error(f"获取国内情报失败: {e}")

        # 2. 获取全球 RSS 情报 (基于 WorldMonitor)
        if self.rss_fetcher:
            try:
                rss_items = self.rss_fetcher.fetch_multiple(
                    categories=self.config.rss_categories,
                    lang=self.config.rss_lang,
                    max_tier=self.config.rss_max_tier,
                )
                # 转换为 NewsItem
                for rss_item in rss_items:
                    news_item = NewsItem(
                        platform=f"rss:{rss_item.source.lower().replace(' ', '_')}",
                        title=rss_item.title,
                        url=rss_item.link,
                        timestamp=rss_item.pub_date.isoformat() if rss_item.pub_date else "",
                        summary=rss_item.description,
                    )
                    all_items.append(news_item)
                logger.info(f"📰 获取 RSS 情报: {len(rss_items)} 条")
            except Exception as e:
                logger.error(f"获取 RSS 情报失败: {e}")

        # 3. 获取 WorldMonitor 全球情报 (可选,需要自托管)
        if self.worldmonitor_adapter:
            try:
                wm_items = await self.worldmonitor_adapter.fetch_multiple_categories(
                    categories=self.config.worldmonitor_categories or ["geopolitics", "military"],
                    limit_per_category=20
                )
                all_items.extend(wm_items)
                logger.info(f"🌍 获取全球情报: {len(wm_items)} 条")
            except Exception as e:
                logger.error(f"获取 WorldMonitor 情报失败: {e}")

        # 按时间排序
        all_items.sort(key=lambda x: x.timestamp, reverse=True)

        logger.info(f"✅ 共获取 {len(all_items)} 条情报")
        return all_items

    async def _analyze_intelligence(
        self,
        news_items: List[NewsItem],
    ) -> List[AnalysisResult]:
        """分析情报

        Args:
            news_items: 新闻列表

        Returns:
            List[AnalysisResult]: 分析结果列表
        """
        try:
            results = await self.analyzer.analyze_batch(news_items)
            logger.info(f"分析完成: {len(results)} 条")
            return results
        except Exception as e:
            logger.error(f"分析情报失败: {e}")
            # 返回默认结果
            return [
                self.analyzer._default_result(item)
                for item in news_items
            ]

    async def _score_intelligence(
        self,
        news_items: List[NewsItem],
        analysis_results: List[AnalysisResult],
        user_id: str,
    ) -> List[ScoredIntelligence]:
        """评分情报

        Args:
            news_items: 新闻列表
            analysis_results: 分析结果
            user_id: 用户 ID

        Returns:
            List[ScoredIntelligence]: 评分后的情报
        """
        try:
            scored = await self.scorer.score_batch(
                news_items,
                analysis_results,
                user_id,
                min_score=self.config.min_score_threshold,
            )
            logger.info(f"评分完成: {len(scored)} 条通过阈值")
            return scored
        except Exception as e:
            logger.error(f"评分失败: {e}")
            return []

    async def _push_intelligence(
        self,
        scored_items: List[ScoredIntelligence],
        user_id: str,
    ) -> List:
        """推送情报

        Args:
            scored_items: 评分后的情报
            user_id: 用户 ID

        Returns:
            List: 推送结果
        """
        if not scored_items:
            return []

        # 构建推送内容
        top_items = scored_items[:5]  # 推送 Top 5

        content_parts = ["📊 今日热点情报\n\n"]
        for i, item in enumerate(top_items, 1):
            content_parts.append(
                f"{i}. {item.news_item.title[:60]}...\n"
            )
            content_parts.append(
                f"   🏷️ {item.analysis_result.category} | "
                f"⭐ {item.total_score:.2f}\n"
            )
            if item.match_reasons:
                content_parts.append(f"   💡 {item.match_reasons[0]}\n")
            content_parts.append("\n")

        content = "".join(content_parts)

        # 创建推送请求
        request = PushRequest(
            user_id=user_id,
            title="🔥 今日热点情报",
            content=content,
            channels=self.config.default_channels or ["feishu"],
            metadata={"source": "intelligence_pipeline"},
        )

        # 执行推送
        try:
            results = await self.pusher.push(request)
            logger.info(f"推送完成: {len(results)} 个渠道")
            return results
        except Exception as e:
            logger.error(f"推送失败: {e}")
            return []

    async def get_news_for_user(
        self,
        user_id: str,
        platforms: Optional[List[str]] = None,
    ) -> List[ScoredIntelligence]:
        """为用户获取个性化情报

        Args:
            user_id: 用户 ID
            platforms: 指定平台 (可选)

        Returns:
            List[ScoredIntelligence]: 个性化情报列表
        """
        # 设置平台
        if platforms:
            original_platforms = self.config.platforms
            self.config.platforms = platforms

        try:
            # 获取
            news_items = await self._fetch_intelligence()

            # 分析
            analysis_results = await self._analyze_intelligence(news_items)

            # 评分
            scored = await self._score_intelligence(
                news_items, analysis_results, user_id
            )

            return scored

        finally:
            # 恢复平台设置
            if platforms:
                self.config.platforms = original_platforms


# ==================== 便捷函数 ====================


def create_intelligence_pipeline(
    platforms: Optional[List[str]] = None,
    llm_model: str = "deepseek-chat",
    channels: Optional[List[str]] = None,
) -> IntelligencePipeline:
    """创建情报流水线

    Args:
        platforms: 要获取的平台列表
        llm_model: LLM 模型
        channels: 推送渠道

    Returns:
        IntelligencePipeline: 流水线实例
    """
    config = PipelineConfig(
        platforms=platforms,
        llm_model=llm_model,
        default_channels=channels or ["feishu"],
    )
    return IntelligencePipeline(config=config)

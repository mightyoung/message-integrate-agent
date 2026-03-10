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
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .fetcher import IntelligenceFetcher, NewsItem as FetcherNewsItem
from .analyzer import IntelligenceAnalyzer, AnalysisResult
from .scorer import IntelligenceScorer, ScoredIntelligence, UserProfile
from .pusher import IntelligencePusher, PushRequest
from .translator import get_translator
from .firecrawl_adapter import get_firecrawl_adapter, FirecrawlAdapter
from src.storage import get_storage_manager
from src.storage.md_generator import NewsItem as StorageNewsItem

# 飞书消息限制配置
FEISHU_MAX_MESSAGE_SIZE = 15000  # 飞书消息最大字节数（保留余量）
FEISHU_MAX_MESSAGES = 5  # 单次推送最大消息数（避免刷屏）
FEISHU_SUMMARY_LENGTH_THRESHOLD = 300  # 超过此长度将单独发送摘要


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

    # Firecrawl 配置 (云服务)
    firecrawl_enabled: bool = False
    firecrawl_api_key: Optional[str] = None
    firecrawl_max_urls: int = 5  # 最多抓取 URL 数量

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
            self.config.firecrawl_enabled = config.get("firecrawl_enabled", False)
            self.config.firecrawl_api_key = config.get("firecrawl_api_key")
            self.config.firecrawl_max_urls = config.get("firecrawl_max_urls", 5)
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

        # 存储管理器 (PostgreSQL + S3 + Redis)
        self.storage = get_storage_manager()

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

        # Firecrawl 适配器 (云服务)
        self.firecrawl_adapter = None
        if self.config.firecrawl_enabled:
            try:
                self.firecrawl_adapter = get_firecrawl_adapter(
                    api_key=self.config.firecrawl_api_key,
                )
                logger.info(f"🔥 Firecrawl 启用: 最多抓取 {self.config.firecrawl_max_urls} 个 URL")
            except Exception as e:
                logger.warning(f"Firecrawl 初始化失败: {e}")

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

        # Step 1.5: Firecrawl 扩展内容 (可选)
        if self.firecrawl_adapter and self.config.firecrawl_enabled:
            news_items = await self._expand_with_firecrawl(news_items)

        # Step 1.6: 去重 (按来源) - 如果有storage则去重
        if self.storage:
            news_items = await self._deduplicate_intelligence(news_items)
            if not news_items:
                return {"status": "no_new_data", "fetched": 0}

        # Step 2: 分析情报
        analysis_results = await self._analyze_intelligence(news_items)

        # Step 2.5: 存储情报 (实时存储) - 如果有storage则存储
        stored_count = 0
        if self.storage:
            stored_count = await self._store_intelligence(news_items, analysis_results)

        # Step 3: 评分
        if user_id:
            scored_items = await self._score_intelligence(
                news_items, analysis_results, user_id
            )
        else:
            # 无用户，返回所有 (添加情报ID)
            scored_items = [
                ScoredIntelligence(
                    intelligence_id=self._generate_intelligence_id(item, i),
                    news_item=item,
                    analysis_result=result,
                    total_score=result.relevance_score,
                    match_reasons=[],
                )
                for i, (item, result) in enumerate(zip(news_items, analysis_results))
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
            "stored": stored_count,
            "scored": len(scored_items),
            "pushed": len(push_results),
            "top_items": [
                {
                    "intelligence_id": s.intelligence_id,
                    "title": s.news_item.title[:50],
                    "score": s.total_score,
                    "category": s.analysis_result.category,
                    "url": getattr(s.news_item, 'url', '') or '',
                    "summary": s.analysis_result.summary[:100] if hasattr(s.analysis_result, 'summary') and s.analysis_result.summary else (getattr(s.news_item, 'summary', '') or '')[:100],
                }
                for s in scored_items[:5]
            ],
        }

    async def _expand_with_firecrawl(
        self,
        news_items: List[FetcherNewsItem],
    ) -> List[FetcherNewsItem]:
        """使用 Firecrawl 扩展情报内容

        Args:
            news_items: 原始情报列表

        Returns:
            List[FetcherNewsItem]: 扩展后的情报列表
        """
        if not news_items or not self.firecrawl_adapter:
            return news_items

        try:
            # 获取需要抓取的 URLs（选择评分最高的）
            urls_to_scrape = []
            for item in news_items[:self.config.firecrawl_max_urls]:
                url = getattr(item, 'url', '')
                if url and url.startswith('http'):
                    urls_to_scrape.append(url)

            if not urls_to_scrape:
                logger.info("[Firecrawl] 无有效 URL 需要抓取")
                return news_items

            logger.info(f"[Firecrawl] 开始抓取 {len(urls_to_scrape)} 个 URL")

            # 批量抓取
            results = await self.firecrawl_adapter.scrape_urls(urls_to_scrape)

            # 更新情报内容
            url_result_map = {r.url: r for r in results if r.success}

            for item in news_items:
                url = getattr(item, 'url', '')
                if url in url_result_map:
                    result = url_result_map[url]
                    # 更新内容
                    item.content = result.markdown
                    # 更新摘要（如果原摘要为空）
                    if not item.summary and result.markdown:
                        item.summary = result.markdown[:500]

            success_count = len(url_result_map)
            logger.info(f"[Firecrawl] 抓取完成: {success_count}/{len(urls_to_scrape)} 成功")

        except Exception as e:
            logger.error(f"[Firecrawl] 扩展失败: {e}")

        return news_items

    async def _fetch_intelligence(self) -> List[FetcherNewsItem]:
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
                    news_item = FetcherNewsItem(
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

    async def _deduplicate_intelligence(
        self,
        news_items: List[FetcherNewsItem],
    ) -> List[FetcherNewsItem]:
        """去重情报

        使用 Redis 对情报进行去重:
        - 基于 URL 去重
        - 基于 (标题 + 来源) 去重

        Args:
            news_items: 原始情报列表

        Returns:
            List[FetcherNewsItem]: 去重后的情报列表
        """
        if not news_items:
            return []

        # 按来源分组去重
        source_groups: Dict[str, List[FetcherNewsItem]] = {}
        for item in news_items:
            # 使用 platform 作为来源标识
            source = item.platform or "unknown"
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(item)

        # 对每个来源进行去重
        deduplicated = []
        for source, items in source_groups.items():
            unique_items = self.storage.deduplicate_items(items, source)
            deduplicated.extend(unique_items)

        logger.info(f"去重完成: {len(news_items)} -> {len(deduplicated)}")
        return deduplicated

    async def _store_intelligence(
        self,
        news_items: List[FetcherNewsItem],
        analysis_results: List[AnalysisResult],
    ) -> int:
        """存储情报到数据库和 S3

        Args:
            news_items: 新闻列表
            analysis_results: 分析结果列表

        Returns:
            int: 成功存储的数量
        """
        if not news_items or not analysis_results:
            return 0

        stored_count = 0
        for item, result in zip(news_items, analysis_results):
            try:
                # 转换为存储层需要的 NewsItem 格式
                # 从 fetcher 的 NewsItem (platform, url, timestamp, summary)
                # 转换为存储的 NewsItem (title, content, url, source_type, etc.)
                md_item = StorageNewsItem(
                    title=item.title,
                    content=getattr(item, 'content', "") or getattr(item, 'summary', "") or "",
                    summary=getattr(item, 'summary', "") or "",
                    url=item.url or "",
                    source=getattr(item, 'platform', '') or "",
                    source_type=getattr(item, 'source_type', 'rss') or "rss",
                    published_at=getattr(item, 'timestamp', None),
                    quality_score=getattr(item, 'quality_score', 0) or 0,
                    metadata=getattr(item, 'metadata', None),
                )

                # 转换为分析结果字典
                analysis_dict = {
                    "summary": result.summary if hasattr(result, 'summary') else "",
                    "category": result.category if hasattr(result, 'category') else "unknown",
                    "relevance_score": result.relevance_score if hasattr(result, 'relevance_score') else 0,
                    "key_points": result.key_points if hasattr(result, 'key_points') else [],
                }

                # 存储
                success = await self.storage.save_intelligence(md_item, analysis_dict)
                if success:
                    stored_count += 1

            except Exception as e:
                logger.error(f"存储情报失败: {e}")
                continue

        logger.info(f"存储完成: {stored_count}/{len(news_items)} 条")
        return stored_count

    async def _analyze_intelligence(
        self,
        news_items: List[FetcherNewsItem],
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
        news_items: List[FetcherNewsItem],
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

    def _generate_intelligence_id(self, news_item, index: int) -> str:
        """生成情报唯一ID

        Args:
            news_item: 新闻条目
            index: 索引

        Returns:
            str: 情报ID
        """
        url = getattr(news_item, 'url', '') or ''
        timestamp = getattr(news_item, 'timestamp', '') or ''
        return f"int_{abs(hash(url + timestamp)) % 1000000:06d}"

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

        # 准备翻译：收集标题和概要
        titles_to_translate = []
        summaries_to_translate = []
        item_data = []

        for item in top_items:
            # 获取标题
            title = item.news_item.title[:80] if len(item.news_item.title) > 80 else item.news_item.title
            titles_to_translate.append(title)

            # 获取概要
            summary = ""
            if hasattr(item.analysis_result, 'summary') and item.analysis_result.summary:
                summary = item.analysis_result.summary
            elif hasattr(item.news_item, 'summary') and item.news_item.summary:
                summary = item.news_item.summary
            elif hasattr(item.news_item, 'content') and item.news_item.content:
                summary = item.news_item.content

            if summary:
                summary = summary[:150].replace('\n', ' ').strip()
            summaries_to_translate.append(summary)

            item_data.append({
                "item": item,
                "url": getattr(item.news_item, 'url', '') or '',
            })

        # 生成标题和概要（根据内容类型选择提示词）
        # 顶级新闻编辑风格 或 顶级科学家风格
        translator = get_translator(model=self.config.llm_model)

        # 按内容类型分组处理
        news_items_to_translate = []
        paper_items_to_translate = []
        github_items_to_translate = []
        item_types = []  # 记录每个 item 对应的类型: 'paper', 'github', 'news'

        for i, data in enumerate(item_data):
            item = data["item"]
            category = getattr(item.analysis_result, 'category', None)

            # 检查来源是否为 GitHub
            source = getattr(item.news_item, 'source', '') or ''
            is_github = 'github' in source.lower()

            # 检查是否为学术论文类别
            is_paper = category and hasattr(category, 'value') and category.value == 'paper'

            if is_github:
                github_items_to_translate.append(i)
                item_types.append('github')
            elif is_paper:
                paper_items_to_translate.append(i)
                item_types.append('paper')
            else:
                news_items_to_translate.append(i)
                item_types.append('news')

        # 并行生成标题和概要
        title_tasks = []
        summary_tasks = []

        for i in range(len(item_data)):
            text_for_title = titles_to_translate[i]
            text_for_summary = summaries_to_translate[i]
            item_type = item_types[i]

            if item_type == 'github':
                # GitHub 仓库：使用顶级开源工程师风格
                title_tasks.append(translator.generate_github_title(text_for_title, max_length=30))
                summary_tasks.append(translator.generate_github_summary(text_for_summary, max_length=150))
            elif item_type == 'paper':
                # 学术论文：使用顶级科学家风格
                title_tasks.append(translator.generate_academic_title(text_for_title, max_length=30))
                summary_tasks.append(translator.generate_academic_summary(text_for_summary, max_length=150))
            else:
                # 新闻：使用顶级新闻编辑风格
                title_tasks.append(translator.generate_news_title(text_for_title, max_length=30))
                summary_tasks.append(translator.generate_news_summary(text_for_summary, max_length=150))

        translated_titles = await asyncio.gather(*title_tasks)
        translated_summaries = await asyncio.gather(*summary_tasks)

        # 动态消息限制逻辑
        # 根据飞书开发者文档：消息体最大约20KB，单次推送消息数不宜过多
        messages_to_send = []  # [(title, content, metadata), ...]

        # 构建主消息内容
        content_parts = ["📊 今日热点情报\n\n"]
        current_size = 0
        item_count = 0
        max_items = len(item_data)

        for i, data in enumerate(item_data):
            item = data["item"]
            int_id = item.intelligence_id or f"#{i+1}"
            title = translated_titles[i] if i < len(translated_titles) else item.news_item.title
            summary = translated_summaries[i] if i < len(translated_summaries) else ""
            url = data["url"]

            # 判断内容类型
            category = getattr(item.analysis_result, 'category', None)
            source = getattr(item.news_item, 'source', '') or ''
            is_github = 'github' in source.lower()
            is_paper = category and hasattr(category, 'value') and category.value == 'paper'

            if is_github:
                type_emoji = "💻"
                type_label = "开源"
                # 获取 stars 数量
                stars = getattr(item.news_item, 'score', 0) or 0
            elif is_paper:
                type_emoji = "📚"
                type_label = "论文"
                stars = 0
            else:
                type_emoji = "📰"
                type_label = "新闻"
                stars = 0

            # 获取发布时间
            timestamp = getattr(item.news_item, 'timestamp', None)
            if timestamp:
                try:
                    from datetime import datetime
                    if isinstance(timestamp, str):
                        # 处理 ISO 格式
                        ts = timestamp[:10] if len(timestamp) >= 10 else timestamp
                    else:
                        ts = timestamp.strftime('%Y-%m-%d') if hasattr(timestamp, 'strftime') else str(timestamp)
                except:
                    ts = str(timestamp)[:10]
            else:
                ts = ""

            # 估算此项内容大小
            item_content = f"{i+1}. {title}\n"
            if summary:
                item_content += f"   📝 {summary}\n"
            if ts:
                item_content += f"   📅 {ts}\n"
            # GitHub 仓库显示 stars 数量，其他显示评分
            if is_github and stars > 0:
                item_content += f"   {type_emoji} {type_label} | ⭐ {stars:,} ⭐ | ID: {int_id}\n"
            else:
                item_content += f"   {type_emoji} {type_label} | ⭐ {item.total_score:.2f} | ID: {int_id}\n"
            if url:
                item_content += f"   🔗 {url}\n"
            item_size = len(item_content.encode('utf-8'))

            # 检查是否超过消息大小限制
            if current_size + item_size > FEISHU_MAX_MESSAGE_SIZE:
                # 当前消息已满，添加到待发送列表
                messages_to_send.append(("🔥 今日热点情报", "".join(content_parts), "intelligence_pipeline"))
                # 开始新消息
                content_parts = ["📊 今日热点情报（续）\n\n"]
                current_size = 0

            content_parts.append(item_content)
            current_size += item_size
            item_count += 1

            # 动态调整：长概要单独发送
            if summary and len(summary) > FEISHU_SUMMARY_LENGTH_THRESHOLD:
                detail_content = f"""📰 情报{int_id} 详细摘要

{title}

{summary}

🔗 原文链接: {url}
"""
                # 检查是否还能发送更多消息
                if len(messages_to_send) < FEISHU_MAX_MESSAGES - 1:
                    messages_to_send.append((f"📰 情报{int_id} 详细摘要", detail_content, "intelligence_pipeline_detail"))
                    logger.info(f"长摘要单独发送: 情报{int_id} ({len(summary)}字)")

        # 添加反馈指引到最后一条主消息
        content_parts.append("━" * 20 + "\n")
        content_parts.append("💬 回复评价格式:\n")
        content_parts.append("  👍/👎 + 情报ID (如: 👍 int_123456)\n")
        content_parts.append("  或回复: 好/差 + 编号 (如: 好 1)\n")

        # 添加最后一条消息
        messages_to_send.append(("🔥 今日热点情报", "".join(content_parts), "intelligence_pipeline"))

        # 限制总消息数
        if len(messages_to_send) > FEISHU_MAX_MESSAGES:
            logger.warning(f"消息数({len(messages_to_send)})超过限制({FEISHU_MAX_MESSAGES})，将只发送前{FEISHU_MAX_MESSAGES}条")
            messages_to_send = messages_to_send[:FEISHU_MAX_MESSAGES]

        # 执行推送
        results = []
        try:
            for title, content, metadata_source in messages_to_send:
                request = PushRequest(
                    user_id=user_id,
                    title=title,
                    content=content,
                    channels=self.config.default_channels or ["feishu"],
                    metadata={"source": metadata_source},
                )
                push_result = await self.pusher.push(request)
                results.extend(push_result)
                logger.info(f"推送消息: {title}, 大小: {len(content.encode('utf-8'))} bytes")

            logger.info(f"推送完成: 共{len(messages_to_send)}条消息")
        except Exception as e:
            logger.error(f"推送失败: {e}")

        return results

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

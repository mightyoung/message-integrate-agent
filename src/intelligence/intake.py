# coding=utf-8
"""
Information Intake - 统一信息获取入口

整合热榜、新闻(RSS)、学术论文、智能搜索(Tavily) 的统一接口

设计原则:
- Tier 1: 热榜直接获取 (无代理)
- Tier 2: RSS 新闻订阅 (已有)
- Tier 3: 学术论文 (无代理)
- Tier 4: Tavily 智能搜索 (仅补充)
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .classifier import InfoCategory, InformationClassifier, get_classifier
from .hot_fetcher import HotFetcher, create_hot_fetcher
from .rss_fetcher import RSSFetcher, create_rss_fetcher
from .academic_fetcher import AcademicFetcher, create_academic_fetcher


@dataclass
class IntelligenceItem:
    """情报条目 - 统一格式"""
    category: str  # hot, news, paper, general
    source: str
    title: str
    url: str
    content: str  # 摘要/描述
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
        }


class InformationIntake:
    """统一信息获取器

    根据查询类型自动选择最合适的信息源
    """

    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url

        # 初始化各层级获取器
        self.classifier = get_classifier()
        self.hot_fetcher = create_hot_fetcher()
        self.rss_fetcher = create_rss_fetcher(proxy_url=proxy_url)
        self.academic_fetcher = create_academic_fetcher()

        # Tavily 搜索（延迟导入，避免循环依赖）
        self._tavily_search = None

    def _get_tavily_search(self):
        """懒加载 Tavily 搜索"""
        if self._tavily_search is None:
            try:
                from src.mcp.tools.search import search_web
                self._tavily_search = search_web
            except ImportError:
                logger.warning("Tavily search not available")
        return self._tavily_search

    async def intake(
        self,
        query: Optional[str] = None,
        category: Optional[InfoCategory] = None,
        max_items: int = 10,
    ) -> List[IntelligenceItem]:
        """统一信息获取入口

        Args:
            query: 查询关键词（可选）
            category: 指定分类（可选）
            max_items: 最大条目数

        Returns:
            List[IntelligenceItem]: 情报列表
        """
        # 1. 确定分类
        if category is None and query:
            result = self.classifier.classify(query)
            category = result.category
            logger.info(f"Query '{query}' classified as: {category.value}")
        elif category is None:
            category = InfoCategory.NEWS  # 默认新闻
        elif isinstance(category, str):
            # 支持字符串参数
            try:
                category = InfoCategory(category)
            except ValueError:
                category = InfoCategory.NEWS

        # 获取分类的字符串值用于日志
        category_str = category.value if isinstance(category, InfoCategory) else str(category)

        # 2. 根据分类获取信息
        items = []

        # 处理 category 参数 - 支持字符串或枚举
        if isinstance(category, str):
            try:
                category = InfoCategory(category)
            except ValueError:
                category = InfoCategory.NEWS

        if category == InfoCategory.HOT:
            items = await self._intake_hot(max_items)
        elif category == InfoCategory.NEWS:
            items = await self._intake_news(max_items)
        elif category == InfoCategory.PAPER:
            items = await self._intake_paper(query, max_items)
        else:  # GENERAL
            items = await self._intake_general(query, max_items)

        logger.info(f"Intake completed: {len(items)} items from {category_str}")
        return items

    async def _intake_hot(self, max_items: int) -> List[IntelligenceItem]:
        """获取热榜信息"""
        hot_items = await self.hot_fetcher.fetch_all()

        items = []
        for hot in hot_items[:max_items]:
            items.append(IntelligenceItem(
                category="hot",
                source=hot.source,
                title=hot.title,
                url=hot.url,
                content=hot.description,
                timestamp=hot.timestamp,
                metadata={"score": hot.score, "rank": hot.rank},
            ))

        return items

    async def _intake_news(self, max_items: int) -> List[IntelligenceItem]:
        """获取新闻信息 (RSS)"""
        # 使用已有的 RSS Fetcher
        rss_items = self.rss_fetcher.fetch_multiple(
            categories=["tech", "geopolitics", "business"],
            max_items_per_feed=5,
        )

        items = []
        for rss in rss_items[:max_items]:
            items.append(IntelligenceItem(
                category="news",
                source=rss.source,
                title=rss.title,
                url=rss.link,
                content=rss.description[:200] if rss.description else "",
                timestamp=rss.pub_date,
                metadata={"threat": rss.threat.category.value if rss.threat else None},
            ))

        return items

    async def _intake_paper(self, query: Optional[str], max_items: int) -> List[IntelligenceItem]:
        """获取学术论文"""
        if query:
            papers = await self.academic_fetcher.search(query, sources=["arxiv"])
        else:
            papers = await self.academic_fetcher.get_recent("arxiv", max_results=max_items)

        items = []
        for paper in papers[:max_items]:
            items.append(IntelligenceItem(
                category="paper",
                source=paper.source,
                title=paper.title,
                url=paper.url,
                content=paper.abstract,
                timestamp=paper.published_date,
                metadata={
                    "authors": paper.authors[:3],  # 只保留前3个作者
                    "categories": paper.categories,
                },
            ))

        return items

    async def _intake_general(self, query: Optional[str], max_items: int) -> List[IntelligenceItem]:
        """通用搜索 (Tavily) - 作为补充来源"""
        if not query:
            # 无查询时返回默认新闻
            return await self._intake_news(max_items)

        search_web = self._get_tavily_search()
        if not search_web:
            logger.warning("Tavily search not available, falling back to RSS")
            return await self._intake_news(max_items)

        try:
            # 调用 Tavily 搜索
            results = await search_web(query, max_results=max_items)

            # 解析结果（简化处理）
            items = []
            if isinstance(results, str):
                # Tavily 返回格式化文本，需要解析
                # 这里简化处理，实际可以进一步解析
                lines = results.split("\n")
                current_title = ""
                current_url = ""
                current_content = []

                for line in lines:
                    if line.startswith("### "):
                        # 新标题
                        if current_title:
                            items.append(IntelligenceItem(
                                category="general",
                                source="tavily",
                                title=current_title,
                                url=current_url,
                                content=" ".join(current_content)[:200],
                            ))
                        current_title = line.replace("### ", "").strip()
                        current_url = ""
                        current_content = []
                    elif line.strip().startswith("http"):
                        current_url = line.strip()
                    elif line.strip() and not line.startswith("##"):
                        current_content.append(line.strip())

                # 添加最后一个
                if current_title:
                    items.append(IntelligenceItem(
                        category="general",
                        source="tavily",
                        title=current_title,
                        url=current_url,
                        content=" ".join(current_content)[:200],
                    ))

            return items[:max_items]

        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            # 降级到 RSS
            return await self._intake_news(max_items)

    async def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        status = {
            "classifier": "ok",
            "hot_fetcher": "ok",
            "rss_fetcher": self.rss_fetcher.get_status() if self.rss_fetcher else {"error": "not initialized"},
            "academic_fetcher": "ok",
            "tavily": "available" if self._get_tavily_search() else "not available",
        }
        return status


# 全局实例
_intake: Optional[InformationIntake] = None


def get_information_intake(proxy_url: Optional[str] = None) -> InformationIntake:
    """获取全局信息获取器实例"""
    global _intake
    if _intake is None:
        _intake = InformationIntake(proxy_url=proxy_url)
    return _intake

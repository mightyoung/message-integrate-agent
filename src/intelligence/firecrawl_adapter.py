# coding=utf-8
"""
Firecrawl Adapter - 网页内容抓取适配器

将 Firecrawl 云服务集成到情报流水线：
- 从 URL 抓取完整内容
- 支持批量抓取
- 支持搜索功能

参考: Firecrawl 官方 SDK
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from loguru import logger


@dataclass
class FirecrawlResult:
    """Firecrawl 抓取结果"""
    url: str
    title: str
    content: str
    markdown: str
    metadata: Dict[str, Any]
    success: bool
    error: str = ""


class FirecrawlAdapter:
    """Firecrawl 适配器

    用于抓取网页完整内容，扩展情报数据
    """

    def __init__(
        self,
        api_key: str = None,
        api_url: str = "https://api.firecrawl.dev",
    ):
        """初始化适配器

        Args:
            api_key: Firecrawl API Key
            api_url: Firecrawl API 地址
        """
        self.api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
        self.api_url = api_url
        self._client = None

        # 缓存已抓取的 URL
        self._cache: Dict[str, FirecrawlResult] = {}

    def _get_client(self):
        """获取 Firecrawl 客户端"""
        if self._client is None:
            try:
                from firecrawl import Firecrawl
                self._client = Firecrawl(api_key=self.api_key, api_url=self.api_url)
                logger.info(f"[Firecrawl] 初始化成功, API: {self.api_url}")
            except ImportError:
                logger.error("[Firecrawl] 未安装 firecrawl-py，请运行: pip install firecrawl")
                return None
        return self._client

    async def scrape_url(
        self,
        url: str,
        formats: List[str] = None,
        only_main_content: bool = True,
    ) -> Optional[FirecrawlResult]:
        """抓取单个 URL

        Args:
            url: 目标 URL
            formats: 返回格式 (markdown, html, text)
            only_main_content: 只抓取主要内容

        Returns:
            FirecrawlResult: 抓取结果
        """
        # 检查缓存
        if url in self._cache:
            logger.info(f"[Firecrawl] 使用缓存: {url}")
            return self._cache[url]

        if formats is None:
            formats = ["markdown", "html"]

        try:
            client = self._get_client()
            if not client:
                return None

            logger.info(f"[Firecrawl] 抓取: {url}")

            # 同步调用（Firecrawl SDK 主要是同步的）
            result = client.scrape(
                url=url,
                formats=formats,
                only_main_content=only_main_content,
            )

            # 新版 Firecrawl 返回 Document 对象
            if result:
                # 获取 title - 可能是 metadata 对象或 dict
                title = ""
                if hasattr(result.metadata, 'title'):
                    title = result.metadata.title or ""
                elif isinstance(result.metadata, dict):
                    title = result.metadata.get("title", "")

                markdown_content = result.markdown or ""
                html_content = result.html or ""

                # 获取 metadata - 转换为 dict
                metadata = {}
                if hasattr(result, 'metadata_dict'):
                    metadata = result.metadata_dict
                elif hasattr(result, 'metadata') and isinstance(result.metadata, dict):
                    metadata = result.metadata
                elif hasattr(result, 'metadata'):
                    # 是 DocumentMetadata 对象，转换为 dict
                    metadata = {
                        "title": getattr(result.metadata, "title", ""),
                        "description": getattr(result.metadata, "description", ""),
                        "url": getattr(result.metadata, "url", ""),
                        "published_time": getattr(result.metadata, "published_time", ""),
                    }

                firecrawl_result = FirecrawlResult(
                    url=url,
                    title=title,
                    content=markdown_content or html_content,
                    markdown=markdown_content,
                    metadata=metadata,
                    success=True,
                )
                # 缓存结果
                self._cache[url] = firecrawl_result
                logger.info(f"[Firecrawl] 成功: {url}, 内容长度: {len(firecrawl_result.content)}")
                return firecrawl_result
            else:
                logger.warning(f"[Firecrawl] 失败: {url}")
                return FirecrawlResult(
                    url=url,
                    title="",
                    content="",
                    markdown="",
                    metadata={},
                    success=False,
                    error="No result returned",
                )

        except Exception as e:
            logger.error(f"[Firecrawl] 异常: {url}, {e}")
            return FirecrawlResult(
                url=url,
                title="",
                content="",
                markdown="",
                metadata={},
                success=False,
                error=str(e),
            )

    async def scrape_urls(
        self,
        urls: List[str],
        formats: List[str] = None,
    ) -> List[FirecrawlResult]:
        """批量抓取 URL

        Args:
            urls: URL 列表
            formats: 返回格式

        Returns:
            List[FirecrawlResult]: 抓取结果列表
        """
        results = []
        for url in urls:
            result = await self.scrape_url(url, formats)
            results.append(result)

        success_count = sum(1 for r in results if r.success)
        logger.info(f"[Firecrawl] 批量抓取完成: {success_count}/{len(urls)} 成功")

        return results

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, str]]:
        """搜索网页

        Args:
            query: 搜索关键词
            limit: 返回数量

        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            client = self._get_client()
            if not client:
                return []

            logger.info(f"[Firecrawl] 搜索: {query}")

            result = client.search(query=query, limit=limit)

            if result.success:
                results = []
                for item in result.data:
                    results.append({
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "description": item.get("description", ""),
                    })
                logger.info(f"[Firecrawl] 搜索完成: {len(results)} 结果")
                return results
            else:
                logger.warning(f"[Firecrawl] 搜索失败: {result.error}")
                return []

        except Exception as e:
            logger.error(f"[Firecrawl] 搜索异常: {e}")
            return []

    async def expand_intelligence(
        self,
        news_items: List,
        max_items: int = 5,
    ) -> List:
        """扩展情报内容

        对高价值情报进行深度抓取

        Args:
            news_items: 原始情报列表
            max_items: 最大抓取数量

        Returns:
            List: 扩展后的情报列表
        """
        if not news_items:
            return news_items

        # 按评分排序，选择 top N
        sorted_items = sorted(
            news_items,
            key=lambda x: getattr(x, 'total_score', 0),
            reverse=True
        )
        items_to_expand = sorted_items[:max_items]

        # 提取 URLs
        urls_to_scrape = []
        item_map = {}  # url -> item index

        for i, item in enumerate(items_to_scrape):
            url = getattr(item.news_item, 'url', '') if hasattr(item, 'news_item') else getattr(item, 'url', '')
            if url and url not in self._cache:
                urls_to_scrape.append(url)
                item_map[url] = i

        if not urls_to_scrape:
            logger.info("[Firecrawl] 无需抓取新 URL")
            return news_items

        # 批量抓取
        results = await self.scrape_urls(urls_to_scrape)

        # 更新情报内容
        for result in results:
            if result.success and result.url in item_map:
                idx = item_map[result.url]
                item = items_to_expand[idx]

                # 更新内容
                if hasattr(item, 'news_item'):
                    item.news_item.content = result.markdown
                    item.news_item.summary = result.markdown[:500]

        logger.info(f"[Firecrawl] 扩展完成: {len(urls_to_scrape)} URL")

        return news_items

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("[Firecrawl] 缓存已清空")


# 全局适配器实例
_firecrawl_adapter: Optional[FirecrawlAdapter] = None


def get_firecrawl_adapter(
    api_key: str = None,
    api_url: str = "https://api.firecrawl.dev",
) -> Optional[FirecrawlAdapter]:
    """获取 Firecrawl 适配器实例"""
    global _firecrawl_adapter
    if _firecrawl_adapter is None:
        _firecrawl_adapter = FirecrawlAdapter(api_key=api_key, api_url=api_url)
    return _firecrawl_adapter

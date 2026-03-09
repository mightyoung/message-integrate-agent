# coding=utf-8
"""
Hot Fetcher - 热榜直接获取器

Tier 1: 热榜直接获取 (无需代理)
- Hacker News API
- GitHub Trending
- Product Hunt

这些 API 通常可以直接访问，不需要代理
"""
import asyncio
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


@dataclass
class HotItem:
    """热榜条目"""
    source: str
    title: str
    url: str
    rank: int
    score: Optional[int] = None
    author: Optional[str] = None
    timestamp: Optional[datetime] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "rank": self.rank,
            "score": self.score,
            "author": self.author,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "description": self.description,
        }


class HackerNewsFetcher:
    """Hacker News 热榜获取器

    使用官方 Firebase API
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, max_items: int = 20, proxy_url: Optional[str] = None):
        self.max_items = max_items
        self.proxy_url = proxy_url
        self._cache: List[HotItem] = []
        self._cache_time: float = 0
        self._cache_ttl = 300  # 5 分钟缓存

    def _create_client(self) -> httpx.AsyncClient:
        """创建带代理的客户端"""
        kwargs = {"timeout": 30.0}
        if self.proxy_url:
            kwargs["proxy"] = self.proxy_url
        return httpx.AsyncClient(**kwargs)

    def _is_cache_valid(self) -> bool:
        return time.time() - self._cache_time < self._cache_ttl

    async def fetch(self) -> List[HotItem]:
        """获取 Hacker News Top Stories"""
        if self._cache and self._is_cache_valid():
            return self._cache

        items = []
        try:
            async with self._create_client() as client:
                # 获取 Top Stories IDs
                response = await client.get(f"{self.BASE_URL}/topstories.json")
                story_ids = response.json()[:self.max_items]

                # 并行获取详情
                tasks = [
                    self._fetch_item(client, story_id, idx + 1)
                    for idx, story_id in enumerate(story_ids)
                ]
                items = await asyncio.gather(*tasks, return_exceptions=True)

                # 过滤异常结果
                items = [item for item in items if isinstance(item, HotItem)]

        except Exception as e:
            logger.error(f"Hacker News fetch error: {e}")

        self._cache = items
        self._cache_time = time.time()
        return items

    async def _fetch_item(self, client: httpx.AsyncClient, item_id: int, rank: int) -> Optional[HotItem]:
        """获取单条故事详情"""
        try:
            response = await client.get(f"{self.BASE_URL}/item/{item_id}.json")
            data = response.json()

            if not data:
                return None

            # 解析时间
            timestamp = None
            if data.get("time"):
                timestamp = datetime.fromtimestamp(data["time"])

            return HotItem(
                source="hackernews",
                title=data.get("title", ""),
                url=data.get("url", f"https://news.ycombinator.com/item?id={item_id}"),
                rank=rank,
                score=data.get("score"),
                author=data.get("by"),
                timestamp=timestamp,
                description=f"{data.get('score')} points | {data.get('descendants', 0)} comments",
            )
        except Exception as e:
            logger.debug(f"Error fetching HN item {item_id}: {e}")
            return None


class GitHubTrendingFetcher:
    """GitHub Trending 获取器

    使用 GitHub API 获取趋势仓库
    """

    def __init__(self, max_items: int = 15, language: str = "all", proxy_url: Optional[str] = None):
        self.max_items = max_items
        self.language = language
        self.proxy_url = proxy_url
        self._cache: List[HotItem] = []
        self._cache_time: float = 0
        self._cache_ttl = 600  # 10 分钟缓存

    def _create_client(self) -> httpx.AsyncClient:
        """创建带代理的客户端"""
        kwargs = {"timeout": 30.0}
        if self.proxy_url:
            kwargs["proxy"] = self.proxy_url
        return httpx.AsyncClient(**kwargs)

    def _is_cache_valid(self) -> bool:
        return time.time() - self._cache_time < self._cache_ttl

    async def fetch(self) -> List[HotItem]:
        """获取 GitHub Trending 仓库"""
        if self._cache and self._is_cache_valid():
            return self._cache

        items = []
        try:
            # 使用 GitHub API 搜索趋势仓库
            # 按 stars 排序，获取近期创建的
            query = f"stars:>1000 created:>{self._get_date_range()}"
            if self.language != "all":
                query += f" language:{self.language}"

            url = "https://api.github.com/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": self.max_items,
            }
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "message-integrate-agent",
            }

            async with self._create_client() as client:
                response = await client.get(url, params=params, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    for idx, repo in enumerate(data.get("items", [])[:self.max_items], 1):
                        items.append(HotItem(
                            source="github_trending",
                            title=repo.get("full_name", ""),
                            url=repo.get("html_url", ""),
                            rank=idx,
                            score=repo.get("stargazers_count"),
                            author=repo.get("owner", {}).get("login"),
                            timestamp=datetime.fromisoformat(
                                repo.get("created_at", "").replace("Z", "+00:00")
                            ) if repo.get("created_at") else None,
                            description=f"⭐ {repo.get('stargazers_count')} | 🍴 {repo.get('forks_count')} | {repo.get('language', 'N/A')}",
                        ))

        except Exception as e:
            logger.error(f"GitHub Trending fetch error: {e}")

        self._cache = items
        self._cache_time = time.time()
        return items

    def _get_date_range(self) -> str:
        """获取日期范围（30天内）"""
        from datetime import timedelta
        date = datetime.now() - timedelta(days=30)
        return date.strftime("%Y-%m-%d")


class ProductHuntFetcher:
    """Product Hunt 热榜获取器"""

    def __init__(self, max_items: int = 15, proxy_url: Optional[str] = None):
        self.max_items = max_items
        self.proxy_url = proxy_url
        self._cache: List[HotItem] = []
        self._cache_time: float = 0
        self._cache_ttl = 300  # 5 分钟缓存

    def _create_client(self) -> httpx.AsyncClient:
        kwargs = {"timeout": 30.0, "follow_redirects": True}
        if self.proxy_url:
            kwargs["proxy"] = self.proxy_url
        return httpx.AsyncClient(**kwargs)

    def _is_cache_valid(self) -> bool:
        return time.time() - self._cache_time < self._cache_ttl

    async def fetch(self) -> List[HotItem]:
        """获取 Product Hunt 今日热门"""
        if self._cache and self._is_cache_valid():
            return self._cache

        items = []
        try:
            # Product Hunt API 需要认证，这里使用备用方案
            # 尝试通过 RSS 或页面获取
            url = "https://www.producthunt.com/feed"

            async with self._create_client() as client:
                response = await client.get(url)

                if response.status_code == 200:
                    # 简化解析，实际生产需要更健壮的解析
                    # Product Hunt 页面结构复杂，这里返回空列表
                    # 实际可以使用官方 API 或第三方
                    logger.info("Product Hunt direct fetch not implemented, skipping")

        except Exception as e:
            logger.error(f"Product Hunt fetch error: {e}")

        # Product Hunt 需要 API Key，暂时跳过
        # 可以后续添加官方 API 支持
        self._cache = items
        self._cache_time = time.time()
        return items


class WeiboHotFetcher:
    """微博热搜获取器

    使用移动端 API，通常可以直连
    """

    def __init__(self, max_items: int = 20, proxy_url: Optional[str] = None):
        self.max_items = max_items
        self.proxy_url = proxy_url
        self._cache: List[HotItem] = []
        self._cache_time: float = 0
        self._cache_ttl = 300  # 5 分钟缓存

    def _create_client(self) -> httpx.AsyncClient:
        kwargs = {"timeout": 30.0}
        if self.proxy_url:
            kwargs["proxy"] = self.proxy_url
        return httpx.AsyncClient(**kwargs)

    def _is_cache_valid(self) -> bool:
        return time.time() - self._cache_time < self._cache_ttl

    async def fetch(self) -> List[HotItem]:
        """获取微博热搜榜"""
        if self._cache and self._is_cache_valid():
            return self._cache

        items = []
        try:
            # 微博移动端 API
            url = "https://weibo.com/ajax/side/hotSearch"

            async with self._create_client() as client:
                response = await client.get(url)

                if response.status_code == 200:
                    data = response.json()
                    realtime = data.get("data", {}).get("realtime", [])

                    for idx, item in enumerate(realtime[:self.max_items], 1):
                        items.append(HotItem(
                            source="weibo_hot",
                            title=item.get("word", ""),
                            url=f"https://s.weibo.com/weibo?q={item.get('word', '')}",
                            rank=idx,
                            score=item.get("num", 0),
                            description=f"热度: {item.get('num', 0)}",
                        ))

        except Exception as e:
            logger.error(f"Weibo hot fetch error: {e}")

        self._cache = items
        self._cache_time = time.time()
        return items


class HotFetcher:
    """热榜统一获取器

    整合多种热榜来源
    """

    def __init__(self, max_items_per_source: int = 15, proxy_url: Optional[str] = None):
        self.max_items = max_items_per_source
        self.proxy_url = proxy_url

        self.fetchers = {
            "hackernews": HackerNewsFetcher(max_items=max_items_per_source, proxy_url=proxy_url),
            "github_trending": GitHubTrendingFetcher(max_items=max_items_per_source, proxy_url=proxy_url),
            "producthunt": ProductHuntFetcher(max_items=max_items_per_source, proxy_url=proxy_url),
            "weibo_hot": WeiboHotFetcher(max_items=max_items_per_source, proxy_url=proxy_url),
        }

    async def fetch_all(self, sources: Optional[List[str]] = None) -> List[HotItem]:
        """获取所有启用的热榜

        Args:
            sources: 指定来源列表，None 表示全部

        Returns:
            List[HotItem]: 按 rank 排序的热榜列表
        """
        if sources is None:
            sources = list(self.fetchers.keys())

        tasks = []
        for source in sources:
            if source in self.fetchers:
                tasks.append(self.fetchers[source].fetch())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)

        # 按 rank 排序
        all_items.sort(key=lambda x: x.rank)

        return all_items

    async def fetch_source(self, source: str) -> List[HotItem]:
        """获取指定来源的热榜"""
        if source not in self.fetchers:
            logger.warning(f"Unknown hot source: {source}")
            return []

        return await self.fetchers[source].fetch()


# 便捷函数
def create_hot_fetcher(proxy_url: Optional[str] = None) -> HotFetcher:
    """创建热榜获取器

    Args:
        proxy_url: 代理 URL (可选)
    """
    return HotFetcher(proxy_url=proxy_url)

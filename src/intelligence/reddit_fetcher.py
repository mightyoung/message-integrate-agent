# coding=utf-8
"""
Reddit Fetcher - 获取 Reddit 热帖

基于 opc-skills 的 Reddit 实现
使用 Reddit 公共 JSON API，无需认证

数据源:
- Reddit 热门帖子 (r/popular)
- 支持获取多个 subreddit 的热门帖子
"""
import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


@dataclass
class RedditItem:
    """Reddit 帖子项"""
    source: str
    title: str
    url: str
    rank: int
    score: Optional[int] = None
    author: Optional[str] = None
    timestamp: Optional[datetime] = None
    description: str = ""
    subreddit: str = ""
    num_comments: int = 0

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
            "subreddit": self.subreddit,
            "num_comments": self.num_comments,
        }


class RedditFetcher:
    """Reddit 热帖获取器

    使用 Reddit 公共 JSON API
    无需认证，但有速率限制
    """

    BASE_URL = "https://www.reddit.com"

    # 默认订阅的 subreddit
    DEFAULT_SUBREDDITS = [
        "technology",
        "science",
        "artificial",
        "MachineLearning",
        "programming",
        "人工智能",  # 中文 subreddit
    ]

    def __init__(
        self,
        max_items: int = 10,
        proxy_url: Optional[str] = None,
        subreddits: Optional[List[str]] = None,
    ):
        self.max_items = max_items
        self.proxy_url = proxy_url
        self.subreddits = subreddits or self.DEFAULT_SUBREDDITS
        self._cache: List[RedditItem] = []
        self._cache_time: float = 0
        self._cache_ttl = 300  # 5 分钟缓存

    def _create_client(self) -> httpx.AsyncClient:
        """创建带代理的客户端"""
        kwargs = {
            "timeout": 30.0,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        }
        if self.proxy_url:
            kwargs["proxy"] = self.proxy_url
        return httpx.AsyncClient(**kwargs)

    def _is_cache_valid(self) -> bool:
        return time.time() - self._cache_time < self._cache_ttl

    def _parse_timestamp(self, created_utc: float) -> datetime:
        """解析 Reddit 时间戳"""
        return datetime.fromtimestamp(created_utc)

    async def _fetch_subreddit(self, client: httpx.AsyncClient, subreddit: str) -> List[RedditItem]:
        """获取单个 subreddit 的热门帖子"""
        items = []
        try:
            # 使用 .json 端点获取数据
            url = f"{self.BASE_URL}/r/{subreddit}/hot/.json"
            response = await client.get(url, params={"limit": self.max_items})

            if response.status_code == 200:
                data = response.json()
                posts = data.get("data", {}).get("children", [])

                for idx, post in enumerate(posts[:self.max_items], 1):
                    post_data = post.get("data", {})
                    items.append(RedditItem(
                        source="reddit",
                        title=post_data.get("title", ""),
                        url=f"https://reddit.com{post_data.get('permalink', '')}",
                        rank=idx,
                        score=post_data.get("score", 0),
                        author=post_data.get("author", ""),
                        timestamp=self._parse_timestamp(post_data.get("created_utc", 0)),
                        description=post_data.get("selftext", "")[:200] if post_data.get("selftext") else "",
                        subreddit=subreddit,
                        num_comments=post_data.get("num_comments", 0),
                    ))
            else:
                logger.warning(f"Reddit fetch error for r/{subreddit}: HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Reddit fetch error for r/{subreddit}: {e}")

        return items

    async def fetch(self) -> List[RedditItem]:
        """获取 Reddit 热门帖子"""
        if self._cache and self._is_cache_valid():
            return self._cache

        items = []
        try:
            async with self._create_client() as client:
                # 并行获取所有 subreddit
                tasks = [
                    self._fetch_subreddit(client, subreddit)
                    for subreddit in self.subreddits
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 合并结果并按 score 排序
                for result in results:
                    if isinstance(result, list):
                        items.extend(result)

                # 按 score 排序
                items.sort(key=lambda x: -((x.score or 0) + x.num_comments * 2))

                # 限制数量
                items = items[:self.max_items]

                # 更新 rank
                for idx, item in enumerate(items, 1):
                    item.rank = idx

        except Exception as e:
            logger.error(f"Reddit fetch error: {e}")

        self._cache = items
        self._cache_time = time.time()
        logger.info(f"Reddit: {len(items)} posts found")
        return items

    async def fetch_async(self) -> List[RedditItem]:
        """异步获取"""
        return await self.fetch()


def create_reddit_fetcher(
    max_items: int = 5,
    proxy_url: Optional[str] = None,
    subreddits: Optional[List[str]] = None,
) -> RedditFetcher:
    """创建 Reddit 获取器的便捷函数"""
    return RedditFetcher(max_items=max_items, proxy_url=proxy_url, subreddits=subreddits)

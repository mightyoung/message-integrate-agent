# coding=utf-8
"""
GitHub Trending Fetcher - 获取 GitHub Trending 仓库

基于 tech-news-digest 的 GitHub Trending 实现

数据源:
- GitHub Search API: 搜索近期活跃的高星仓库
- 支持按主题过滤 (llm, ai-agent, crypto, frontier-tech)
"""
import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from urllib.parse import quote
import logging

from loguru import logger


# GitHub Trending 搜索查询
TRENDING_QUERIES = [
    {"topic": "llm", "q": "llm large-language-model in:topics,name,description"},
    {"topic": "ai-agent", "q": "ai-agent autonomous-agent in:topics,name,description"},
    {"topic": "crypto", "q": "blockchain ethereum solidity defi in:topics,name,description"},
    {"topic": "frontier-tech", "q": "machine-learning deep-learning in:topics,name,description"},
]

TIMEOUT = 30


class GitHubTrendingItem:
    """GitHub Trending 仓库项"""

    def __init__(
        self,
        repo: str,
        name: str,
        description: str,
        url: str,
        stars: int,
        daily_stars_est: int,
        forks: int,
        language: str,
        topics: List[str],
        created_at: str,
        pushed_at: str,
        readme_content: str = "",
    ):
        self.repo = repo
        self.name = name
        self.description = description or ""
        self.url = url
        self.stars = stars
        self.daily_stars_est = daily_stars_est
        self.forks = forks
        self.language = language or "Unknown"
        self.topics = topics
        self.created_at = created_at
        self.pushed_at = pushed_at
        self.readme_content = readme_content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo": self.repo,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "stars": self.stars,
            "daily_stars_est": self.daily_stars_est,
            "forks": self.forks,
            "language": self.language,
            "topics": self.topics,
            "created_at": self.created_at,
            "pushed_at": self.pushed_at,
        }


class GitHubTrendingFetcher:
    """GitHub Trending 仓库获取器"""

    def __init__(
        self,
        github_token: str = None,
        hours: int = 48,
        min_stars: int = 50,
        per_topic: int = 15,
    ):
        """初始化

        Args:
            github_token: GitHub Token (可选，提高 API 限制)
            hours: 回溯时间窗口(小时)
            min_stars: 最小星数
            per_topic: 每个主题获取的最大仓库数
        """
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.hours = hours
        self.min_stars = min_stars
        self.per_topic = per_topic
        self._headers = {
            "User-Agent": "MessageIntegrateAgent/1.0",
            "Accept": "application/vnd.github.v3+json",
        }
        if self.github_token:
            self._headers["Authorization"] = f"Bearer {self.github_token}"

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析 GitHub ISO 日期"""
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def fetch(self) -> List[GitHubTrendingItem]:
        """获取 GitHub Trending 仓库

        Returns:
            仓库列表 (按星数排序)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.hours)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        all_repos = []
        seen_repos = set()

        for tq in TRENDING_QUERIES:
            q = f"{tq['q']} pushed:>{cutoff_str} stars:>{self.min_stars}"
            url = f"https://api.github.com/search/repositories?q={quote(q)}&sort=stars&order=desc&per_page={self.per_topic}"

            try:
                req = Request(url, headers=self._headers)
                with urlopen(req, timeout=TIMEOUT) as resp:
                    data = json.loads(resp.read().decode())

                for item in data.get("items", []):
                    full_name = item["full_name"]
                    if full_name in seen_repos:
                        continue
                    seen_repos.add(full_name)

                    # 估算每日增长星数
                    created = self._parse_date(item.get("created_at", ""))
                    age_days = max(1, (datetime.now(timezone.utc) - created).days) if created else 365
                    stars = item.get("stargazers_count", 0)
                    daily_stars = round(stars / age_days)

                    all_repos.append(
                        GitHubTrendingItem(
                            repo=full_name,
                            name=item.get("name", ""),
                            description=item.get("description") or "",
                            url=item.get("html_url", ""),
                            stars=stars,
                            daily_stars_est=daily_stars,
                            forks=item.get("forks_count", 0),
                            language=item.get("language", ""),
                            topics=[tq["topic"]],
                            created_at=item.get("created_at", ""),
                            pushed_at=item.get("pushed_at", ""),
                        )
                    )

                logger.debug(f"Trending [{tq['topic']}]: {len(data.get('items', []))} repos")

            except HTTPError as e:
                logger.warning(f"GitHub trending search error [{tq['topic']}]: HTTP {e.code}")
            except Exception as e:
                logger.warning(f"GitHub trending search error [{tq['topic']}]: {e}")

        # 按星数排序
        all_repos.sort(key=lambda x: -x.stars)
        logger.info(f"GitHub Trending: {len(all_repos)} repos found")
        return all_repos

    async def fetch_async(self) -> List[GitHubTrendingItem]:
        """异步获取 GitHub Trending 仓库"""
        return await asyncio.to_thread(self.fetch)


def create_github_trending_fetcher() -> GitHubTrendingFetcher:
    """创建 GitHub Trending 获取器的便捷函数"""
    return GitHubTrendingFetcher()

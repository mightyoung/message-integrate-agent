# coding=utf-8
"""
WorldMonitor Adapter - 集成 WorldMonitor 情报源

基于 WorldMonitor 项目 (https://github.com/koala73/worldmonitor)

功能:
- 从 WorldMonitor API 获取全球新闻
- 支持多类别: geopolitics, military, economy, tech, climate 等
- 转换 WorldMonitor 格式到本地 NewsItem 格式
- 支持 AI 摘要生成

参考:
- WorldMonitor RSS 服务: src/services/rss.ts
- WorldMonitor API: api/news/v1/
- WorldMonitor feeds 配置: src/config/feeds.ts (435+ 源)
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
from loguru import logger


class ThreatLevel(Enum):
    """威胁等级"""
    UNSPECIFIED = "unspecified"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorldMonitorCategory(Enum):
    """WorldMonitor 新闻类别"""
    GEOPOLITICS = "geopolitics"
    MILITARY = "military"
    ECONOMY = "economy"
    TECH = "tech"
    CLIMATE = "climate"
    ENERGY = "energy"
    HEALTH = "health"
    SPACE = "space"
    CYBER = "cyber"


@dataclass
class WorldMonitorNewsItem:
    """WorldMonitor 新闻条目 (原始格式)"""
    source: str
    title: str
    link: str
    published_at: int  # timestamp
    is_alert: bool = False
    threat_level: Optional[str] = None
    threat_category: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class WorldMonitorConfig:
    """WorldMonitor 配置"""
    api_url: str = "https://worldmonitor.app"
    api_key: str = ""
    timeout: int = 30
    max_items: int = 50
    categories: List[str] = field(default_factory=lambda: ["geopolitics", "military", "economy"])


class WorldMonitorAdapter:
    """
    WorldMonitor 适配器

    从 WorldMonitor 获取全球情报,转换为本项目格式

    WorldMonitor 特性:
    - 435+ 精选 RSS 源
    - 威胁分类 (keyword + AI)
    - 地理编码
    - AI 摘要 (Ollama/Groq/OpenRouter)
    """

    def __init__(self, config: Optional[WorldMonitorConfig] = None):
        self.config = config or WorldMonitorConfig()
        self._session = None

    @property
    def session(self):
        """获取或创建请求会话"""
        if self._session is None:
            self._session = requests.Session()
            if self.config.api_key:
                self._session.headers.update({"Authorization": f"Bearer {self.config.api_key}"})
        return self._session

    async def fetch_news(
        self,
        category: str = "geopolitics",
        limit: int = 50,
        language: str = "en"
    ) -> List[WorldMonitorNewsItem]:
        """
        获取指定类别的新闻

        Args:
            category: 新闻类别 (geopolitics/military/economy/tech/climate)
            limit: 返回数量
            language: 语言 (en/zh/es/etc.)

        Returns:
            List[WorldMonitorNewsItem]
        """
        # WorldMonitor 使用 RSS 聚合,没有公开 API
        # 这里模拟调用方式,实际需要部署 WorldMonitor 或使用其公开端点
        logger.info(f"📡 Fetching {category} news from WorldMonitor (limit={limit})")

        # 实际实现需要调用 WorldMonitor API
        # 由于 WorldMonitor 是自托管项目,这里提供两种模式:
        # 1. 本地部署模式: 调用本地 API
        # 2. 远程模式: 如果 WorldMonitor 公开 API

        try:
            # 尝试调用 WorldMonitor RSS 端点
            items = await self._fetch_from_rss(category, limit, language)
            return items
        except Exception as e:
            logger.error(f"WorldMonitor fetch error: {e}")
            return []

    async def _fetch_from_rss(
        self,
        category: str,
        limit: int,
        language: str
    ) -> List[WorldMonitorNewsItem]:
        """从 WorldMonitor RSS 端点获取"""
        # WorldMonitor 提供 RSS 端点
        # 实际需要根据 category 选择正确的 RSS 源

        # 这里返回空列表作为示例
        # 实际实现需要:
        # 1. 根据 category 映射到对应的 RSS 源
        # 2. 调用 rss-proxy 端点
        # 3. 解析返回的 NewsItem

        logger.debug(f"Fetching {category} RSS feeds")

        # 示例: 使用 WorldMonitor 的 rss-proxy
        # url = f"{self.config.api_url}/api/rss-proxy?category={category}&lang={language}"
        # response = self.session.get(url, timeout=self.config.timeout)
        # items = self._parse_rss_response(response.json())

        return []

    def _parse_rss_response(self, data: Dict[str, Any]) -> List[WorldMonitorNewsItem]:
        """解析 WorldMonitor RSS 响应"""
        items = []

        for item_data in data.get("items", []):
            item = WorldMonitorNewsItem(
                source=item_data.get("source", "Unknown"),
                title=item_data.get("title", ""),
                link=item_data.get("link", ""),
                published_at=item_data.get("publishedAt", 0),
                is_alert=item_data.get("isAlert", False),
                threat_level=item_data.get("threat", {}).get("level"),
                threat_category=item_data.get("threat", {}).get("category"),
                location_name=item_data.get("locationName"),
            )

            # 解析地理坐标
            if item_data.get("location"):
                item.latitude = item_data["location"].get("latitude")
                item.longitude = item_data["location"].get("longitude")

            items.append(item)

        return items

    def to_local_news_item(self, wm_item: WorldMonitorNewsItem) -> 'NewsItem':
        """
        转换 WorldMonitor 格式到本地 NewsItem

        Args:
            wm_item: WorldMonitor 新闻条目

        Returns:
            本地 NewsItem 格式
        """
        from src.intelligence.fetcher import NewsItem

        # 转换时间戳
        timestamp = ""
        if wm_item.published_at:
            try:
                dt = datetime.fromtimestamp(wm_item.published_at / 1000)
                timestamp = dt.isoformat()
            except:
                pass

        return NewsItem(
            platform=f"worldmonitor:{wm_item.source.lower().replace(' ', '_')}",
            title=wm_item.title,
            url=wm_item.link,
            timestamp=timestamp,
            summary=wm_item.threat_category or ""
        )

    async def fetch_and_convert(
        self,
        category: str = "geopolitics",
        limit: int = 50
    ) -> List['NewsItem']:
        """
        获取并转换新闻到本地格式

        Args:
            category: 新闻类别
            limit: 返回数量

        Returns:
            List[NewsItem]
        """
        wm_items = await self.fetch_news(category, limit)

        # 转换为本地格式
        local_items = [self.to_local_news_item(item) for item in wm_items]

        logger.info(f"✅ Converted {len(local_items)} items from WorldMonitor")
        return local_items

    async def fetch_multiple_categories(
        self,
        categories: Optional[List[str]] = None,
        limit_per_category: int = 20
    ) -> List['NewsItem']:
        """
        获取多个类别的新闻

        Args:
            categories: 类别列表,默认使用配置中的类别
            limit_per_category: 每个类别的数量

        Returns:
            List[NewsItem]
        """
        if categories is None:
            categories = self.config.categories

        all_items = []

        # 并发获取
        tasks = [
            self.fetch_and_convert(category, limit_per_category)
            for category in categories
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_items.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Category fetch error: {result}")

        # 按时间排序
        all_items.sort(
            key=lambda x: x.timestamp,
            reverse=True
        )

        return all_items

    async def get_ai_summary(
        self,
        headlines: List[str],
        provider: str = "openrouter"
    ) -> Optional[str]:
        """
        获取 AI 摘要 (使用 WorldMonitor 的 AI 服务)

        注意: 需要 WorldMonitor 部署并配置 AI 提供商

        Args:
            headlines: 标题列表
            provider: AI 提供商 (openrouter/groq/ollama)

        Returns:
            摘要文本
        """
        logger.info(f"🤖 Requesting AI summary from {provider}")

        # WorldMonitor 提供 /api/summarize 端点
        # 实际调用需要:
        # url = f"{self.config.api_url}/api/summarize"
        # payload = {
        #     "provider": provider,
        #     "headlines": headlines,
        #     "mode": "brief"
        # }
        # response = self.session.post(url, json=payload, timeout=60)
        # return response.json().get("summary")

        logger.warning("AI summary requires WorldMonitor deployment with API key")
        return None

    def close(self):
        """关闭会话"""
        if self._session:
            self._session.close()
            self._session = None


def create_worldmonitor_adapter(
    api_url: str = "https://worldmonitor.app",
    api_key: str = "",
    categories: Optional[List[str]] = None
) -> WorldMonitorAdapter:
    """
    创建 WorldMonitor 适配器

    Args:
        api_url: WorldMonitor API 地址
        api_key: API 密钥
        categories: 感兴趣的类别

    Returns:
        WorldMonitorAdapter 实例
    """
    config = WorldMonitorConfig(
        api_url=api_url,
        api_key=api_key,
        categories=categories or ["geopolitics", "military", "economy"]
    )
    return WorldMonitorAdapter(config)

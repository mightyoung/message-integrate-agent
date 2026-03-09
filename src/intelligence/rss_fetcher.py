# coding=utf-8
"""
RSS Fetcher - 基于 WorldMonitor 的 RSS 获取器

从 WorldMonitor (https://github.com/koala73/worldmonitor) 移植:
- 435+ 精选 RSS 源
- 内存缓存 + 持久化缓存
- 失败冷却机制
- 并行批量获取
- 威胁分类集成

特性:
- RSS/Atom 格式支持
- 图像提取
- 自动威胁分类
- 失败重试与冷却
"""
import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests
from loguru import logger

from .feeds_config import Feed, get_all_feeds, get_feeds_by_category, create_feeds_config
from .threat_classifier import (
    ThreatClassification,
    ThreatLevel,
    classify_by_keyword,
    is_alert,
)


# 常量
FEED_COOLDOWN_MS = 5 * 60 * 1000  # 5 分钟冷却
MAX_FAILURES = 2
MAX_CACHE_ENTRIES = 100
CACHE_TTL = 30 * 60 * 1000  # 30 分钟 TTL


@dataclass
class RSSNewsItem:
    """RSS 新闻条目"""
    source: str
    title: str
    link: str
    pub_date: Optional[datetime] = None
    description: str = ""
    image_url: Optional[str] = None
    lang: str = "en"
    threat: Optional[ThreatClassification] = None
    is_alert: bool = False
    # 地理信息
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "link": self.link,
            "pub_date": self.pub_date.isoformat() if self.pub_date else None,
            "description": self.description,
            "image_url": self.image_url,
            "lang": self.lang,
            "threat": {
                "level": self.threat.level.value if self.threat else None,
                "category": self.threat.category.value if self.threat else None,
                "confidence": self.threat.confidence if self.threat else None,
            } if self.threat else None,
            "is_alert": self.is_alert,
            "location_name": self.location_name,
            "lat": self.lat,
            "lon": self.lon,
        }


class FeedFailure:
    """Feed 失败状态"""
    def __init__(self):
        self.count = 0
        self.cooldown_until = 0


class RSSFetcher:
    """RSS 获取器

    基于 WorldMonitor 的 rss.ts 实现:
    - 缓存机制
    - 失败冷却
    - 并行获取
    - 威胁分类
    """

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 2,
    ):
        """初始化

        Args:
            proxy_url: 代理 URL
            timeout: 超时秒数
            max_retries: 最大重试次数
        """
        self.proxy_url = proxy_url
        self.timeout = timeout
        self.max_retries = max_retries

        # 缓存
        self._feed_cache: Dict[str, List[RSSNewsItem]] = {}
        self._cache_timestamp: Dict[str, float] = {}

        # 失败跟踪
        self._feed_failures: Dict[str, FeedFailure] = {}

        # 请求会话
        self._session = requests.Session()
        if proxy_url:
            self._session.proxies = {"http": proxy_url, "https": proxy_url}

        # 默认请求头
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _cleanup_cache(self) -> None:
        """清理过期缓存"""
        now = time.time() * 1000

        # 清理过期条目
        for key in list(self._cache_timestamp.keys()):
            if now - self._cache_timestamp[key] > CACHE_TTL * 2:
                del self._feed_cache[key]
                del self._cache_timestamp[key]

        # 清理冷却过期的失败
        for key in list(self._feed_failures.keys()):
            failure = self._feed_failures[key]
            if failure.cooldown_until > 0 and now > failure.cooldown_until:
                del self._feed_failures[key]

        # 限制缓存大小
        if len(self._feed_cache) > MAX_CACHE_ENTRIES:
            # 删除最老的
            sorted_keys = sorted(self._cache_timestamp.keys(), key=lambda k: self._cache_timestamp[k])
            for key in sorted_keys[:len(self._feed_cache) - MAX_CACHE_ENTRIES]:
                del self._feed_cache[key]
                del self._cache_timestamp[key]

    def _is_feed_on_cooldown(self, feed_name: str) -> bool:
        """检查 feed 是否在冷却期"""
        if feed_name not in self._feed_failures:
            return False

        failure = self._feed_failures[feed_name]
        if time.time() * 1000 < failure.cooldown_until:
            return True

        if failure.cooldown_until > 0:
            del self._feed_failures[feed_name]
        return False

    def _record_failure(self, feed_name: str) -> None:
        """记录失败"""
        if feed_name not in self._feed_failures:
            self._feed_failures[feed_name] = FeedFailure()

        failure = self._feed_failures[feed_name]
        failure.count += 1

        if failure.count >= MAX_FAILURES:
            failure.cooldown_until = time.time() * 1000 + FEED_COOLDOWN_MS
            logger.warning(f"[RSS] {feed_name} on cooldown for 5 minutes after {failure.count} failures")

    def _record_success(self, feed_name: str) -> None:
        """记录成功"""
        if feed_name in self._feed_failures:
            del self._feed_failures[feed_name]

    def _get_cache_key(self, feed: Feed) -> str:
        """获取缓存键"""
        if isinstance(feed.url, dict):
            url = feed.url.get("en", list(feed.url.values())[0])
        else:
            url = feed.url
        return hashlib.md5(f"{feed.name}:{url}".encode()).hexdigest()

    def _get_cached(self, feed: Feed) -> Optional[List[RSSNewsItem]]:
        """获取缓存"""
        key = self._get_cache_key(feed)
        if key in self._feed_cache:
            if time.time() * 1000 - self._cache_timestamp[key] < CACHE_TTL:
                return self._feed_cache[key]
        return None

    def _set_cached(self, feed: Feed, items: List[RSSNewsItem]) -> None:
        """设置缓存"""
        key = self._get_cache_key(feed)
        self._feed_cache[key] = items
        self._cache_timestamp[key] = time.time() * 1000

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期"""
        if not date_str:
            return None

        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        # 尝试自动检测
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            pass

        return None

    def _extract_image_url(self, item: Any) -> Optional[str]:
        """从 RSS 项中提取图片 URL"""
        try:
            # 尝试 media:content
            media_content = item.find("{http://search.yahoo.com/mrss/}content")
            if media_content is not None:
                url = media_content.get("url")
                if url:
                    return url

            # 尝试 media:thumbnail
            media_thumb = item.find("{http://search.yahoo.com/mrss/}thumbnail")
            if media_thumb is not None:
                url = media_thumb.get("url")
                if url:
                    return url

            # 尝试 enclosure
            enclosure = item.find("enclosure")
            if enclosure is not None:
                url = enclosure.get("url")
                type_attr = enclosure.get("type", "")
                if url and type_attr.startswith("image/"):
                    return url

            # 尝试从 description 提取
            description = item.find("description")
            if description is not None and description.text:
                import re
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', description.text)
                if img_match:
                    return img_match.group(1)

        except Exception as e:
            logger.debug(f"Error extracting image: {e}")

        return None

    def _classify_threat(self, title: str) -> ThreatClassification:
        """分类威胁"""
        return classify_by_keyword(title)

    def _fetch_single_feed(self, feed: Feed) -> List[RSSNewsItem]:
        """获取单个 RSS 源"""
        # 检查冷却
        if self._is_feed_on_cooldown(feed.name):
            cached = self._get_cached(feed)
            if cached:
                logger.debug(f"[RSS] {feed.name} on cooldown, using cached {len(cached)} items")
                return cached
            return []

        # 检查缓存
        cached = self._get_cached(feed)
        if cached:
            return cached

        # 获取 URL
        if isinstance(feed.url, dict):
            url = feed.url.get(feed.lang or "en", feed.url.get("en", list(feed.url.values())[0]))
        else:
            url = feed.url

        if not url:
            logger.warning(f"[RSS] No URL for feed {feed.name}")
            self._record_failure(feed.name)
            return []

        for attempt in range(self.max_retries):
            try:
                response = self._session.get(
                    url,
                    headers=self._headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                # 解析 XML
                root = ET.fromstring(response.content)

                # 检测格式
                items = root.findall(".//item")
                is_atom = len(items) == 0
                if is_atom:
                    items = root.findall(".//entry")

                if len(items) == 0:
                    logger.warning(f"[RSS] No items found in {feed.name}")
                    self._record_failure(feed.name)
                    return []

                results: List[RSSNewsItem] = []
                for item in items[:10]:  # 限制每源数量
                    try:
                        # 提取标题
                        title_elem = item.find("title")
                        title = title_elem.text if title_elem is not None and title_elem.text else ""

                        if not title:
                            continue

                        # 提取链接
                        link = ""
                        if is_atom:
                            link_elem = item.find("link")
                            if link_elem is not None:
                                link = link_elem.get("href", "") or link_elem.text or ""
                        else:
                            link_elem = item.find("link")
                            link = link_elem.text if link_elem is not None and link_elem.text else ""

                        # 提取日期
                        pub_date = None
                        if is_atom:
                            pub_date_elem = item.find("published") or item.find("updated")
                        else:
                            pub_date_elem = item.find("pubDate")

                        if pub_date_elem is not None and pub_date_elem.text:
                            pub_date = self._parse_date(pub_date_elem.text)

                        # 提取描述
                        description = ""
                        desc_elem = item.find("description")
                        if desc_elem is not None and desc_elem.text:
                            # 清理 HTML
                            import re
                            description = re.sub(r'<[^>]+>', '', desc_elem.text)[:200]

                        # 提取图片
                        image_url = self._extract_image_url(item)

                        # 威胁分类
                        threat = self._classify_threat(title)
                        is_alert_level = is_alert(threat)

                        results.append(RSSNewsItem(
                            source=feed.name,
                            title=title.strip(),
                            link=link.strip(),
                            pub_date=pub_date,
                            description=description,
                            image_url=image_url,
                            lang=feed.lang or "en",
                            threat=threat,
                            is_alert=is_alert_level,
                        ))

                    except Exception as e:
                        logger.debug(f"[RSS] Error parsing item in {feed.name}: {e}")
                        continue

                # 缓存结果
                self._set_cached(feed, results)
                self._record_success(feed.name)

                logger.info(f"[RSS] {feed.name}: fetched {len(results)} items")
                return results

            except requests.RequestException as e:
                logger.warning(f"[RSS] {feed.name} attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    self._record_failure(feed.name)
            except Exception as e:
                logger.error(f"[RSS] {feed.name} error: {e}")
                self._record_failure(feed.name)
                break

        return []

    def fetch_feed(self, feed: Feed) -> List[RSSNewsItem]:
        """获取单个 RSS 源"""
        self._cleanup_cache()
        return self._fetch_single_feed(feed)

    async def fetch_feed_async(self, feed: Feed) -> List[RSSNewsItem]:
        """异步获取单个 RSS 源"""
        return await asyncio.to_thread(self.fetch_feed, feed)

    def fetch_multiple(
        self,
        feeds: Optional[List[Feed]] = None,
        categories: Optional[List[str]] = None,
        lang: str = "en",
        max_tier: int = 2,
        max_items_per_feed: int = 10,
    ) -> List[RSSNewsItem]:
        """批量获取多个 RSS 源

        Args:
            feeds: 指定 RSS 源列表
            categories: 指定分类列表
            lang: 语言
            max_tier: 最大信任层级
            max_items_per_feed: 每源最大条目数

        Returns:
            List[RSSNewsItem]: 新闻列表
        """
        # 确定要获取的 feeds
        if feeds:
            target_feeds = feeds
        elif categories:
            target_feeds = []
            for cat in categories:
                target_feeds.extend(get_feeds_by_category(cat, lang))
        else:
            target_feeds = get_all_feeds(lang, max_tier)

        # 过滤到指定层级
        target_feeds = [f for f in target_feeds if f.tier <= max_tier]

        logger.info(f"[RSS] Fetching {len(target_feeds)} feeds...")

        # 串行获取 (可改为并行)
        all_items: List[RSSNewsItem] = []

        for feed in target_feeds:
            items = self._fetch_single_feed(feed)
            # 限制数量
            all_items.extend(items[:max_items_per_feed])

        # 按日期排序 (处理时区aware/naive比较)
        def get_sort_key(item: RSSNewsItem) -> float:
            if item.pub_date is None:
                return 0
            # 转换为timestamp进行比较
            try:
                return item.pub_date.timestamp()
            except:
                return 0

        all_items.sort(key=get_sort_key, reverse=True)

        logger.info(f"[RSS] Total: {len(all_items)} items from {len(target_feeds)} feeds")

        # 统计
        alert_items = [i for i in all_items if i.is_alert]
        if alert_items:
            logger.info(f"[RSS] Alert items: {len(alert_items)}")

        return all_items

    async def fetch_multiple_async(
        self,
        feeds: Optional[List[Feed]] = None,
        categories: Optional[List[str]] = None,
        lang: str = "en",
        max_tier: int = 2,
        max_items_per_feed: int = 10,
    ) -> List[RSSNewsItem]:
        """异步批量获取"""
        return await asyncio.to_thread(
            self.fetch_multiple,
            feeds, categories, lang, max_tier, max_items_per_feed
        )

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "cached_feeds": len(self._feed_cache),
            "failed_feeds": len(self._feed_failures),
            "failures": {
                name: {"count": f.count, "cooldown_until": f.cooldown_until}
                for name, f in self._feed_failures.items()
            }
        }

    def close(self) -> None:
        """关闭"""
        if self._session:
            self._session.close()


# 便捷函数
def create_rss_fetcher(proxy_url: Optional[str] = None) -> RSSFetcher:
    """创建 RSS 获取器"""
    return RSSFetcher(proxy_url=proxy_url)

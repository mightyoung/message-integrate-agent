# coding=utf-8
"""
Intelligence Fetcher - 情报数据获取

基于 TrendRadar DataFetcher 重构:
- 支持 NewsNow API 数据获取
- 代理支持
- 自动重试机制

参考: TrendRadar/crawler/fetcher.py
"""
import json
import time
from typing import Dict, List, Optional, Tuple, Union

import requests
from loguru import logger


class NewsItem:
    """新闻条目"""

    def __init__(
        self,
        platform: str,
        title: str,
        url: str,
        timestamp: Optional[str] = None,
        summary: Optional[str] = None,
    ):
        self.platform = platform
        self.title = title
        self.url = url
        self.timestamp = timestamp or ""
        self.summary = summary or ""

    def to_dict(self) -> Dict:
        return {
            "platform": self.platform,
            "title": self.title,
            "url": self.url,
            "timestamp": self.timestamp,
            "summary": self.summary,
        }


class IntelligenceFetcher:
    """情报获取器

    从多个平台获取热点情报:
    - NewsNow API
    - RSS 订阅源
    - 自定义数据源
    """

    # 默认 API 地址
    DEFAULT_API_URL = "https://newsnow.busiyi.world/api/s"

    # 默认请求头
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }

    # 支持的平台列表
    PLATFORMS = {
        "zhihu": "知乎",
        "weibo": "微博",
        "bilibili": "B站",
        "douyin": "抖音",
        "xiaohongshu": "小红书",
        "toutiao": "今日头条",
        "baidu": "百度",
        "zhihu": "知乎",
        "csdn": "CSDN",
        "juejin": "掘金",
        "36kr": "36氪",
        "虎嗅": "huxiu",
        "techcrunch": "TechCrunch",
        "wired": "Wired",
    }

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        """初始化情报获取器

        Args:
            proxy_url: 代理服务器 URL
            api_url: API 基础 URL
        """
        self.proxy_url = proxy_url
        self.api_url = api_url or self.DEFAULT_API_URL

    def fetch_data(
        self,
        platform_id: str,
        max_retries: int = 2,
    ) -> Tuple[Optional[str], str, str]:
        """获取指定平台数据

        Args:
            platform_id: 平台 ID
            max_retries: 最大重试次数

        Returns:
            (响应文本, 平台ID, 状态) 元组
        """
        url = f"{self.api_url}?id={platform_id}&latest"

        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(
                    url,
                    proxies=proxies,
                    headers=self.DEFAULT_HEADERS,
                    timeout=10,
                )
                response.raise_for_status()

                data_text = response.text
                data_json = json.loads(data_text)

                status = data_json.get("status", "未知")
                if status not in ["success", "cache"]:
                    raise ValueError(f"响应状态异常: {status}")

                status_info = "最新数据" if status == "success" else "缓存数据"
                logger.info(f"获取 {platform_id} 成功（{status_info}）")

                return data_text, platform_id, status_info

            except Exception as e:
                retries += 1
                wait_time = min(3 * retries, 10)
                logger.warning(f"获取 {platform_id} 失败 (重试 {retries}/{max_retries}): {e}")
                if retries <= max_retries:
                    time.sleep(wait_time)

        return None, platform_id, "失败"

    def fetch_multiple(
        self,
        platform_ids: List[str],
    ) -> List[NewsItem]:
        """批量获取多个平台数据

        Args:
            platform_ids: 平台 ID 列表

        Returns:
            List[NewsItem]: 新闻条目列表
        """
        results = []

        for platform_id in platform_ids:
            data, _, status = self.fetch_data(platform_id)
            if data:
                items = self._parse_data(data, platform_id)
                results.extend(items)

        logger.info(f"批量获取完成: {len(results)} 条新闻")
        return results

    def _parse_data(self, data_text: str, platform: str) -> List[NewsItem]:
        """解析数据为 NewsItem 列表

        Args:
            data_text: 原始数据文本
            platform: 平台 ID

        Returns:
            List[NewsItem]: 新闻条目列表
        """
        try:
            data_json = json.loads(data_text)
            # 支持两种格式: "items" 或 "data"
            items = data_json.get("items") or data_json.get("data", [])

            news_items = []
            for item in items:
                # 提取标题和 URL
                title = item.get("title", "")
                url = item.get("url", "") or item.get("mobileUrl", "")
                # 使用 updatedTime 作为时间戳
                timestamp = ""
                if data_json.get("updatedTime"):
                    timestamp = str(data_json.get("updatedTime"))

                if title and url:
                    news_items.append(
                        NewsItem(
                            platform=platform,
                            title=title,
                            url=url,
                            timestamp=timestamp,
                        )
                    )

            return news_items

        except Exception as e:
            logger.error(f"解析数据失败: {e}")
            return []

    def list_platforms(self) -> List[Dict]:
        """列出支持的平台

        Returns:
            List[Dict]: 平台列表
        """
        return [
            {"id": pid, "name": name}
            for pid, name in self.PLATFORMS.items()
        ]


# ==================== 便捷函数 ====================


def create_intelligence_fetcher(
    proxy_url: Optional[str] = None,
) -> IntelligenceFetcher:
    """创建情报获取器

    Args:
        proxy_url: 代理 URL

    Returns:
        IntelligenceFetcher: 情报获取器实例
    """
    return IntelligenceFetcher(proxy_url=proxy_url)


# ==================== 测试 ====================

if __name__ == "__main__":
    # 测试获取
    fetcher = create_intelligence_fetcher()

    # 获取微博数据
    data, platform, status = fetcher.fetch_data("weibo")
    print(f"平台: {platform}, 状态: {status}")

    # 解析数据
    if data:
        items = fetcher._parse_data(data, platform)
        print(f"获取到 {len(items)} 条新闻")
        for item in items[:3]:
            print(f"- {item.title[:50]}...")

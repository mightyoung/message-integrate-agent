# coding=utf-8
"""
Storage Manager - 统一存储管理

整合 PostgresClient, S3Client, Redis 的统一入口
"""
import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

from loguru import logger

from .postgres_client import PostgresClient, IntelligenceRecord
from .s3_client import S3Client
from .redis_client import RedisClient
from .md_generator import MDGenerator, NewsItem


class StorageManager:
    """统一存储管理器

    提供情报数据的存储和检索功能:
    - PostgreSQL: 结构化数据存储 + 向量搜索
    - S3: Markdown 文件存储
    - Redis: 去重缓存
    """

    def __init__(
        self,
        enable_postgres: bool = True,
        enable_s3: bool = True,
        enable_redis: bool = True,
        redis_client: Optional[RedisClient] = None,
    ):
        """初始化存储管理器

        Args:
            enable_postgres: 是否启用 PostgreSQL
            enable_s3: 是否启用 S3
            enable_redis: 是否启用 Redis
            redis_client: 可选的 Redis 客户端 (用于测试)
        """
        self.enable_postgres = enable_postgres
        self.enable_s3 = enable_s3
        self.enable_redis = enable_redis

        # 初始化各存储客户端
        self._postgres: Optional[PostgresClient] = None
        self._s3: Optional[S3Client] = None
        self._redis: Optional[RedisClient] = redis_client  # 允许注入 Redis 客户端
        self._md_generator = MDGenerator()

        # 去重相关
        self._dedup_prefix_url = "dedup:url:"
        self._dedup_prefix_title = "dedup:title:"
        self._dedup_expire = 7 * 24 * 3600  # 7天

    @property
    def postgres(self) -> Optional[PostgresClient]:
        """获取 PostgreSQL 客户端 (懒加载)"""
        if self._postgres is None and self.enable_postgres:
            try:
                self._postgres = PostgresClient()
            except Exception as e:
                logger.warning(f"PostgreSQL 连接失败: {e}")
                self.enable_postgres = False
        return self._postgres

    @property
    def s3(self) -> Optional[S3Client]:
        """获取 S3 客户端 (懒加载)"""
        if self._s3 is None and self.enable_s3:
            try:
                self._s3 = S3Client()
            except Exception as e:
                logger.warning(f"S3 连接失败: {e}")
                self.enable_s3 = False
        return self._s3

    @property
    def redis(self) -> Optional[RedisClient]:
        """获取 Redis 客户端 (懒加载)"""
        if self._redis is None and self.enable_redis:
            try:
                self._redis = RedisClient()
            except Exception as e:
                logger.warning(f"Redis 连接失败: {e}")
                self.enable_redis = False
        return self._redis

    # ==================== 去重功能 ====================

    def check_duplicate(self, url: str, title: str, source: str) -> bool:
        """检查是否重复

        Args:
            url: 文章 URL
            title: 文章标题
            source: 来源 (rss, weibo, etc.)

        Returns:
            True if duplicate, False otherwise
        """
        if not self.redis:
            return False

        # 检查 URL
        if url:
            url_key = f"{self._dedup_prefix_url}{url}"
            if self.redis.exists(url_key):
                logger.debug(f"URL 重复: {url}")
                return True

        # 检查标题+来源
        if title and source:
            title_key = f"{self._dedup_prefix_title}{source}:{title}"
            if self.redis.exists(title_key):
                logger.debug(f"标题重复: {title}")
                return True

        return False

    def mark_processed(self, url: str, title: str, source: str):
        """标记为已处理

        Args:
            url: 文章 URL
            title: 文章标题
            source: 来源
        """
        if not self.redis:
            return

        # 标记 URL
        if url:
            url_key = f"{self._dedup_prefix_url}{url}"
            self.redis.set(url_key, "1", expire=self._dedup_expire)

        # 标记标题+来源
        if title and source:
            title_key = f"{self._dedup_prefix_title}{source}:{title}"
            self.redis.set(title_key, "1", expire=self._dedup_expire)

    def deduplicate_items(self, items: List[NewsItem], source: str) -> List[NewsItem]:
        """对情报列表去重

        Args:
            items: 情报列表
            source: 来源标识

        Returns:
            去重后的情报列表
        """
        unique_items = []
        for item in items:
            if not self.check_duplicate(item.url, item.title, source):
                unique_items.append(item)
                self.mark_processed(item.url, item.title, source)
            else:
                logger.debug(f"去重: {item.title[:30]}...")

        logger.info(f"去重: {len(items)} -> {len(unique_items)}")
        return unique_items

    # ==================== 向量生成 ====================

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """使用 Qwen API 生成向量

        Args:
            text: 文本内容

        Returns:
            向量列表，失败返回 None
        """
        try:
            import httpx

            api_key = os.environ.get("QWEN_API_KEY")
            if not api_key:
                logger.warning("QWEN_API_KEY 未配置，无法生成向量")
                return None

            model = os.environ.get("QWEN_EMBEDDING_MODEL", "text-embedding-v4")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "input": text[:8000],  # 限制长度
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("data", [{}])[0].get("embedding", [])
                    logger.debug(f"生成向量成功, 维度: {len(embedding)}")
                    return embedding
                else:
                    logger.warning(f"生成向量失败: {response.status_code} - {response.text[:200]}")
                    return None

        except Exception as e:
            logger.error(f"生成向量异常: {e}")
            return None

    # ==================== 存储功能 ====================

    async def save_intelligence(
        self,
        news_item: NewsItem,
        analysis_result: Dict[str, Any],
    ) -> bool:
        """保存情报到数据库和 S3

        Args:
            news_item: 新闻条目
            analysis_result: 分析结果

        Returns:
            是否成功
        """
        try:
            # 1. 生成向量
            content_for_embedding = f"{news_item.title}\n{news_item.content or news_item.summary}"
            embedding = await self.generate_embedding(content_for_embedding)

            # 2. 存入 PostgreSQL
            if self.postgres:
                # 来源类型映射
                source_type_map = {"rss": 1, "weibo": 2, "zhihu": 3, "bilibili": 4, "huggingface": 5}
                source_type = source_type_map.get(news_item.source_type, 0)

                # 生成 info_id
                info_id = str(abs(hash(news_item.url)) % 1000000)

                # 准备 metadata (转换为 JSON 字符串)
                metadata_dict = {
                    "analysis": analysis_result,
                    "source": news_item.source,
                    "quality_score": news_item.quality_score,
                }

                self.postgres.insert_intelligence(
                    info_id=info_id,
                    content=news_item.content or "",
                    summary=analysis_result.get("summary", news_item.summary),
                    embedding=embedding,
                    source_type=source_type,
                    title=news_item.title,
                    url=news_item.url,
                    metadata=json.dumps(metadata_dict),
                )
                logger.info(f"已存入 PostgreSQL: {news_item.title[:30]}...")

            # 3. 生成 Markdown 并上传 S3
            if self.s3:
                md_content = self._generate_markdown(news_item, analysis_result)
                s3_key = self._get_s3_key(news_item)

                self.s3.upload_text(
                    content=md_content,
                    key=s3_key,
                    content_type="text/markdown",
                )
                logger.info(f"已上传 S3: {s3_key}")

            return True

        except Exception as e:
            logger.error(f"保存情报失败: {e}")
            return False

    def _generate_markdown(self, news_item: NewsItem, analysis_result: Dict[str, Any]) -> str:
        """生成 Markdown 内容

        Args:
            news_item: 新闻条目
            analysis_result: 分析结果

        Returns:
            Markdown 格式字符串
        """
        lines = []

        # 标题
        lines.append(f"# {news_item.title}")
        lines.append("")

        # 元信息
        lines.append(f"**来源**: {news_item.source}")
        if news_item.published_at:
            lines.append(f"**发布时间**: {news_item.published_at}")
        lines.append("")

        # 摘要
        summary = analysis_result.get("summary", news_item.summary)
        if summary:
            lines.append(f"## 摘要")
            lines.append(summary)
            lines.append("")

        # 分类和评分
        category = analysis_result.get("category", "unknown")
        score = analysis_result.get("relevance_score", 0)
        lines.append(f"**分类**: {category} | **评分**: {score:.2f}")
        lines.append("")

        # 详细内容
        if news_item.content:
            lines.append("## 详细内容")
            lines.append(news_item.content)
            lines.append("")

        # 原文链接
        if news_item.url:
            lines.append(f"**原文链接**: [查看原文]({news_item.url})")

        return "\n".join(lines)

    def _get_s3_key(self, news_item: NewsItem) -> str:
        """生成 S3 存储路径

        Args:
            news_item: 新闻条目

        Returns:
            S3 key
        """
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")
        source = news_item.source_type or "unknown"

        # 生成文件名
        title_slug = "".join(c if c.isalnum() else "_" for c in news_item.title[:50])
        filename = f"{now.strftime('%H%M%S')}_{title_slug}.md"

        return f"intelligence/{date_path}/{source}/{filename}"

    # ==================== 检索功能 ====================

    async def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """相似度搜索

        Args:
            query: 查询文本
            limit: 返回数量

        Returns:
            相似情报列表
        """
        if not self.postgres:
            return []

        # 生成查询向量
        embedding = await self.generate_embedding(query)
        if not embedding:
            return []

        # 搜索
        results = self.postgres.search_similar(embedding, limit=limit)
        return results


# 全局单例
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """获取全局存储管理器实例"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager


async def create_storage_manager(
    enable_postgres: bool = True,
    enable_s3: bool = True,
    enable_redis: bool = True,
    redis_client: Optional[RedisClient] = None,
) -> StorageManager:
    """创建存储管理器实例

    Args:
        enable_postgres: 是否启用 PostgreSQL
        enable_s3: 是否启用 S3
        enable_redis: 是否启用 Redis
        redis_client: 可选的 Redis 客户端 (用于测试)

    Returns:
        StorageManager 实例
    """
    global _storage_manager
    _storage_manager = StorageManager(
        enable_postgres=enable_postgres,
        enable_s3=enable_s3,
        enable_redis=enable_redis,
        redis_client=redis_client,
    )
    return _storage_manager

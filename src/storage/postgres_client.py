# coding=utf-8
"""
PostgreSQL Client - pgvector 向量存储

存储情报信息并进行相似度搜索
"""
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import psycopg2
from psycopg2 import sql
from loguru import logger


@dataclass
class IntelligenceRecord:
    """情报记录"""
    id: Optional[int] = None
    info_id: str = ""
    content: str = ""
    summary: str = ""
    embedding: Optional[List[float]] = None
    source_type: int = 0
    source_id: int = 0
    title: str = ""
    url: str = ""
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None


class PostgresClient:
    """PostgreSQL 客户端 - 支持 pgvector 向量存储"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None,
    ):
        """初始化 PostgreSQL 客户端

        Args:
            host: 主机地址
            port: 端口
            user: 用户名
            password: 密码
            database: 数据库名
        """
        # 从环境变量读取或使用传入的参数
        self.host = host or os.environ.get("PG_HOST", "localhost")
        self.port = port or int(os.environ.get("PG_PORT", "5432"))
        self.user = user or os.environ.get("PG_USER", "postgres")
        self.password = password or os.environ.get("PG_PASSWORD", "postgres")
        self.database = database or os.environ.get("PG_DB_NAME", "intelligence_db")

        self.conn = None
        self._connect()

        logger.info(f"PostgresClient initialized: {self.database} @ {self.host}:{self.port}")

    def _connect(self):
        """建立数据库连接"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
            )
            self.conn.autocommit = True
        except psycopg2.OperationalError as e:
            # 数据库可能不存在，尝试创建
            logger.warning(f"Database {self.database} not found, attempting to create...")
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
            )
            self.conn.autocommit = True
            self._create_database()
            self.conn.close()
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
            )
            self.conn.autocommit = True
            self._init_extensions()
            self._create_tables()

    def _create_database(self):
        """创建数据库"""
        cursor = self.conn.cursor()
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier(self.database)
        ))
        cursor.close()
        logger.info(f"Database {self.database} created")

    def _init_extensions(self):
        """初始化扩展"""
        cursor = self.conn.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cursor.close()

    def _create_tables(self):
        """创建表"""
        cursor = self.conn.cursor()

        # 情报信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intelligence_info (
                id SERIAL PRIMARY KEY,
                info_id VARCHAR(32) UNIQUE NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                embedding VECTOR(1024),
                source_type SMALLINT NOT NULL DEFAULT 0,
                source_id SMALLINT NOT NULL DEFAULT 0,
                title VARCHAR(500),
                url VARCHAR(1000),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # 创建向量索引 (HNSW)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_intelligence_embedding
            ON intelligence_info
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)

        # 创建时间索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_intelligence_created_at
            ON intelligence_info(created_at DESC)
        """)

        # 创建来源索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_intelligence_source
            ON intelligence_info(source_type, source_id)
        """)

        cursor.close()
        logger.info("Database tables initialized")

    def insert_intelligence(
        self,
        info_id: str,
        content: str,
        summary: str = "",
        embedding: List[float] = None,
        source_type: int = 0,
        source_id: int = 0,
        title: str = "",
        url: str = "",
        metadata: Dict[str, Any] = None,
    ) -> int:
        """插入情报记录

        Args:
            info_id: InfoID
            content: 原始内容
            summary: 摘要
            embedding: 向量
            source_type: 来源类型
            source_id: 来源ID
            title: 标题
            url: 原文链接
            metadata: 附加数据

        Returns:
            记录 ID
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO intelligence_info
            (info_id, content, summary, embedding, source_type, source_id, title, url, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (info_id) DO UPDATE
            SET content = EXCLUDED.content,
                summary = EXCLUDED.summary,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata
            RETURNING id
        """, (
            info_id,
            content,
            summary,
            embedding,
            source_type,
            source_id,
            title,
            url,
            metadata or {},
        ))

        result = cursor.fetchone()
        record_id = result[0] if result else None
        cursor.close()

        logger.info(f"Inserted intelligence record: {info_id}")
        return record_id

    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 5,
        source_type: int = None,
    ) -> List[Dict[str, Any]]:
        """相似度搜索

        Args:
            query_embedding: 查询向量
            limit: 返回数量限制
            source_type: 来源类型过滤

        Returns:
            相似记录列表
        """
        cursor = self.conn.cursor()

        # 构建查询
        query = """
            SELECT
                id, info_id, content, summary, source_type, source_id,
                title, url, metadata, created_at,
                (embedding <=> %s::vector) as distance
            FROM intelligence_info
            WHERE embedding IS NOT NULL
        """
        params = [query_embedding]

        if source_type is not None:
            query += " AND source_type = %s"
            params.append(source_type)

        query += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([query_embedding, limit])

        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "info_id": row[1],
                "content": row[2],
                "summary": row[3],
                "source_type": row[4],
                "source_id": row[5],
                "title": row[6],
                "url": row[7],
                "metadata": row[8],
                "created_at": row[9],
                "distance": row[10],
            })

        cursor.close()
        return results

    def get_by_info_id(self, info_id: str) -> Optional[Dict[str, Any]]:
        """根据 InfoID 获取记录

        Args:
            info_id: InfoID

        Returns:
            记录或 None
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, info_id, content, summary, source_type, source_id,
                   title, url, metadata, created_at
            FROM intelligence_info
            WHERE info_id = %s
        """, (info_id,))

        row = cursor.fetchone()
        cursor.close()

        if not row:
            return None

        return {
            "id": row[0],
            "info_id": row[1],
            "content": row[2],
            "summary": row[3],
            "source_type": row[4],
            "source_id": row[5],
            "title": row[6],
            "url": row[7],
            "metadata": row[8],
            "created_at": row[9],
        }

    def list_recent(self, limit: int = 10, source_type: int = None) -> List[Dict[str, Any]]:
        """获取最近的情报

        Args:
            limit: 返回数量限制
            source_type: 来源类型过滤

        Returns:
            记录列表
        """
        cursor = self.conn.cursor()

        query = """
            SELECT id, info_id, content, summary, source_type, source_id,
                   title, url, metadata, created_at
            FROM intelligence_info
        """
        params = []

        if source_type is not None:
            query += " WHERE source_type = %s"
            params.append(source_type)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "info_id": row[1],
                "content": row[2],
                "summary": row[3],
                "source_type": row[4],
                "source_id": row[5],
                "title": row[6],
                "url": row[7],
                "metadata": row[8],
                "created_at": row[9],
            })

        cursor.close()
        return results

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            logger.info("PostgreSQL connection closed")


def create_postgres_client() -> PostgresClient:
    """创建 PostgreSQL 客户端的便捷函数"""
    return PostgresClient()

# coding=utf-8
"""
S3 Client - RustFs Storage Integration

将收集到的信息转换为 MD 文件并上传到 S3 存储
"""
import os
from datetime import datetime
from typing import Optional, List
from pathlib import Path

import boto3
from botocore.config import Config
from loguru import logger


class S3Client:
    """S3 客户端 - 支持 RustFs/MinIO 等 S3 兼容存储"""

    def __init__(
        self,
        endpoint_url: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket_name: str = None,
        region_name: str = "us-east-1",
    ):
        """初始化 S3 客户端

        Args:
            endpoint_url: S3 端点 URL
            access_key: 访问密钥
            secret_key: 秘密密钥
            bucket_name: 存储桶名称
            region_name: 区域名称
        """
        # 从环境变量读取或使用传入的参数
        self.endpoint_url = endpoint_url or os.environ.get("S3_ENDPOINT_URL")
        self.access_key = access_key or os.environ.get("S3_ACCESS_KEY")
        self.secret_key = secret_key or os.environ.get("S3_SECRET_KEY")
        self.bucket_name = bucket_name or os.environ.get("S3_BUCKET_NAME")
        self.region_name = region_name or os.environ.get("S3_REGION_NAME", "us-east-1")

        if not all([self.endpoint_url, self.access_key, self.secret_key, self.bucket_name]):
            raise ValueError("Missing S3 configuration. Check environment variables.")

        # 创建 S3 客户端
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
            config=Config(signature_version="s3v4"),
        )

        self.base_path = "message-integrate-agent"

        logger.info(f"S3Client initialized: {self.bucket_name} @ {self.endpoint_url}")

    def _get_key(self, path: str) -> str:
        """生成完整的 S3 key

        Args:
            path: 相对路径

        Returns:
            完整的 S3 key
        """
        return f"{self.base_path}/{path.lstrip('/')}"

    def upload_text(
        self,
        content: str,
        key: str,
        content_type: str = "text/markdown",
    ) -> str:
        """上传文本内容到 S3

        Args:
            content: 文本内容
            key: S3 key (相对于基础路径)
            content_type: 内容类型

        Returns:
            完整的 S3 URL
        """
        full_key = self._get_key(key)

        self.client.put_object(
            Bucket=self.bucket_name,
            Key=full_key,
            Body=content.encode("utf-8"),
            ContentType=content_type,
        )

        url = f"{self.endpoint_url}/{self.bucket_name}/{full_key}"
        logger.info(f"Uploaded to S3: {url}")
        return url

    def upload_md(
        self,
        content: str,
        folder: str,
        filename: str = None,
    ) -> str:
        """上传 Markdown 文件

        Args:
            content: Markdown 内容
            folder: 文件夹名称 (如 'intelligence/2026-03-08')
            filename: 文件名 (如 'digest.md', 默认自动生成)

        Returns:
            完整的 S3 URL
        """
        # 生成文件名
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"digest_{timestamp}.md"

        # 构建完整路径
        path = f"{folder}/{filename}"

        return self.upload_text(content, path, "text/markdown")

    def upload_intelligence_digest(
        self,
        content: str,
        date: str = None,
        category: str = "general",
    ) -> str:
        """上传情报摘要

        Args:
            content: Markdown 内容
            date: 日期 (如 '2026-03-08', 默认今天)
            category: 分类 (如 'tech', 'military', 'geopolitics')

        Returns:
            完整的 S3 URL
        """
        date = date or datetime.now().strftime("%Y-%m-%d")
        folder = f"intelligence/{date}/{category}"

        return self.upload_md(content, folder)

    def download(self, key: str) -> str:
        """从 S3 下载内容

        Args:
            key: S3 key

        Returns:
            文件内容
        """
        full_key = self._get_key(key)

        response = self.client.get_object(
            Bucket=self.bucket_name,
            Key=full_key,
        )

        return response["Body"].read().decode("utf-8")

    def list_files(self, prefix: str = "") -> List[str]:
        """列出文件

        Args:
            prefix: 前缀

        Returns:
            文件列表
        """
        full_prefix = self._get_key(prefix)

        response = self.client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=full_prefix,
        )

        if "Contents" not in response:
            return []

        return [obj["Key"] for obj in response["Contents"]]

    def delete(self, key: str):
        """删除文件

        Args:
            key: S3 key
        """
        full_key = self._get_key(key)

        self.client.delete_object(
            Bucket=self.bucket_name,
            Key=full_key,
        )

        logger.info(f"Deleted from S3: {full_key}")

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """获取预签名 URL

        Args:
            key: S3 key
            expires_in: 过期时间(秒)

        Returns:
            预签名 URL
        """
        full_key = self._get_key(key)

        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": full_key},
            ExpiresIn=expires_in,
        )

        return url


def create_s3_client() -> S3Client:
    """创建 S3 客户端的便捷函数"""
    return S3Client()

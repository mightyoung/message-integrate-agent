# coding=utf-8
"""
GitHub README Fetcher & Summarizer - 获取并总结 README.md

功能:
1. 获取仓库的 README.md 内容
2. 使用 LLM 生成项目简要说明
"""
import os
import re
import base64
import asyncio
from typing import Optional, List, Dict, Any
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import httpx

from loguru import logger


TIMEOUT = 30
MAX_README_SIZE = 50000  # 50KB max


class ReadmeFetcher:
    """README.md 获取器"""

    # README 文件名候选列表
    README_NAMES = [
        "README.md",
        "README.rst",
        "README.txt",
        "README",
        "readme.md",
        "README.MD",
    ]

    def __init__(self, github_token: str = None):
        """初始化

        Args:
            github_token: GitHub Token (可选)
        """
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self._headers = {
            "User-Agent": "MessageIntegrateAgent/1.0",
            "Accept": "application/vnd.github.v3+json",
        }
        if self.github_token:
            self._headers["Authorization"] = f"Bearer {self.github_token}"

    def fetch(self, repo: str) -> Optional[str]:
        """获取仓库的 README 内容

        Args:
            repo: 仓库名 (格式: owner/repo)

        Returns:
            README 内容或 None
        """
        # 首先尝试获取默认分支
        try:
            # 获取仓库信息
            url = f"https://api.github.com/repos/{repo}"
            req = Request(url, headers=self._headers)
            with urlopen(req, timeout=TIMEOUT) as resp:
                repo_info = httpx._models.JSONResponse(
                    status_code=resp.status,
                    headers=dict(resp.headers),
                    content=resp.read(),
                ).json()

            default_branch = repo_info.get("default_branch", "main")
        except Exception as e:
            logger.warning(f"获取仓库信息失败 {repo}: {e}")
            default_branch = "main"

        # 尝试获取 README
        for readme_name in self.README_NAMES:
            content = self._try_fetch_readme(repo, default_branch, readme_name)
            if content:
                return content

        return None

    def _try_fetch_readme(
        self, repo: str, branch: str, readme_name: str
    ) -> Optional[str]:
        """尝试获取指定分支的 README"""
        # 方法1: 使用 GitHub Contents API
        try:
            url = f"https://api.github.com/repos/{repo}/contents/{readme_name}?ref={branch}"
            req = Request(url, headers=self._headers)
            with urlopen(req, timeout=TIMEOUT) as resp:
                data = httpx._models.JSONResponse(
                    status_code=resp.status,
                    headers=dict(resp.headers),
                    content=resp.read(),
                ).json()

            if data.get("encoding") == "base64" and data.get("content"):
                content = base64.b64decode(data["content"]).decode("utf-8")
                if len(content) <= MAX_README_SIZE:
                    return content
        except Exception:
            pass

        # 方法2: 直接从原始 URL 获取
        try:
            raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{readme_name}"
            req = Request(raw_url, headers=self._headers)
            with urlopen(req, timeout=TIMEOUT) as resp:
                content = resp.read().decode("utf-8")
                if len(content) <= MAX_README_SIZE:
                    return content
        except Exception:
            pass

        return None

    async def fetch_async(self, repo: str) -> Optional[str]:
        """异步获取 README"""
        return await asyncio.to_thread(self.fetch, repo)

    def fetch_multiple(self, repos: List[str]) -> Dict[str, str]:
        """批量获取多个仓库的 README

        Args:
            repos: 仓库列表

        Returns:
            {repo: README内容} 字典
        """
        results = {}
        for repo in repos:
            content = self.fetch(repo)
            if content:
                results[repo] = content
        return results


class ReadmeSummarizer:
    """README 摘要生成器"""

    def __init__(self, llm_client=None):
        """初始化

        Args:
            llm_client: LLM 客户端 (需要实现 chat 方法)
        """
        self.llm_client = llm_client

    def summarize(self, readme_content: str, repo_name: str = "") -> str:
        """生成 README 摘要

        Args:
            readme_content: README 内容
            repo_name: 仓库名

        Returns:
            摘要文本
        """
        # 预处理: 移除多余的空白和 Markdown
        content = self._preprocess(readme_content)

        # 截取前 8000 字符 (足够理解项目)
        content = content[:8000]

        # 如果没有 LLM 客户端，使用规则提取
        if not self.llm_client:
            return self._rule_based_summary(content, repo_name)

        # 使用 LLM 生成摘要
        prompt = f"""请阅读以下 GitHub 项目的 README 文件，生成一个简短的项目简介（50-100字）。

项目名称: {repo_name}

README 内容:
{content}

请直接输出项目简介，不要有额外解释。"""

        try:
            response = asyncio.run(
                self.llm_client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                )
            )
            return response.get("content", "").strip()
        except Exception as e:
            logger.warning(f"LLM 摘要生成失败: {e}")
            return self._rule_based_summary(content, repo_name)

    def _preprocess(self, content: str) -> str:
        """预处理 README 内容"""
        # 移除 Markdown 标题
        content = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)
        # 移除代码块
        content = re.sub(r"```[^`]*```", "", content, flags=re.DOTALL)
        # 移除链接 [text](url)
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
        # 移除图片
        content = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", content)
        # 移除多余空白
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()

    def _rule_based_summary(self, content: str, repo_name: str) -> str:
        """基于规则的摘要生成"""
        lines = content.split("\n")

        # 提取前几行作为简介
        summary_lines = []
        for line in lines[:10]:
            line = line.strip()
            if line and not line.startswith("!"):
                # 移除常见前缀
                line = re.sub(r"^[-*]\s*", "", line)
                if len(line) > 10:
                    summary_lines.append(line)
            if len(summary_lines) >= 3:
                break

        if summary_lines:
            return " | ".join(summary_lines[:2])

        # 如果无法提取，返回仓库名
        return f"GitHub 仓库: {repo_name}"


class GitHubRepoInfo:
    """GitHub 仓库信息 (包含 README 摘要)"""

    def __init__(
        self,
        trending_item,
        readme_content: str = None,
        summary: str = None,
    ):
        self.repo = trending_item.repo
        self.name = trending_item.name
        self.description = trending_item.description
        self.url = trending_item.url
        self.stars = trending_item.stars
        self.daily_stars_est = trending_item.daily_stars_est
        self.forks = trending_item.forks
        self.language = trending_item.language
        self.topics = trending_item.topics
        self.readme_content = readme_content
        self.summary = summary or trending_item.description

    def to_message(self) -> str:
        """转换为消息格式"""
        lines = []

        # 标题和星数
        lines.append(f"**⭐ {self.name}** ({self.stars} ⭐)")

        # 语言和每日增长
        lang_info = f"🔤 {self.language}" if self.language else ""
        if self.daily_stars_est > 0:
            lang_info += f" | 📈 +{self.daily_stars_est}/天"
        if lang_info:
            lines.append(lang_info)

        # 简要说明
        if self.summary:
            lines.append(f"> {self.summary[:200]}")

        # 链接
        lines.append(f"[查看项目]({self.url})")

        return "\n".join(lines)


def create_readme_fetcher() -> ReadmeFetcher:
    """创建 README 获取器的便捷函数"""
    return ReadmeFetcher()


def create_readme_summarizer(llm_client=None) -> ReadmeSummarizer:
    """创建 README 摘要生成器的便捷函数"""
    return ReadmeSummarizer(llm_client=llm_client)

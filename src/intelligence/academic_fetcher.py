# coding=utf-8
"""
Academic Fetcher - 学术论文获取器

Tier 3: 学术论文 (API 直连)
- arXiv API
- PubMed API

这些学术 API 通常可以直接访问，不需要代理
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlencode

import httpx
from loguru import logger


@dataclass
class AcademicPaper:
    """学术论文"""
    source: str  # arxiv, pubmed
    title: str
    url: str
    authors: List[str]
    abstract: str
    published_date: Optional[datetime] = None
    categories: List[str] = None
    citations: Optional[int] = None

    def __post_init__(self):
        if self.categories is None:
            self.categories = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "authors": self.authors,
            "abstract": self.abstract,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "categories": self.categories,
            "citations": self.citations,
        }


class ArxivFetcher:
    """arXiv 论文获取器

    使用官方 arXiv API: http://export.arxiv.org/api/query
    """

    def __init__(self, max_results: int = 10):
        self.max_results = max_results
        self.base_url = "http://export.arxiv.org/api/query"

    async def search(self, query: str, categories: Optional[List[str]] = None) -> List[AcademicPaper]:
        """搜索 arXiv 论文

        Args:
            query: 搜索关键词
            categories: 指定分类，None 表示全部

        Returns:
            List[AcademicPaper]: 论文列表
        """
        papers = []

        try:
            # 构建查询
            search_query = query
            if categories:
                cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
                search_query = f"({query}) AND ({cat_query})"

            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": self.max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }

            url = f"{self.base_url}?{urlencode(params)}"

            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    papers = self._parse_atom_response(response.text)

        except Exception as e:
            logger.error(f"arXiv search error: {e}")

        return papers

    async def get_recent(self, category: str = "cs.AI", max_results: int = 10) -> List[AcademicPaper]:
        """获取指定分类的最新论文

        Args:
            category: arXiv 分类
            max_results: 最大数量

        Returns:
            List[AcademicPaper]: 论文列表
        """
        papers = []

        try:
            params = {
                "search_query": f"cat:{category}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }

            url = f"{self.base_url}?{urlencode(params)}"

            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    papers = self._parse_atom_response(response.text)

        except Exception as e:
            logger.error(f"arXiv recent error: {e}")

        return papers

    def _parse_atom_response(self, xml_content: str) -> List[AcademicPaper]:
        """解析 Atom 格式响应"""
        papers = []

        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_content)

            # 定义命名空间
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom',
            }

            # 查找 entry 元素
            for entry in root.findall('atom:entry', ns):
                try:
                    # 提取标题
                    title_elem = entry.find('atom:title', ns)
                    title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

                    # 提取摘要
                    summary_elem = entry.find('atom:summary', ns)
                    abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""

                    # 提取链接
                    link = ""
                    for link_elem in entry.findall('atom:link', ns):
                        if link_elem.get("type") == "text/html":
                            link = link_elem.get("href", "")
                            break
                    if not link:
                        id_elem = entry.find('atom:id', ns)
                        link = id_elem.text if id_elem is not None and id_elem.text else ""

                    # 提取作者
                    authors = []
                    for author in entry.findall('atom:author', ns):
                        name_elem = author.find('atom:name', ns)
                        if name_elem is not None and name_elem.text:
                            authors.append(name_elem.text)

                    # 提取发布日期
                    published = None
                    published_elem = entry.find('atom:published', ns)
                    if published_elem is not None and published_elem.text:
                        try:
                            published = datetime.fromisoformat(
                                published_elem.text.replace("Z", "+00:00")
                            )
                        except:
                            pass

                    # 提取分类
                    categories = []
                    for cat in entry.findall('arxiv:category', ns):
                        cat_attrib = cat.get("term")
                        if cat_attrib:
                            categories.append(cat_attrib)

                    papers.append(AcademicPaper(
                        source="arxiv",
                        title=title,
                        url=link,
                        authors=authors,
                        abstract=abstract[:500],  # 截断摘要
                        published_date=published,
                        categories=categories,
                    ))

                except Exception as e:
                    logger.debug(f"Error parsing arXiv entry: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing arXiv response: {e}")

        return papers


class PubMedFetcher:
    """PubMed 论文获取器

    使用 NCBI E-utilities API
    """

    def __init__(self, max_results: int = 10):
        self.max_results = max_results
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    async def search(self, query: str, max_results: Optional[int] = None) -> List[AcademicPaper]:
        """搜索 PubMed 论文

        Args:
            query: 搜索关键词
            max_results: 最大数量

        Returns:
            List[AcademicPaper]: 论文列表
        """
        papers = []
        max_results = max_results or self.max_results

        try:
            # Step 1: 获取 ID 列表
            search_url = f"{self.base_url}/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": max_results,
                "sort": "relevance",
            }

            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(search_url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    id_list = data.get("esearchresult", {}).get("idlist", [])

                    if not id_list:
                        return papers

                    # Step 2: 获取详情
                    fetch_url = f"{self.base_url}/esummary.fcgi"
                    params = {
                        "db": "pubmed",
                        "id": ",".join(id_list),
                        "retmode": "json",
                    }

                    response = await client.get(fetch_url, params=params)

                    if response.status_code == 200:
                        data = response.json()
                        papers = self._parse_summary_response(data)

        except Exception as e:
            logger.error(f"PubMed search error: {e}")

        return papers

    async def get_recent(self, max_results: int = 10) -> List[AcademicPaper]:
        """获取最新论文"""
        return await self.search("2024[DP]", max_results)

    def _parse_summary_response(self, data: Dict) -> List[AcademicPaper]:
        """解析摘要响应"""
        papers = []

        try:
            result = data.get("result", {})

            for uid, info in result.items():
                if uid == "uids" or not isinstance(info, dict):
                    continue

                # 提取标题
                title = info.get("title", "")

                # 提取摘要（需要单独请求，这里简化处理）
                abstract = ""

                # 提取作者
                authors = []
                for author in info.get("authors", []):
                    if isinstance(author, dict):
                        authors.append(author.get("name", ""))

                # 提取链接
                pubmed_id = info.get("uid", "")
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"

                # 提取发布日期
                pub_date = None
                pubdate_str = info.get("pubdate", "")
                if pubdate_str:
                    try:
                        pub_date = datetime.strptime(pubdate_str, "%Y %b %d")
                    except:
                        try:
                            pub_date = datetime.strptime(pubdate_str, "%Y")
                        except:
                            pass

                papers.append(AcademicPaper(
                    source="pubmed",
                    title=title,
                    url=url,
                    authors=authors,
                    abstract=abstract,
                    published_date=pub_date,
                    citations=info.get("pubmed_citations", 0),
                ))

        except Exception as e:
            logger.error(f"Error parsing PubMed response: {e}")

        return papers


class AcademicFetcher:
    """学术论文统一获取器

    整合 arXiv 和 PubMed
    """

    def __init__(self, max_results: int = 10):
        self.max_results = max_results

        self.fetchers = {
            "arxiv": ArxivFetcher(max_results=max_results),
            "pubmed": PubMedFetcher(max_results=max_results),
        }

    async def search(self, query: str, sources: Optional[List[str]] = None) -> List[AcademicPaper]:
        """搜索学术论文

        Args:
            query: 搜索关键词
            sources: 指定来源，None 表示全部

        Returns:
            List[AcademicPaper]: 论文列表
        """
        if sources is None:
            sources = list(self.fetchers.keys())

        tasks = []
        for source in sources:
            if source in self.fetchers:
                tasks.append(self.fetchers[source].search(query))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        papers = []
        for result in results:
            if isinstance(result, list):
                papers.extend(result)

        # 按日期排序
        papers.sort(
            key=lambda x: x.published_date.timestamp() if x.published_date else 0,
            reverse=True
        )

        return papers

    async def get_recent(self, source: str, max_results: int = 10) -> List[AcademicPaper]:
        """获取最新论文"""
        if source == "arxiv":
            return await self.fetchers["arxiv"].get_recent(max_results=max_results)
        elif source == "pubmed":
            return await self.fetchers["pubmed"].get_recent(max_results=max_results)
        return []


# 便捷函数
def create_academic_fetcher() -> AcademicFetcher:
    """创建学术论文获取器"""
    return AcademicFetcher()

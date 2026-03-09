# coding=utf-8
"""
Information Classifier - 信息分类路由器

根据查询类型将请求路由到最合适的信息源:

Tier 1: 热榜直接获取 (无需代理)
  - Hacker News, GitHub Trending, Product Hunt

Tier 2: RSS 新闻订阅 (已有实现)
  - WorldMonitor RSS 源

Tier 3: 学术论文 (API 直连)
  - arXiv, PubMed

Tier 4: 智能搜索 (Tavily 补充)
  - 仅用于特定问题深度搜索
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any


class InfoCategory(Enum):
    """信息分类"""
    HOT = "hot"        # 热榜
    NEWS = "news"     # 新闻
    PAPER = "paper"    # 学术论文
    GENERAL = "general"  # 通用搜索


@dataclass
class ClassificationResult:
    """分类结果"""
    category: InfoCategory
    confidence: float  # 置信度 0-1
    keywords_matched: List[str]
    recommended_sources: List[str]


class InformationClassifier:
    """信息分类路由器

    根据查询内容确定最合适的信息获取方式
    """

    # 分类规则
    KEYWORDS = {
        InfoCategory.HOT: [
            "trending", "hot", "top", "热搜", "趋势", "热门",
            "今日热点", "github trending", "hacker news",
            "product hunt", "最火", "爆火", "飙升",
        ],
        InfoCategory.NEWS: [
            "news", "新闻", "资讯", "今日", "最新",
            "报道", "消息", "动态", "快讯",
        ],
        InfoCategory.PAPER: [
            "paper", "论文", "arxiv", "research", "学术",
            "研究", "publication", "conference", "期刊",
        ],
    }

    # 分类对应的首选来源
    SOURCE_MAPPING = {
        InfoCategory.HOT: ["hackernews", "github_trending", "producthunt"],
        InfoCategory.NEWS: ["rss"],
        InfoCategory.PAPER: ["arxiv", "pubmed"],
        InfoCategory.GENERAL: ["tavily"],
    }

    def classify(self, query: str) -> ClassificationResult:
        """分类查询

        Args:
            query: 用户查询

        Returns:
            ClassificationResult: 分类结果
        """
        query_lower = query.lower()
        category_scores: Dict[InfoCategory, float] = {cat: 0.0 for cat in InfoCategory}
        keywords_matched: Dict[InfoCategory, List[str]] = {cat: [] for cat in InfoCategory}

        # 匹配关键词
        for category, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    category_scores[category] += 1.0
                    keywords_matched[category].append(keyword)

        # 特殊模式匹配
        # 1. 明确要求搜索
        if any(kw in query_lower for kw in ["搜索", "search", "找", "查"]):
            if not any(category_scores.values()):
                category_scores[InfoCategory.GENERAL] = 0.5

        # 2. 明确指定来源
        if "arxiv" in query_lower or "arXiv" in query:
            category_scores[InfoCategory.PAPER] += 2.0
            keywords_matched[InfoCategory.PAPER].append("arxiv")
        if "github" in query_lower:
            category_scores[InfoCategory.HOT] += 1.5
            keywords_matched[InfoCategory.HOT].append("github")
        if "hacker news" in query_lower or "hn" in query_lower:
            category_scores[InfoCategory.HOT] += 2.0
            keywords_matched[InfoCategory.HOT].append("hacker news")

        # 找出最高分类
        if not any(category_scores.values()):
            # 默认通用搜索
            return ClassificationResult(
                category=InfoCategory.GENERAL,
                confidence=0.5,
                keywords_matched=[],
                recommended_sources=["tavily"],
            )

        max_score = max(category_scores.values())
        # 归一化置信度
        total = sum(category_scores.values())
        confidence = max_score / total if total > 0 else 0.5

        # 获取最高分类
        for cat, score in category_scores.items():
            if score == max_score:
                return ClassificationResult(
                    category=cat,
                    confidence=confidence,
                    keywords_matched=keywords_matched[cat],
                    recommended_sources=self.SOURCE_MAPPING.get(cat, ["tavily"]),
                )

        # Fallback
        return ClassificationResult(
            category=InfoCategory.GENERAL,
            confidence=0.5,
            keywords_matched=[],
            recommended_sources=["tavily"],
        )

    def get_fetcher_config(self, category: InfoCategory) -> Dict[str, Any]:
        """获取分类对应的获取器配置

        Args:
            category: 信息分类

        Returns:
            Dict: 配置字典
        """
        configs = {
            InfoCategory.HOT: {
                "sources": ["hackernews", "github_trending", "producthunt"],
                "max_items": 20,
                "use_proxy": False,  # 热榜 API 通常不需要代理
            },
            InfoCategory.NEWS: {
                "sources": ["rss"],
                "categories": ["tech", "geopolitics", "business"],
                "max_items": 30,
                "use_proxy": True,
            },
            InfoCategory.PAPER: {
                "sources": ["arxiv", "pubmed"],
                "max_items": 10,
                "use_proxy": False,  # 学术 API 通常可直连
            },
            InfoCategory.GENERAL: {
                "sources": ["tavily"],
                "max_items": 10,
                "use_proxy": True,
            },
        }
        return configs.get(category, configs[InfoCategory.GENERAL])


# 全局实例
_classifier: Optional[InformationClassifier] = None


def get_classifier() -> InformationClassifier:
    """获取全局分类器实例"""
    global _classifier
    if _classifier is None:
        _classifier = InformationClassifier()
    return _classifier

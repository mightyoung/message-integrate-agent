# coding=utf-8
"""
Intelligence Analyzer - 情报 AI 分析

基于 TrendRadar AIAnalyzer 重构:
- 使用 LLM 分析新闻价值
- 多维度评分
- 摘要生成

参考: TrendRadar/ai/analyzer.py
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

from src.prompts import get_prompt


@dataclass
class AnalysisResult:
    """分析结果"""

    news_id: str
    relevance_score: float  # 相关性评分 0-1
    importance_score: float  # 重要性评分 0-1
    summary: str  # AI 生成的摘要
    category: str  # 分类
    keywords: List[str]  # 关键词
    sentiment: str  # 情感 positive/negative/neutral
    translated_title: Optional[str] = None  # 翻译后的标题 (如果是英文)
    translated_summary: Optional[str] = None  # 翻译后的摘要


class IntelligenceAnalyzer:
    """情报分析器

    使用 LLM 对新闻进行深度分析:
    - 相关性评分
    - 重要性评分
    - 自动摘要
    - 分类标签
    """

    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        """初始化分析器

        Args:
            llm_config: LLM 配置
        """
        self.llm_config = llm_config or {}
        self.default_model = self.llm_config.get("model", "deepseek-chat")

    async def analyze(self, news_item) -> AnalysisResult:
        """分析单条新闻

        Args:
            news_item: NewsItem 实例

        Returns:
            AnalysisResult: 分析结果
        """
        try:
            # 构建分析提示
            prompt = self._build_analysis_prompt(news_item)

            # 调用 LLM
            from src.mcp.tools.llm import chat_with_llm

            response = await chat_with_llm(
                prompt=prompt,
                model=self.default_model,
                system_message=get_prompt("intelligence_analyzer"),
                temperature=0.3,
            )

            # 解析结果
            result = self._parse_analysis_response(response, news_item)
            return result

        except Exception as e:
            logger.error(f"分析新闻失败: {e}")
            # 返回默认结果
            return self._default_result(news_item)

    async def translate_to_chinese(self, text: str) -> Optional[str]:
        """翻译文本为中文

        Args:
            text: 要翻译的文本

        Returns:
            翻译后的中文文本，如果失败返回 None
        """
        # 检测是否需要翻译 (简单检查是否包含英文字母)
        if not any(c.isalpha() for c in text):
            return None

        # 检查是否主要是中文
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        if chinese_chars / max(len(text), 1) > 0.3:
            return None  # 已经是中文为主

        try:
            from src.mcp.tools.llm import chat_with_llm

            prompt = f"""请将以下文本翻译成中文。只返回翻译结果，不要有任何额外解释。

文本: {text[:2000]}"""

            response = await chat_with_llm(
                prompt=prompt,
                model=self.default_model,
                system_message=get_prompt("translator"),
                temperature=0.3,
            )

            if response and not response.startswith("Error"):
                return response.strip()
        except Exception as e:
            logger.error(f"翻译失败: {e}")

        return None

    async def analyze_and_translate(self, news_item) -> AnalysisResult:
        """分析并翻译新闻

        Args:
            news_item: NewsItem 实例

        Returns:
            AnalysisResult: 包含翻译结果的分析结果
        """
        # 先分析
        result = await self.analyze(news_item)

        # 检查是否需要翻译标题和摘要
        title_translated = False
        summary_translated = False

        # 翻译标题
        if news_item.title:
            translated = await self.translate_to_chinese(news_item.title)
            if translated:
                result.translated_title = translated
                title_translated = True

        # 翻译摘要 (如果有)
        if result.summary:
            translated = await self.translate_to_chinese(result.summary)
            if translated:
                result.translated_summary = translated
                summary_translated = True

        logger.debug(f"翻译状态 - 标题: {title_translated}, 摘要: {summary_translated}")
        return result

    async def analyze_batch(
        self,
        news_items: List,
        max_concurrent: int = 5,
    ) -> List[AnalysisResult]:
        """批量分析新闻

        Args:
            news_items: 新闻列表
            max_concurrent: 最大并发数

        Returns:
            List[AnalysisResult]: 分析结果列表
        """
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_limit(item):
            async with semaphore:
                return await self.analyze(item)

        results = await asyncio.gather(
            *[analyze_with_limit(item) for item in news_items],
            return_exceptions=True,
        )

        # 过滤异常结果
        valid_results = [
            r for r in results if isinstance(r, AnalysisResult)
        ]

        logger.info(f"批量分析完成: {len(valid_results)}/{len(news_items)} 条")
        return valid_results

    def _build_analysis_prompt(self, news_item) -> str:
        """构建分析提示

        Args:
            news_item: 新闻条目

        Returns:
            str: 提示文本
        """
        return f"""请分析以下新闻:

标题: {news_item.title}
平台: {news_item.platform}
链接: {news_item.url}
时间: {news_item.timestamp}

请从以下维度分析:
1. 相关性: 这条新闻与科技/AI/互联网行业的相关程度 (0-1分)
2. 重要性: 这条新闻的重要程度 (0-1分)
3. 分类: 新闻分类 (如: AI突破、产品发布、行业动态、投资并购等)
4. 关键词: 3-5个关键词
5. 情感: 新闻情感 (positive/negative/neutral)

请用以下JSON格式返回:
{{
    "relevance_score": 0.0-1.0,
    "importance_score": 0.0-1.0,
    "summary": "一句话摘要",
    "category": "分类名称",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "sentiment": "positive/negative/neutral"
}}"""

    def _parse_analysis_response(
        self,
        response: str,
        news_item,
    ) -> AnalysisResult:
        """解析 LLM 响应

        Args:
            response: LLM 响应文本
            news_item: 原始新闻

        Returns:
            AnalysisResult: 解析后的结果
        """
        try:
            import json
            import re

            # 提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                return AnalysisResult(
                    news_id=news_item.url,
                    relevance_score=float(data.get("relevance_score", 0.5)),
                    importance_score=float(data.get("importance_score", 0.5)),
                    summary=data.get("summary", "")[:200],
                    category=data.get("category", "其他"),
                    keywords=data.get("keywords", []),
                    sentiment=data.get("sentiment", "neutral"),
                )

        except Exception as e:
            logger.warning(f"解析响应失败: {e}")

        return self._default_result(news_item)

    def _default_result(self, news_item) -> AnalysisResult:
        """返回默认结果

        Args:
            news_item: 新闻条目

        Returns:
            AnalysisResult: 默认结果
        """
        return AnalysisResult(
            news_id=news_item.url,
            relevance_score=0.5,
            importance_score=0.5,
            summary=news_item.title[:100],
            category="其他",
            keywords=[],
            sentiment="neutral",
        )


# ==================== 便捷函数 ====================


def create_intelligence_analyzer(
    model: str = "deepseek-chat",
) -> IntelligenceAnalyzer:
    """创建情报分析器

    Args:
        model: LLM 模型

    Returns:
        IntelligenceAnalyzer: 分析器实例
    """
    return IntelligenceAnalyzer(llm_config={"model": model})

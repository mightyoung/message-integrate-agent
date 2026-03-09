# coding=utf-8
"""
MD Generator - 将情报转换为 Markdown 文件

基于 tech-news-digest 模板格式生成 Markdown 摘要
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.intelligence.github_trending import GitHubTrendingItem

from dataclasses import dataclass


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    content: str = ""
    summary: str = ""
    url: str = ""
    source: str = ""
    source_type: str = "rss"
    published_at: Optional[str] = None
    quality_score: int = 0
    metadata: Dict[str, Any] = None


class MDGenerator:
    """Markdown 文件生成器"""

    def __init__(self, title: str = "情报摘要"):
        """初始化生成器

        Args:
            title: 文档标题
        """
        self.title = title

    def generate_digest(
        self,
        items: List[NewsItem],
        categories: Dict[str, List[NewsItem]] = None,
        summary: str = "",
        stats: Dict[str, int] = None,
    ) -> str:
        """生成情报摘要

        Args:
            items: 新闻条目列表
            categories: 按分类组织的条目
            summary: 执行摘要
            stats: 统计信息

        Returns:
            Markdown 格式的字符串
        """
        lines = []

        # 标题
        date_str = datetime.now().strftime("%Y-%m-%d")
        lines.append(f"# {self.title} — {date_str}")
        lines.append("")

        # 执行摘要
        if summary:
            lines.append(f"> {summary}")
            lines.append("")

        # 按分类显示
        if categories:
            for category, category_items in categories.items():
                if not category_items:
                    continue

                lines.append(f"## {self._get_category_emoji(category)} {category}")
                lines.append("")

                for item in category_items[:10]:  # 每类最多10条
                    lines.append(self._format_item(item))

                lines.append("")
        else:
            # 无分类时直接显示所有条目
            for item in items[:20]:  # 最多20条
                lines.append(self._format_item(item))
            lines.append("")

        # 统计信息
        if stats:
            lines.append("---")
            lines.append("")
            lines.append("### 统计信息")
            lines.append("")
            stats_parts = []
            for key, value in stats.items():
                stats_parts.append(f"{key}: {value}")
            lines.append(" | ".join(stats_parts))
            lines.append("")

        return "\n".join(lines)

    def _format_item(self, item: NewsItem) -> str:
        """格式化单个条目

        Args:
            item: 新闻条目

        Returns:
            格式化的字符串
        """
        lines = []

        # 标题和质量分数
        score_emoji = self._get_score_emoji(item.quality_score)
        lines.append(f"**{score_emoji} {item.title}**")

        # 内容/摘要
        if item.summary:
            lines.append(f"> {item.summary}")
        elif item.content:
            # 截取内容
            content = item.content[:200] + "..." if len(item.content) > 200 else item.content
            lines.append(f"> {content}")

        # 来源和时间
        meta_parts = []
        if item.source:
            meta_parts.append(item.source)
        if item.published_at:
            meta_parts.append(item.published_at)

        if meta_parts:
            lines.append(f"*{', '.join(meta_parts)}*")

        # URL
        if item.url:
            lines.append(f"[原文链接]({item.url})")

        lines.append("")

        return "\n".join(lines)

    def _get_category_emoji(self, category: str) -> str:
        """获取分类对应的 emoji

        Args:
            category: 分类名称

        Returns:
            emoji 符号
        """
        emoji_map = {
            "llm": "🧠",
            "ai": "🤖",
            "agent": "🔐",
            "tech": "💻",
            "security": "🔒",
            "crypto": "💰",
            "geopolitics": "🌍",
            "military": "⚔️",
            "cyber": "🛡️",
            "finance": "📈",
            "science": "🔬",
            "default": "📰",
        }

        category_lower = category.lower()
        return emoji_map.get(category_lower, emoji_map["default"])

    def _get_score_emoji(self, score: int) -> str:
        """根据质量分数返回 emoji

        Args:
            score: 质量分数

        Returns:
            emoji 符号
        """
        if score >= 8:
            return "🔥"
        elif score >= 5:
            return "⭐"
        else:
            return "📝"

    def generate_bettafish_report(self, analysis_result: Dict[str, Any]) -> str:
        """生成 BettaFish 分析报告

        Args:
            analysis_result: 分析结果

        Returns:
            Markdown 格式的报告
        """
        lines = []

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines.append(f"# 深入分析报告 — {date_str}")
        lines.append("")

        # 分析主题
        if "topic" in analysis_result:
            lines.append(f"**分析主题**: {analysis_result['topic']}")
            lines.append("")

        # 情感分析
        if "sentiment" in analysis_result:
            lines.append("## 情感分析")
            lines.append("")
            lines.append(f"- **总体情感**: {analysis_result['sentiment'].get('overall', 'N/A')}")
            lines.append(f"- **情感得分**: {analysis_result['sentiment'].get('score', 'N/A')}")
            lines.append("")

        # 关键观点
        if "key_points" in analysis_result:
            lines.append("## 关键观点")
            lines.append("")
            for point in analysis_result["key_points"]:
                lines.append(f"- {point}")
            lines.append("")

        # 风险评估
        if "risks" in analysis_result:
            lines.append("## 风险评估")
            lines.append("")
            for risk in analysis_result["risks"]:
                lines.append(f"- {risk}")
            lines.append("")

        # 建议
        if "recommendations" in analysis_result:
            lines.append("## 建议")
            lines.append("")
            for rec in analysis_result["recommendations"]:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)

    def generate_mirofish_report(self, prediction_result: Dict[str, Any]) -> str:
        """生成 MiroFish 预测报告

        Args:
            prediction_result: 预测结果

        Returns:
            Markdown 格式的报告
        """
        lines = []

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines.append(f"# 预测性分析报告 — {date_str}")
        lines.append("")

        # 预测主题
        if "scenario" in prediction_result:
            lines.append(f"**预测场景**: {prediction_result['scenario']}")
            lines.append("")

        # 预测结果
        if "predictions" in prediction_result:
            lines.append("## 预测结果")
            lines.append("")
            for pred in prediction_result["predictions"]:
                lines.append(f"### {pred.get('title', 'Prediction')}")
                lines.append(f"**概率**: {pred.get('probability', 'N/A')}")
                lines.append(f"**置信度**: {pred.get('confidence', 'N/A')}")
                if "reasoning" in pred:
                    lines.append(f"**推理**: {pred['reasoning']}")
                lines.append("")

        # 趋势分析
        if "trends" in prediction_result:
            lines.append("## 趋势分析")
            lines.append("")
            for trend in prediction_result["trends"]:
                lines.append(f"- {trend}")
            lines.append("")

        # 建议行动
        if "recommended_actions" in prediction_result:
            lines.append("## 建议行动")
            lines.append("")
            for action in prediction_result["recommended_actions"]:
                lines.append(f"- {action}")
            lines.append("")

        return "\n".join(lines)

    def generate_github_trending(
        self,
        repos: List["GitHubTrendingItem"],
        include_readme_summary: bool = True,
    ) -> str:
        """生成 GitHub Trending 摘要

        Args:
            repos: GitHub Trending 仓库列表
            include_readme_summary: 是否包含 README 摘要

        Returns:
            Markdown 格式的字符串
        """
        lines = []

        # 标题
        date_str = datetime.now().strftime("%Y-%m-%d")
        lines.append(f"# 🐙 GitHub Trending — {date_str}")
        lines.append("")

        # 按语言分组
        by_language: Dict[str, List] = {}
        for repo in repos:
            lang = repo.language or "Unknown"
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(repo)

        # 按语言显示
        for lang, lang_repos in sorted(by_language.items(), key=lambda x: -len(x[1])):
            lines.append(f"## 🔤 {lang} ({len(lang_repos)} 个项目)")
            lines.append("")

            for repo in lang_repos[:10]:  # 每语言最多10个
                lines.append(self._format_github_repo(repo, include_readme_summary))

            lines.append("")

        # 统计
        lines.append("---")
        lines.append("")
        lines.append("### 统计")
        lines.append("")
        lines.append(f"- 总项目数: {len(repos)}")
        lines.append(f"- 总星数: {sum(r.stars for r in repos)}")
        lines.append(f"- 总Fork数: {sum(r.forks for r in repos)}")
        lines.append("")

        return "\n".join(lines)

    def _format_github_repo(self, repo, include_summary: bool = True) -> str:
        """格式化 GitHub 仓库条目"""
        lines = []

        # 标题和星数
        stars_emoji = "🔥" if repo.stars >= 1000 else "⭐"
        lines.append(f"### {stars_emoji} {repo.name} ({repo.stars:,} ⭐)")

        # 每日增长
        if repo.daily_stars_est > 0:
            lines.append(f"> 📈 +{repo.daily_stars_est} stars/day")

        # Fork 数
        if repo.forks > 0:
            lines.append(f"> 🍴 {repo.forks:,} forks")

        # 描述
        if repo.description:
            lines.append(f"> {repo.description}")

        # 简要说明 (来自 README)
        if include_summary and hasattr(repo, 'summary') and repo.summary:
            lines.append(f"> 📝 {repo.summary}")

        # 链接
        lines.append(f"[查看项目 →]({repo.url})")

        # 主题标签
        if repo.topics:
            tags = " ".join(f"`{t}`" for t in repo.topics)
            lines.append(f"> {tags}")

        lines.append("")

        return "\n".join(lines)


def create_md_generator(title: str = "情报摘要") -> MDGenerator:
    """创建 MD 生成器的便捷函数"""
    return MDGenerator(title=title)

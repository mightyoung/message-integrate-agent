# coding=utf-8
"""
Intelligence Scorer - 情报价值评分

基于多维度评分模型:
- 时效性评分
- 相关性评分
- 重要性评分
- 用户兴趣匹配

参考: Microsoft Azure Multi-Signal Ranking
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class UserProfile:
    """用户画像"""

    user_id: str
    interests: List[str]  # 兴趣关键词
    preferred_categories: List[str]  # 偏好分类
    notification_channels: List[str]  # 通知渠道
    notify_frequency: str  # 通知频率 hourly/daily/weekly
    last_active: Optional[str] = None


@dataclass
class ScoredIntelligence:
    """评分后的情报"""

    news_item: Any
    analysis_result: Any
    total_score: float
    match_reasons: List[str]
    intelligence_id: str = ""


class IntelligenceScorer:
    """情报价值评分器

    综合多维度评分:
    - 时效性: 发布时间距离现在的时间
    - 相关性: 与用户兴趣的匹配度
    - 重要性: 新闻本身的重要程度
    - 用户匹配: 与用户画像的匹配程度
    """

    # 权重配置
    DEFAULT_WEIGHTS = {
        "recency": 0.2,      # 时效性权重
        "relevance": 0.3,    # 相关性权重
        "importance": 0.3,    # 重要性权重
        "user_match": 0.2,    # 用户匹配权重
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
    ):
        """初始化评分器

        Args:
            weights: 评分权重配置
        """
        self.weights = weights or self.DEFAULT_WEIGHTS
        self._user_profiles: Dict[str, UserProfile] = {}

    def register_user(self, profile: UserProfile):
        """注册用户画像

        Args:
            profile: 用户画像
        """
        self._user_profiles[profile.user_id] = profile
        logger.info(f"注册用户画像: {profile.user_id}")

    def update_user_interests(
        self,
        user_id: str,
        interests: List[str],
    ):
        """更新用户兴趣

        Args:
            user_id: 用户 ID
            interests: 兴趣列表
        """
        if user_id in self._user_profiles:
            self._user_profiles[user_id].interests = interests
        else:
            self._user_profiles[user_id] = UserProfile(
                user_id=user_id,
                interests=interests,
                preferred_categories=[],
                notification_channels=["feishu"],
                notify_frequency="daily",
            )

    async def score(
        self,
        news_item,
        analysis_result,
        user_id: str,
    ) -> ScoredIntelligence:
        """对情报进行评分

        Args:
            news_item: 新闻条目
            analysis_result: 分析结果
            user_id: 用户 ID

        Returns:
            ScoredIntelligence: 评分后的情报
        """
        # 获取用户画像
        user_profile = self._user_profiles.get(user_id)

        # 1. 时效性评分
        recency_score = self._calc_recency_score(news_item)

        # 2. 相关性评分 (来自分析结果)
        relevance_score = analysis_result.relevance_score

        # 3. 重要性评分 (来自分析结果)
        importance_score = analysis_result.importance_score

        # 4. 用户匹配评分
        user_match_score = self._calc_user_match_score(
            analysis_result, user_profile
        )

        # 计算总分
        total_score = (
            recency_score * self.weights["recency"] +
            relevance_score * self.weights["relevance"] +
            importance_score * self.weights["importance"] +
            user_match_score * self.weights["user_match"]
        )

        # 生成匹配原因
        match_reasons = self._generate_match_reasons(
            news_item, analysis_result, user_profile
        )

        return ScoredIntelligence(
            news_item=news_item,
            analysis_result=analysis_result,
            total_score=total_score,
            match_reasons=match_reasons,
        )

    async def score_batch(
        self,
        news_items: List,
        analysis_results: List,
        user_id: str,
        min_score: float = 0.5,
    ) -> List[ScoredIntelligence]:
        """批量评分并过滤

        Args:
            news_items: 新闻列表
            analysis_results: 分析结果列表
            user_id: 用户 ID
            min_score: 最低分数阈值

        Returns:
            List[ScoredIntelligence]: 评分后的情报列表
        """
        scored_items = []

        for news_item, analysis_result in zip(news_items, analysis_results):
            scored = await self.score(news_item, analysis_result, user_id)
            if scored.total_score >= min_score:
                scored_items.append(scored)

        # 按分数排序
        scored_items.sort(key=lambda x: x.total_score, reverse=True)

        logger.info(f"批量评分完成: {len(scored_items)}/{len(news_items)} 条通过阈值")
        return scored_items

    def _calc_recency_score(self, news_item) -> float:
        """计算时效性评分

        Args:
            news_item: 新闻条目

        Returns:
            float: 0-1 分数
        """
        # 如果有时间信息，计算时间差
        if news_item.timestamp:
            try:
                # 尝试解析时间
                pub_time = datetime.fromisoformat(news_item.timestamp)
                hours_old = (datetime.now() - pub_time).total_seconds() / 3600

                # 24小时内为1分，之后递减
                if hours_old <= 1:
                    return 1.0
                elif hours_old <= 6:
                    return 0.9
                elif hours_old <= 24:
                    return 0.7
                elif hours_old <= 72:
                    return 0.5
                elif hours_old <= 168:  # 1周
                    return 0.3
                else:
                    return 0.1
            except Exception:
                pass

        # 默认分数
        return 0.5

    def _calc_user_match_score(
        self,
        analysis_result,
        user_profile: Optional[UserProfile],
    ) -> float:
        """计算用户匹配评分

        Args:
            analysis_result: 分析结果
            user_profile: 用户画像

        Returns:
            float: 0-1 分数
        """
        if not user_profile:
            return 0.5  # 无用户信息，返回中间值

        score = 0.0
        reasons = []

        # 检查分类匹配
        if analysis_result.category in user_profile.preferred_categories:
            score += 0.5

        # 检查关键词匹配
        if user_profile.interests and analysis_result.keywords:
            keywords = set(k.lower() for k in analysis_result.keywords)
            interests = set(i.lower() for i in user_profile.interests)
            matches = keywords & interests

            if matches:
                score += min(0.5, len(matches) * 0.2)

        return min(1.0, score)

    def _generate_match_reasons(
        self,
        news_item,
        analysis_result,
        user_profile: Optional[UserProfile],
    ) -> List[str]:
        """生成匹配原因

        Args:
            news_item: 新闻条目
            analysis_result: 分析结果
            user_profile: 用户画像

        Returns:
            List[str]: 匹配原因列表
        """
        reasons = []

        # 分类原因
        if analysis_result.category:
            reasons.append(f"分类: {analysis_result.category}")

        # 关键词原因
        if analysis_result.keywords:
            reasons.append(f"关键词: {', '.join(analysis_result.keywords[:3])}")

        # 用户匹配原因
        if user_profile and user_profile.interests:
            interests = set(i.lower() for i in user_profile.interests)
            keywords = set(k.lower() for k in analysis_result.keywords)
            matches = keywords & interests
            if matches:
                reasons.append(f"匹配你的兴趣: {', '.join(matches)}")

        return reasons

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像

        Args:
            user_id: 用户 ID

        Returns:
            Optional[UserProfile]: 用户画像
        """
        return self._user_profiles.get(user_id)


# ==================== 便捷函数 ====================


def create_intelligence_scorer(
    weights: Optional[Dict[str, float]] = None,
) -> IntelligenceScorer:
    """创建情报评分器

    Args:
        weights: 评分权重

    Returns:
        IntelligenceScorer: 评分器实例
    """
    return IntelligenceScorer(weights=weights)

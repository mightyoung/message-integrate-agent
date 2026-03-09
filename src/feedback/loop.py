"""
FeedbackLoop - 反馈闭环处理

使用 AI 分析反馈模式并触发系统改进:
1. 分析反馈模式 (多次负面 → 同一问题)
2. 负面反馈触发 Agent 反思
3. 纠正更新知识库/路由规则
4. 自我改进机制

设计参考:
- Self-Refine: https://arxiv.org/abs/2303.17491
- RLHF: 从人类反馈中学习
- Critic Pattern: 即时反馈机制
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

from loguru import logger


@dataclass
class FeedbackPattern:
    """反馈模式"""
    pattern_type: str  # "negative_topic", "low_rating", "repeated_correction"
    count: int
    first_seen: str
    last_seen: str
    related_messages: List[str] = field(default_factory=list)
    suggested_action: Optional[str] = None


@dataclass
class ReflectionResult:
    """反思结果"""
    analysis: str  # 分析原因
    improvement: str  # 改进建议
    confidence: float  # 置信度 0-1
    action_taken: str = "logged"  # "logged", "rule_updated", "skill_updated", "none"


class FeedbackLoop:
    """
    反馈闭环处理器

    处理流程:
    1. 接收反馈
    2. 分析模式 (批量反馈)
    3. 触发反思 (负面反馈)
    4. 执行改进 (纠正反馈)
    """

    # 负面反馈阈值
    THRESHOLD_THUMBS_DOWN = 1
    THRESHOLD_LOW_RATING = 2  # <= 2 stars

    # 模式检测阈值
    PATTERN_WINDOW_MINUTES = 60  # 1小时内
    PATTERN_MIN_COUNT = 3  # 最少3次

    def __init__(
        self,
        feedback_service,
        experience_logger=None,
        agent_loop=None,
        keyword_router=None,
    ):
        """
        初始化反馈闭环

        Args:
            feedback_service: FeedbackService 实例
            experience_logger: ExperienceLogger 实例 (可选)
            agent_loop: AgentLoop 实例 (用于反思)
            keyword_router: KeywordRouter 实例 (用于更新规则)
        """
        self.feedback_service = feedback_service
        self.experience_logger = experience_logger
        self.agent_loop = agent_loop
        self.keyword_router = keyword_router

        # 反馈模式缓存
        self._recent_feedbacks: List[Dict[str, Any]] = []
        self._patterns: Dict[str, FeedbackPattern] = {}

        # 注册反馈回调
        self._register_callbacks()

    def _register_callbacks(self):
        """注册反馈回调"""
        from src.feedback import FeedbackType

        # 负面反馈回调
        self.feedback_service.register_callback(
            FeedbackType.THUMBS_DOWN,
            self._handle_negative_feedback
        )

        # 低评分回调
        self.feedback_service.register_callback(
            FeedbackType.RATING,
            self._handle_rating_feedback
        )

        # 纠正反馈回调
        self.feedback_service.register_callback(
            FeedbackType.CORRECTION,
            self._handle_correction_feedback
        )

        logger.info("✅ FeedbackLoop callbacks registered")

    async def _handle_negative_feedback(self, feedback):
        """处理负面反馈 - 触发反思"""
        logger.info(f"🔴 收到负面反馈: {feedback.id}")

        # 触发 AI 反思
        if self.agent_loop:
            result = await self._trigger_reflection(
                feedback=feedback,
                reason="thumbs_down"
            )
            if result:
                logger.info(f"💭 反思完成: {result.improvement}")

    async def _handle_rating_feedback(self, feedback):
        """处理低评分反馈"""
        # 检查是否为低评分
        if isinstance(feedback.value, (int, float)) and feedback.value <= self.THRESHOLD_LOW_RATING:
            logger.info(f"⭐ 低评分反馈: {feedback.value}")

            if self.agent_loop:
                result = await self._trigger_reflection(
                    feedback=feedback,
                    reason=f"low_rating_{feedback.value}"
                )
                if result:
                    logger.info(f"💭 评分反思: {result.improvement}")

    async def _handle_correction_feedback(self, feedback):
        """处理纠正反馈 - 更新知识库"""
        logger.info(f"✏️ 收到纠正反馈: {feedback.id}")

        # 提取学习内容
        await self._process_correction(feedback)

    async def _trigger_reflection(
        self,
        feedback,
        reason: str
    ) -> Optional[ReflectionResult]:
        """
        触发 Agent 反思

        Args:
            feedback: 反馈对象
            reason: 反思原因

        Returns:
            ReflectionResult 或 None
        """
        if not self.agent_loop:
            logger.warning("AgentLoop not available for reflection")
            return None

        try:
            # 构建反思提示
            prompt = self._build_reflection_prompt(feedback, reason)

            # 使用 AgentLoop 进行反思
            result = await self.agent_loop.run(
                message=prompt,
                session_id=f"reflection_{feedback.message_id}",
                user_id=feedback.user_id,
                context={
                    "task": "reflection",
                    "original_message_id": feedback.message_id,
                    "feedback_reason": reason,
                }
            )

            if result.success:
                # 解析反思结果
                reflection = self._parse_reflection_result(
                    result.final_output,
                    reason
                )

                # 记录到经验日志
                if self.experience_logger:
                    await self.experience_logger.log_error(
                        error_type="feedback_reflection",
                        error_message=f"反思原因: {reason}",
                        context={
                            "message_id": feedback.message_id,
                            "agent": feedback.agent_name,
                            "analysis": reflection.analysis,
                        },
                        solution=reflection.improvement,
                    )

                return reflection
            else:
                logger.warning(f"反思失败: {result.error}")
                return None

        except Exception as e:
            logger.error(f"反思执行失败: {e}")
            return None

    def _build_reflection_prompt(self, feedback, reason: str) -> str:
        """构建反思提示"""
        return f"""你收到了一个负面反馈，请进行深度反思。

反馈类型: {reason}
消息ID: {feedback.message_id}
Agent: {feedback.agent_name}
路由: {feedback.router_used}

请分析:
1. 为什么用户会给这个反馈?
2. 回复中可能存在什么问题?
3. 以后如何改进?

请用简洁的语言回答上述问题。"""

    def _parse_reflection_result(self, output: str, reason: str) -> ReflectionResult:
        """解析反思结果"""
        # 简单解析 - 实际可以用 LLM 进一步结构化
        return ReflectionResult(
            analysis=output[:200] if output else "无分析",
            improvement=output[200:] if output and len(output) > 200 else output or "无改进建议",
            confidence=0.7,
            action_taken="logged"
        )

    async def _process_correction(self, feedback) -> bool:
        """
        处理纠正反馈 - 更新知识库

        Args:
            feedback: 纠正反馈

        Returns:
            是否成功处理
        """
        if not self.experience_logger:
            return False

        try:
            correction_text = feedback.value
            message_id = feedback.message_id

            # 提取关键纠正内容
            await self.experience_logger.log_error(
                error_type="user_correction",
                error_message=f"用户纠正: {correction_text}",
                context={
                    "message_id": message_id,
                    "agent": feedback.agent_name,
                    "router": feedback.router_used,
                },
                solution="待分析",
            )

            # 尝试更新关键词路由
            if self.keyword_router:
                await self._update_routing_from_correction(
                    feedback, correction_text
                )

            logger.info(f"✅ 纠正已处理: {message_id}")
            return True

        except Exception as e:
            logger.error(f"纠正处理失败: {e}")
            return False

    async def _update_routing_from_correction(self, feedback, correction: str):
        """从纠正中学习并更新路由"""
        # 简单实现 - 检测是否包含新关键词
        # 实际可以使用 LLM 提取关键词

        keywords_to_check = ["天气", "翻译", "搜索", "天气查询"]

        for keyword in keywords_to_check:
            if keyword in correction.lower():
                logger.info(f"📝 从纠正中学习: 检测到关键词 '{keyword}'")
                # 可以添加新规则或调整现有规则
                # 实际实现需要更复杂的逻辑

    async def analyze_patterns(self) -> Dict[str, FeedbackPattern]:
        """
        分析反馈模式

        检测:
        - 同一话题的多次负面反馈
        - 低评分聚集
        - 重复纠正

        Returns:
            模式字典
        """
        # 获取近期反馈
        cutoff = datetime.now() - timedelta(minutes=self.PATTERN_WINDOW_MINUTES)
        recent = [
            f for f in self._recent_feedbacks
            if datetime.fromisoformat(f.get("timestamp", "2000-01-01")) > cutoff
        ]

        # 按话题分组 (简化: 按 agent 分组)
        by_agent = defaultdict(list)
        for f in recent:
            agent = f.get("agent_name", "unknown")
            by_agent[agent].append(f)

        # 检测模式
        patterns = {}

        for agent, feedbacks in by_agent.items():
            if len(feedbacks) >= self.PATTERN_MIN_COUNT:
                # 检查负面比例
                negative_count = sum(
                    1 for f in feedbacks
                    if f.get("feedback_type") in ["thumbs_down", "rating"]
                    and f.get("value", 5) <= 2
                )

                if negative_count >= self.PATTERN_MIN_COUNT:
                    pattern = FeedbackPattern(
                        pattern_type="negative_topic",
                        count=negative_count,
                        first_seen=feedbacks[0].get("timestamp", ""),
                        last_seen=feedbacks[-1].get("timestamp", ""),
                        related_messages=[f.get("message_id") for f in feedbacks],
                        suggested_action=f"检查 {agent} 的输出质量",
                    )
                    patterns[agent] = pattern
                    logger.warning(f"⚠️ 检测到负面模式: {agent} ({negative_count} 次)")

        self._patterns = patterns
        return patterns

    def get_suggestions(self) -> List[str]:
        """获取改进建议"""
        suggestions = []

        for pattern in self._patterns.values():
            if pattern.suggested_action:
                suggestions.append(pattern.suggested_action)

        # 基于统计的建议
        stats = self.feedback_service.get_stats()

        if stats.thumbs_down_count > 10:
            suggestions.append("负面反馈较多，建议检查核心路由策略")

        if stats.avg_rating > 0 and stats.avg_rating < 3:
            suggestions.append("平均评分较低，建议优化 Agent 输出质量")

        if stats.correction_count > 5:
            suggestions.append("纠正反馈较多，建议更新知识库")

        return suggestions

    async def close(self):
        """关闭反馈闭环"""
        # 清理资源
        self._recent_feedbacks.clear()
        self._patterns.clear()
        logger.info("🔄 FeedbackLoop closed")

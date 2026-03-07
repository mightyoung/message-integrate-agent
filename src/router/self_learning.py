"""
Self-Learning Router - 可自学习的路由系统

实现从成功交互中自动学习：
- 关键词提取
- 路由规则自动更新
- 成功案例学习

设计参考：
- Naive Bayes 分类器思路
- 关键词提取算法 (TF-IDF 简化版)
- 反馈循环学习系统
"""
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class LearnedPattern:
    """学习到的模式"""

    def __init__(
        self,
        keywords: List[str],
        agent: str,
        action: Optional[str] = None,
        success_count: int = 1,
        last_success: Optional[str] = None,
    ):
        self.keywords = keywords
        self.agent = agent
        self.action = action
        self.success_count = success_count
        self.created_at = datetime.now().isoformat()
        self.last_success = last_success or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keywords": self.keywords,
            "agent": self.agent,
            "action": self.action,
            "success_count": self.success_count,
            "created_at": self.created_at,
            "last_success": self.last_success,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearnedPattern":
        pattern = cls(
            keywords=data["keywords"],
            agent=data["agent"],
            action=data.get("action"),
            success_count=data.get("success_count", 1),
            last_success=data.get("last_success"),
        )
        pattern.created_at = data.get("created_at", pattern.created_at)
        return pattern


class SelfLearningRouter:
    """
    可自学习的路由器

    特性：
    - 从成功交互中学习
    - 自动提取关键词
    - 动态更新路由规则
    - 基于置信度的路由
    """

    def __init__(
        self,
        storage_path: str = "data/router_learnings.json",
        min_success_count: int = 3,
        keyword_extraction_threshold: float = 0.3,
    ):
        """
        初始化自学习路由器

        Args:
            storage_path: 学习数据存储路径
            min_success_count: 最少成功次数才添加到路由
            keyword_extraction_threshold: 关键词提取阈值
        """
        self.storage_path = Path(storage_path)
        self.min_success_count = min_success_count
        self.keyword_threshold = keyword_extraction_threshold

        # 学习到的模式
        self.learned_patterns: Dict[str, LearnedPattern] = {}

        # 成功案例库
        self.success_cases: List[Dict[str, Any]] = []

        # 统计信息
        self.stats = {
            "total_learned": 0,
            "total_successful": 0,
            "total_failed": 0,
        }

        # 加载已保存的学习数据
        self._load()

    def _load(self):
        """加载保存的学习数据"""
        if not self.storage_path.exists():
            return

        try:
            data = json.loads(self.storage_path.read_text())

            # 加载模式
            for agent, patterns in data.get("patterns", {}).items():
                for pattern_data in patterns:
                    pattern = LearnedPattern.from_dict(pattern_data)
                    key = "_".join(pattern.keywords)
                    self.learned_patterns[key] = pattern

            # 加载统计
            self.stats = data.get("stats", self.stats)

            logger.info(f"📚 加载了 {len(self.learned_patterns)} 个学习模式")

        except Exception as e:
            logger.warning(f"⚠️ 加载学习数据失败: {e}")

    def _save(self):
        """保存学习数据"""
        # 确保目录存在
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # 整理数据
        patterns_by_agent = defaultdict(list)
        for pattern in self.learned_patterns.values():
            patterns_by_agent[pattern.agent].append(pattern.to_dict())

        data = {
            "patterns": dict(patterns_by_agent),
            "stats": self.stats,
            "saved_at": datetime.now().isoformat(),
        }

        try:
            self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"❌ 保存学习数据失败: {e}")

    def extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词

        使用简单的词频统计：
        - 过滤停用词
        - 计算词频
        - 选取高频词

        Args:
            text: 输入文本

        Returns:
            关键词列表
        """
        # 简单停用词
        stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can",
        }

        # 分词（简单按空格和标点）
        import re
        words = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())

        # 过滤停用词和短词
        words = [w for w in words if w not in stop_words and len(w) > 1]

        # 词频统计
        word_freq = defaultdict(int)
        for word in words:
            word_freq[word] += 1

        # 计算阈值
        if not word_freq:
            return []

        max_freq = max(word_freq.values())
        threshold = max_freq * self.keyword_threshold

        # 选取高频词
        keywords = [
            word for word, freq in word_freq.items()
            if freq >= threshold
        ]

        return keywords[:5]  # 最多5个关键词

    def learn_from_success(
        self,
        message: str,
        agent: str,
        action: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        从成功案例中学习

        Args:
            message: 用户消息
            agent: 目标 agent
            action: 动作
            context: 额外上下文
        """
        self.stats["total_successful"] += 1

        # 提取关键词
        keywords = self.extract_keywords(message)

        if not keywords:
            logger.debug(f"⚠️ 无法从消息中提取关键词: {message[:30]}")
            return

        # 创建或更新模式
        key = "_".join(keywords)

        if key in self.learned_patterns:
            # 更新已有模式
            pattern = self.learned_patterns[key]
            pattern.success_count += 1
            pattern.last_success = datetime.now().isoformat()

            # 如果达到阈值，添加到路由
            if pattern.success_count >= self.min_success_count:
                logger.info(f"🧠 学习模式已激活: {keywords} -> {agent}")

        else:
            # 创建新模式
            pattern = LearnedPattern(
                keywords=keywords,
                agent=agent,
                action=action,
                success_count=1,
            )
            self.learned_patterns[key] = pattern
            logger.info(f"🧠 学习新模式: {keywords} -> {agent}")

        # 记录成功案例
        self.success_cases.append({
            "message": message,
            "keywords": keywords,
            "agent": agent,
            "action": action,
            "timestamp": datetime.now().isoformat(),
        })

        # 保持案例数量限制
        if len(self.success_cases) > 1000:
            self.success_cases = self.success_cases[-500:]

        self.stats["total_learned"] = len(self.learned_patterns)

        # 保存
        self._save()

    def learn_from_failure(
        self,
        message: str,
        attempted_agent: str,
        error: str,
    ):
        """
        从失败案例中学习（用于避免重复错误）

        Args:
            message: 用户消息
            attempted_agent: 尝试的 agent
            error: 错误信息
        """
        self.stats["total_failed"] += 1

        # 记录失败案例
        # 可以用于后续分析或避免相同错误

    def get_recommended_keywords(self, agent: str) -> List[str]:
        """
        获取指定 agent 的推荐关键词

        Args:
            agent: Agent 名称

        Returns:
            关键词列表
        """
        keywords = []

        for pattern in self.learned_patterns.values():
            if pattern.agent == agent and pattern.success_count >= self.min_success_count:
                keywords.extend(pattern.keywords)

        # 去重
        return list(set(keywords))

    def get_routing_suggestion(self, message: str) -> Optional[Dict[str, Any]]:
        """
        获取路由建议

        Args:
            message: 用户消息

        Returns:
            路由建议或 None
        """
        keywords = self.extract_keywords(message)

        if not keywords:
            return None

        # 查找匹配的模式
        best_match = None
        best_score = 0

        for pattern in self.learned_patterns.values():
            # 计算匹配分数
            matches = sum(1 for kw in keywords if kw in pattern.keywords)
            score = matches / len(pattern.keywords) if pattern.keywords else 0

            # 考虑成功次数
            score *= min(pattern.success_count / 10, 1.0)

            if score > best_score and pattern.success_count >= self.min_success_count:
                best_score = score
                best_match = pattern

        if best_match:
            return {
                "agent": best_match.agent,
                "action": best_match.action,
                "confidence": best_score,
                "keywords": best_match.keywords,
            }

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "active_patterns": len([
                p for p in self.learned_patterns.values()
                if p.success_count >= self.min_success_count
            ]),
            "total_patterns": len(self.learned_patterns),
            "recent_cases": len(self.success_cases[-10:]),
        }

    def export_rules(self) -> List[Dict[str, Any]]:
        """
        导出可用的路由规则

        Returns:
            规则列表
        """
        rules = []

        for pattern in self.learned_patterns.values():
            if pattern.success_count >= self.min_success_count:
                rules.append({
                    "keywords": pattern.keywords,
                    "agent": pattern.agent,
                    "action": pattern.action,
                    "confidence": min(pattern.success_count / 10, 1.0),
                })

        return rules


# 全局实例
_self_learning_router: Optional[SelfLearningRouter] = None


def get_self_learning_router() -> SelfLearningRouter:
    """获取全局自学习路由器"""
    global _self_learning_router
    if _self_learning_router is None:
        _self_learning_router = SelfLearningRouter()
    return _self_learning_router

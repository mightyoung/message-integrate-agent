"""
Experience Logger - 结构化的"记忆"

实现 OpenClaw 风格的经验日志系统：
- LEARNINGS.md: 记录学习到的最佳实践
- ERRORS.md: 记录失败和解决方案
- FEATURE_REQUESTS.md: 记录功能请求

设计参考：
- OpenClaw self-improving-agent
- Python logging 模块
- 结构化错误追踪系统
"""
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class Priority(Enum):
    """优先级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExperienceLogger:
    """
    结构化经验日志系统

    存储结构：
    .learnings/
    ├── LEARNINGS.md         # 最佳实践和学习
    ├── ERRORS.md            # 错误和解决方案
    └── FEATURE_REQUESTS.md  # 功能请求

    特性：
    - 自动创建目录结构
    - 标准化日志格式
    - 支持自动触发记录
    """

    LEARNINGS_DIR = Path(".learnings")
    LEARNINGS_FILE = LEARNINGS_DIR / "LEARNINGS.md"
    ERRORS_FILE = LEARNINGS_DIR / "ERRORS.md"
    FEATURES_FILE = LEARNINGS_DIR / "FEATURE_REQUESTS.md"

    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化经验日志

        Args:
            base_dir: 基础目录，默认当前目录
        """
        if base_dir:
            self.LEARNINGS_DIR = base_dir / ".learnings"
            self.LEARNINGS_FILE = self.LEARNINGS_DIR / "LEARNINGS.md"
            self.ERRORS_FILE = self.LEARNINGS_DIR / "ERRORS.md"
            self.FEATURES_FILE = self.LEARNINGS_DIR / "FEATURE_REQUESTS.md"

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保目录存在"""
        self.LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)

        # 确保文件存在
        for file_path in [self.LEARNINGS_FILE, self.ERRORS_FILE, self.FEATURES_FILE]:
            if not file_path.exists():
                self._init_file(file_path)

    def _init_file(self, file_path: Path):
        """初始化文件"""
        title = file_path.stem
        file_path.write_text(f"# {title}\n\n", encoding="utf-8")

    # ==================== LEARNINGS ====================

    def log_learning(
        self,
        content: str,
        priority: str = "medium",
        category: str = "general",
        tags: Optional[List[str]] = None,
    ):
        """
        记录学习到的最佳实践

        Args:
            content: 学习内容
            priority: 优先级
            category: 分类
            tags: 标签
        """
        entry = self._format_entry(
            title="学习记录",
            content=content,
            priority=priority,
            category=category,
            tags=tags,
        )

        self._append_entry(self.LEARNINGS_FILE, entry)
        logger.info(f"📚 记录学习: {content[:50]}...")

    def log_user_correction(
        self,
        original: str,
        correction: str,
        reason: str,
    ):
        """
        记录用户纠正

        Args:
            original: 原始回复
            correction: 纠正后的回复
            reason: 纠正原因
        """
        content = f"""用户纠正:
原始: {original}
纠正: {correction}
原因: {reason}"""

        entry = self._format_entry(
            title="用户纠正",
            content=content,
            priority="high",
            category="correction",
            tags=["correction", "user-feedback"],
        )

        self._append_entry(self.LEARNINGS_FILE, entry)
        logger.info(f"📚 记录用户纠正: {reason[:50]}...")

    def log_best_practice(
        self,
        practice: str,
        context: str,
        source: str = "experience",
    ):
        """
        记录最佳实践

        Args:
            practice: 实践内容
            context: 使用场景
            source: 来源
        """
        content = f"""最佳实践: {practice}
场景: {context}
来源: {source}"""

        entry = self._format_entry(
            title="最佳实践",
            content=content,
            priority="medium",
            category="best-practice",
            tags=["best-practice", source],
        )

        self._append_entry(self.LEARNINGS_FILE, entry)

    # ==================== ERRORS ====================

    def log_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        solution: Optional[str] = None,
    ):
        """
        记录错误和解决方案

        Args:
            error: 异常对象
            context: 错误上下文
            solution: 解决方案
        """
        content = f"""错误类型: {type(error).__name__}
错误信息: {str(error)}
上下文: {context}
解决方案: {solution or '待解决'}"""

        entry = self._format_entry(
            title="错误记录",
            content=content,
            priority="high",
            category="error",
            tags=["error", type(error).__name__],
        )

        self._append_entry(self.ERRORS_FILE, entry)
        logger.warning(f"❌ 记录错误: {type(error).__name__} - {str(error)[:50]}...")

    def log_api_failure(
        self,
        api_name: str,
        status_code: int,
        response: str,
        retry_strategy: Optional[str] = None,
    ):
        """
        记录 API 调用失败

        Args:
            api_name: API 名称
            status_code: HTTP 状态码
            response: 响应内容
            retry_strategy: 重试策略
        """
        content = f"""API: {api_name}
状态码: {status_code}
响应: {response[:200]}
重试策略: {retry_strategy or '无'}"""

        entry = self._format_entry(
            title="API 失败",
            content=content,
            priority="high",
            category="api-error",
            tags=["api", str(status_code)],
        )

        self._append_entry(self.ERRORS_FILE, entry)

    def log_resolution(
        self,
        error_description: str,
        solution: str,
        effectiveness: str = "unknown",
    ):
        """
        记录问题解决方案

        Args:
            error_description: 问题描述
            solution: 解决方案
            effectiveness: 有效性评估
        """
        content = f"""问题: {error_description}
解决: {solution}
有效性: {effectiveness}"""

        entry = self._format_entry(
            title="解决方案",
            content=content,
            priority="medium",
            category="resolution",
            tags=["resolution", effectiveness],
        )

        self._append_entry(self.ERRORS_FILE, entry)

    # ==================== FEATURES ====================

    def log_feature_request(
        self,
        feature: str,
        description: str,
        requester: str = "system",
        priority: str = "medium",
    ):
        """
        记录功能请求

        Args:
            feature: 功能名称
            description: 功能描述
            requester: 请求者
            priority: 优先级
        """
        content = f"""功能: {feature}
描述: {description}
请求者: {requester}"""

        entry = self._format_entry(
            title="功能请求",
            content=content,
            priority=priority,
            category="feature-request",
            tags=["feature", requester],
        )

        self._append_entry(self.FEATURES_FILE, entry)
        logger.info(f"📝 记录功能请求: {feature}")

    def log_unsupported_intent(
        self,
        intent: str,
        user_message: str,
    ):
        """
        记录不支持的意图

        Args:
            intent: 意图
            user_message: 用户消息
        """
        content = f"""意图: {intent}
消息: {user_message}"""

        entry = self._format_entry(
            title="不支持的意图",
            content=content,
            priority="low",
            category="unsupported",
            tags=["intent", "unsupported"],
        )

        self._append_entry(self.FEATURES_FILE, entry)

    # ==================== UTILITIES ====================

    def _format_entry(
        self,
        title: str,
        content: str,
        priority: str = "medium",
        category: str = "general",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        格式化日志条目

        格式:
        ---
        ## [时间] [优先级] 标题
        **分类**: xxx
        **标签**: tag1, tag2

        内容...
        ---
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tags_str = ", ".join(tags) if tags else "无"

        return f"""---
## [{timestamp}] [{priority.upper()}] {title}
**分类**: {category}
**标签**: {tags_str}

{content}
---
"""

    def _append_entry(self, file_path: Path, entry: str):
        """追加条目到文件"""
        # 读取现有内容
        content = file_path.read_text(encoding="utf-8")

        # 在最后一个 --- 之后插入新条目
        parts = content.rsplit("---", 1)
        if len(parts) == 2:
            new_content = parts[0] + "---" + entry + "\n"
        else:
            new_content = content + entry

        file_path.write_text(new_content, encoding="utf-8")

    def get_learnings(
        self,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取学习记录

        Args:
            category: 分类筛选
            limit: 返回数量

        Returns:
            学习记录列表
        """
        return self._parse_file(self.LEARNINGS_FILE, category, limit)

    def get_errors(
        self,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取错误记录

        Args:
            category: 分类筛选
            limit: 返回数量

        Returns:
            错误记录列表
        """
        return self._parse_file(self.ERRORS_FILE, category, limit)

    def get_feature_requests(
        self,
        priority: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取功能请求

        Args:
            priority: 优先级筛选
            limit: 返回数量

        Returns:
            功能请求列表
        """
        return self._parse_file(self.FEATURES_FILE, priority, limit)

    def _parse_file(
        self,
        file_path: Path,
        filter_key: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """解析文件内容"""
        if not file_path.exists():
            return []

        content = file_path.read_text(encoding="utf-8")

        # 分割条目
        entries = content.split("---")

        results = []
        for entry in entries:
            if not entry.strip() or entry.strip() == "\n":
                continue

            # 解析条目
            parsed = self._parse_entry(entry)

            if parsed:
                # 应用筛选
                if filter_key:
                    if parsed.get("category") == filter_key or parsed.get("priority") == filter_key:
                        results.append(parsed)
                else:
                    results.append(parsed)

            if len(results) >= limit:
                break

        return results

    def _parse_entry(self, entry: str) -> Optional[Dict[str, Any]]:
        """解析单个条目"""
        try:
            lines = entry.strip().split("\n")

            # 提取标题
            title_match = re.search(r"\[(.+?)\]\s+\[(.+?)\]\s+(.+)", lines[0] if lines else "")
            if not title_match:
                return None

            timestamp, priority, title = title_match.groups()

            # 提取分类和标签
            category = "general"
            tags = []

            for line in lines[1:]:
                if "**分类**:" in line:
                    category = line.split(":**")[1].strip()
                elif "**标签**:" in line:
                    tags_str = line.split(":**")[1].strip()
                    tags = [t.strip() for t in tags_str.split(",")]

            # 提取内容
            content_start = 0
            for i, line in enumerate(lines):
                if line.startswith("**分类**") or line.startswith("**标签**"):
                    content_start = i + 1

            content = "\n".join(lines[content_start:]).strip()

            return {
                "timestamp": timestamp,
                "priority": priority,
                "title": title,
                "category": category,
                "tags": tags,
                "content": content,
            }

        except Exception as e:
            logger.debug(f"解析条目失败: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "learnings_count": len(self.get_learnings(limit=1000)),
            "errors_count": len(self.get_errors(limit=1000)),
            "features_count": len(self.get_feature_requests(limit=1000)),
        }

        # 统计优先级分布
        errors = self.get_errors(limit=1000)
        priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for error in errors:
            p = error.get("priority", "medium").lower()
            if p in priority_counts:
                priority_counts[p] += 1

        stats["errors_by_priority"] = priority_counts

        return stats


# 全局实例
_experience_logger: Optional[ExperienceLogger] = None


def get_experience_logger() -> ExperienceLogger:
    """获取全局经验日志实例"""
    global _experience_logger
    if _experience_logger is None:
        _experience_logger = ExperienceLogger()
    return _experience_logger

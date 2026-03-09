"""
Memory Compaction Trigger - 内存压缩触发器

实现预压缩内存触发机制：
- 上下文窗口阈值检测
- 静默 Agent Turn 触发
- 持久化笔记生成

参考:
- OpenClaw: Pre-compaction memory flush
- https://gist.github.com/royosherove/971c7b4a350a30ac8a8dad41604a95a0
"""
import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


@dataclass
class MemorySnapshot:
    """内存快照"""
    id: str
    timestamp: datetime
    content_summary: str
    key_insights: List[str] = field(default_factory=list)
    pending_tasks: List[str] = field(default_factory=list)
    context_tokens: int = 0


class MemoryCompactionTrigger:
    """内存压缩触发器

    在上下文窗口耗尽前触发预压缩：
    1. 监控上下文使用率
    2. 达到阈值时触发静默 Agent Turn
    3. 生成持久化笔记
    4. 支持自定义压缩策略
    """

    # 默认阈值
    DEFAULT_THRESHOLD_RATIO = 0.8  # 80%
    DEFAULT_WINDOW_TOKENS = 128000  # GPT-4 默认窗口

    def __init__(
        self,
        threshold_ratio: float = DEFAULT_THRESHOLD_RATIO,
        max_tokens: int = DEFAULT_WINDOW_TOKENS,
        memory_dir: Path = None,
        compaction_handler: Optional[Callable[..., Any]] = None
    ):
        """初始化触发器

        Args:
            threshold_ratio: 触发阈值比例
            max_tokens: 最大 token 数
            memory_dir: 内存目录
            compaction_handler: 自定义压缩处理器
        """
        self.threshold_ratio = threshold_ratio
        self.max_tokens = max_tokens
        self.memory_dir = memory_dir or Path(".learnings/memory")
        self.compaction_handler = compaction_handler

        # 统计
        self._stats = {
            "triggers": 0,
            "skips": 0,
            "compactions": 0
        }

        # 状态
        self._last_compaction_time: Optional[float] = None
        self._cooldown_seconds = 300  # 5分钟冷却

        logger.info(f"MemoryCompactionTrigger initialized (threshold={threshold_ratio}, max_tokens={max_tokens})")

    def should_trigger(
        self,
        current_tokens: int,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """判断是否应该触发压缩

        Args:
            current_tokens: 当前 token 数
            context: 上下文

        Returns:
            bool: 是否应该触发
        """
        # 检查冷却时间
        if self._last_compaction_time:
            elapsed = time.time() - self._last_compaction_time
            if elapsed < self._cooldown_seconds:
                self._stats["skips"] += 1
                logger.debug(f"Compaction skipped (cooldown): {elapsed:.1f}s < {self._cooldown_seconds}s")
                return False

        # 检查阈值
        ratio = current_tokens / self.max_tokens
        should_trigger = ratio >= self.threshold_ratio

        if should_trigger:
            self._stats["triggers"] += 1
            logger.info(f"Compaction triggered (ratio={ratio:.2%}, tokens={current_tokens})")
        else:
            self._stats["skips"] += 1

        return should_trigger

    async def trigger(
        self,
        agent_context: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> MemorySnapshot:
        """触发压缩

        Args:
            agent_context: Agent 上下文
            system_prompt: 系统提示

        Returns:
            MemorySnapshot: 内存快照
        """
        logger.info("Starting memory compaction...")

        # 生成快照 ID
        snapshot_id = f"memory_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

        # 创建内存目录
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 构建提示
        prompt = system_prompt or self._build_compaction_prompt(agent_context)

        # 如果有自定义处理器，调用它
        if self.compaction_handler:
            try:
                if asyncio.iscoroutinefunction(self.compaction_handler):
                    await self.compaction_handler(prompt, agent_context)
                else:
                    self.compaction_handler(prompt, agent_context)
            except Exception as e:
                logger.error(f"Custom compaction handler failed: {e}")

        # 生成持久化笔记
        snapshot = await self._create_snapshot(
            snapshot_id,
            agent_context,
            prompt
        )

        # 保存笔记
        await self._save_snapshot(snapshot)

        # 更新状态
        self._last_compaction_time = time.time()
        self._stats["compactions"] += 1

        logger.info(f"Memory compaction completed: {snapshot_id}")

        return snapshot

    def _build_compaction_prompt(self, context: Dict[str, Any]) -> str:
        """构建压缩提示

        Args:
            context: 上下文

        Returns:
            str: 压缩提示
        """
        return f"""请分析当前会话的上下文，并将重要信息整理成持久化笔记。

当前上下文：
- 最近消息数：{context.get('message_count', 'unknown')}
- 会话时长：{context.get('session_duration', 'unknown')}
- 关键话题：{', '.join(context.get('topics', [])) or '无'}

请完成以下任务：
1. 提取关键洞察（最多5条）
2. 列出待完成的任务（最多5个）
3. 总结重要信息

输出格式：
## 关键洞察
- ...

## 待完成任务
- ...

## 重要总结
..."""

    async def _create_snapshot(
        self,
        snapshot_id: str,
        context: Dict[str, Any],
        prompt: str
    ) -> MemorySnapshot:
        """创建内存快照

        Args:
            snapshot_id: 快照 ID
            context: 上下文
            prompt: 提示

        Returns:
            MemorySnapshot: 快照
        """
        # 提取关键信息
        summary = context.get("summary", "No summary available")
        topics = context.get("topics", [])
        pending = context.get("pending_tasks", [])

        # 估算 token
        context_tokens = len(str(context).split()) * 1.3  # 粗略估算

        return MemorySnapshot(
            id=snapshot_id,
            timestamp=datetime.now(),
            content_summary=summary[:500],  # 限制长度
            key_insights=topics[:5],
            pending_tasks=pending[:5],
            context_tokens=int(context_tokens)
        )

    async def _save_snapshot(self, snapshot: MemorySnapshot):
        """保存快照

        Args:
            snapshot: 快照
        """
        # 文件名
        filename = f"{snapshot.id}.md"
        filepath = self.memory_dir / filename

        # 生成 Markdown 内容
        lines = [
            f"# Memory Snapshot - {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**ID**: {snapshot.id}",
            f"**Timestamp**: {snapshot.timestamp.isoformat()}",
            f"**Context Tokens**: ~{snapshot.context_tokens}",
            "",
            "## Summary",
            snapshot.content_summary,
            "",
        ]

        if snapshot.key_insights:
            lines.extend([
                "## Key Insights",
                *[f"- {insight}" for insight in snapshot.key_insights],
                "",
            ])

        if snapshot.pending_tasks:
            lines.extend([
                "## Pending Tasks",
                *[f"- {task}" for task in snapshot.pending_tasks],
                "",
            ])

        # 写入文件
        content = "\n".join(lines)
        filepath.write_text(content, encoding="utf-8")

        logger.info(f"Saved memory snapshot: {filepath}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计

        Returns:
            Dict: 统计信息
        """
        return {
            **self._stats,
            "last_compaction": self._last_compaction_time,
            "threshold_ratio": self.threshold_ratio,
            "max_tokens": self.max_tokens
        }

    def set_threshold(self, ratio: float):
        """设置阈值

        Args:
            ratio: 阈值比例
        """
        if 0 < ratio <= 1:
            self.threshold_ratio = ratio
            logger.info(f"Threshold ratio set to {ratio}")

    def reset_cooldown(self):
        """重置冷却时间"""
        self._last_compaction_time = None
        logger.info("Cooldown reset")


# ==================== 便捷函数 ====================

async def create_memory_note(
    content: str,
    category: str = "general",
    memory_dir: Path = None
) -> Path:
    """创建内存笔记

    Args:
        content: 内容
        category: 分类
        memory_dir: 目录

    Returns:
        Path: 文件路径
    """
    memory_dir = memory_dir or Path(".learnings/memory")
    memory_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{category}_{timestamp}.md"
    filepath = memory_dir / filename

    # 写入内容
    lines = [
        f"# {category.title()} - {timestamp}",
        "",
        content,
        "",
        f"---",
        f"*Created by MemoryCompactionTrigger*"
    ]

    filepath.write_text("\n".join(lines), encoding="utf-8")

    return filepath


def estimate_tokens(text: str) -> int:
    """估算 token 数

    Args:
        text: 文本

    Returns:
        int: 估算 token 数
    """
    # 简单估算：平均 1 token ≈ 0.75 单词
    words = len(text.split())
    return int(words / 0.75)


# ==================== 测试 ====================

if __name__ == "__main__":
    async def test():
        trigger = MemoryCompactionTrigger(threshold_ratio=0.5, max_tokens=1000)

        # 测试阈值检测
        print(f"Should trigger (500 tokens): {trigger.should_trigger(500)}")
        print(f"Should trigger (600 tokens): {trigger.should_trigger(600)}")

        # 测试触发
        context = {
            "message_count": 10,
            "session_duration": "1 hour",
            "topics": ["AI", "agents", "memory"],
            "pending_tasks": ["fix bug", "write tests"],
            "summary": "Discussed memory management in AI agents"
        }

        snapshot = await trigger.trigger(context)
        print(f"Snapshot: {snapshot.id}")
        print(f"Insights: {snapshot.key_insights}")

        # 统计
        print(f"Stats: {trigger.get_stats()}")

    asyncio.run(test())

"""
Heartbeat Checklist - 心跳检查清单

实现 OpenClaw 风格的 HEARTBEAT.md 检查机制：
- 加载检查清单
- 评估系统状态
- 决定是否推送

参考:
- OpenClaw: HEARTBEAT.md workspace file
- https://gist.github.com/royosherove/971c7b4a350a30ac8a8dad41604a95a0
"""
import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.heartbeat.response import HeartbeatResponse, HeartbeatStatus, Channel


# 默认检查清单路径
DEFAULT_CHECKLIST_PATH = Path(".learnings/HEARTBEAT.md")


@dataclass
class ChecklistItem:
    """检查项"""
    id: str
    name: str
    description: str
    condition: str  # 条件表达式
    action: str    # 触发动作
    enabled: bool = True
    severity: str = "info"  # info/warning/error


@dataclass
class EvaluationResult:
    """评估结果"""
    item_id: str
    triggered: bool
    message: str
    severity: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class HeartbeatChecklist:
    """心跳检查清单

    类似 OpenClaw 的 HEARTBEAT.md 工作区文件机制：
    - 检查清单定义在 .learnings/HEARTBEAT.md
    - 每个心跳周期评估清单项
    - 满足条件时生成告警
    """

    # 默认检查清单模板
    DEFAULT_ITEMS: List[ChecklistItem] = [
        ChecklistItem(
            id="error_rate",
            name="错误率检查",
            description="检查错误率是否超过阈值",
            condition="error_rate > 0.1",
            action="alert",
            severity="error"
        ),
        ChecklistItem(
            id="user_feedback",
            name="用户反馈检查",
            description="检查是否有负面反馈",
            condition="thumbs_down_count > 0",
            action="alert",
            severity="warning"
        ),
        ChecklistItem(
            id="inactive_users",
            name="用户活跃度检查",
            description="检查是否有用户长时间无交互",
            condition="inactive_hours > 24",
            action="alert",
            severity="info"
        ),
        ChecklistItem(
            id="skill_updates",
            name="技能更新检查",
            description="检查是否有可用技能更新",
            condition="pending_updates > 0",
            action="alert",
            severity="info"
        ),
        ChecklistItem(
            id="health_status",
            name="系统健康检查",
            description="检查系统组件健康状态",
            condition="unhealthy_components > 0",
            action="alert",
            severity="warning"
        ),
    ]

    def __init__(
        self,
        checklist_path: Optional[Path] = None,
        default_channel: str = Channel.DEFAULT.value
    ):
        """初始化检查清单

        Args:
            checklist_path: 检查清单文件路径
            default_channel: 默认推送通道
        """
        self.checklist_path = checklist_path or DEFAULT_CHECKLIST_PATH
        self.default_channel = default_channel
        self.items: List[ChecklistItem] = []
        self._last_evaluation: Optional[datetime] = None

    async def load(self) -> List[ChecklistItem]:
        """加载检查清单

        Returns:
            List[ChecklistItem]: 检查项列表
        """
        # 如果文件存在，从文件加载
        if self.checklist_path.exists():
            try:
                content = self.checklist_path.read_text(encoding="utf-8")
                self.items = self._parse_checklist(content)
                logger.info(f"Loaded {len(self.items)} checklist items from {self.checklist_path}")
            except Exception as e:
                logger.warning(f"Failed to load checklist: {e}, using defaults")
                self.items = self.DEFAULT_ITEMS.copy()
        else:
            # 使用默认检查清单
            self.items = self.DEFAULT_ITEMS.copy()
            logger.info(f"Using default checklist with {len(self.items)} items")

        return self.items

    def _parse_checklist(self, content: str) -> List[ChecklistItem]:
        """解析检查清单内容

        Args:
            content: 清单文件内容

        Returns:
            List[ChecklistItem]: 检查项列表
        """
        items = []

        # 解析 Markdown 格式的检查清单
        # 格式: - [ ] item_id: description
        pattern = r"- \[([ x])\] (\w+): (.+?)(?:\n|$)"

        for match in re.finditer(pattern, content):
            enabled = match.group(1) == " "
            item_id = match.group(2)
            description = match.group(3).strip()

            # 查找对应的默认项或创建新项
            default_item = next(
                (item for item in self.DEFAULT_ITEMS if item.id == item_id),
                None
            )

            if default_item:
                item = ChecklistItem(
                    id=item_id,
                    name=default_item.name,
                    description=description,
                    condition=default_item.condition,
                    action=default_item.action,
                    enabled=enabled,
                    severity=default_item.severity
                )
            else:
                # 未知的检查项，使用默认设置
                item = ChecklistItem(
                    id=item_id,
                    name=item_id,
                    description=description,
                    condition="true",  # 默认条件
                    action="alert",
                    enabled=enabled
                )

            items.append(item)

        return items if items else self.DEFAULT_ITEMS.copy()

    async def evaluate(
        self,
        context: Dict[str, Any]
    ) -> HeartbeatResponse:
        """评估检查清单

        Args:
            context: 评估上下文，包含:
                - error_rate: 错误率
                - thumbs_down_count: 负面反馈数
                - inactive_hours: 不活跃小时数
                - pending_updates: 待更新技能数
                - unhealthy_components: 不健康组件数
                - metrics: 指标数据

        Returns:
            HeartbeatResponse: 评估结果响应
        """
        if not self.items:
            await self.load()

        results: List[EvaluationResult] = []

        # 评估每个检查项
        for item in self.items:
            if not item.enabled:
                continue

            result = await self._evaluate_item(item, context)
            if result:
                results.append(result)

        self._last_evaluation = datetime.now()

        # 生成响应
        return self._generate_response(results, context)

    async def _evaluate_item(
        self,
        item: ChecklistItem,
        context: Dict[str, Any]
    ) -> Optional[EvaluationResult]:
        """评估单个检查项

        Args:
            item: 检查项
            context: 上下文

        Returns:
            Optional[EvaluationResult]: 评估结果
        """
        try:
            # 简单条件评估
            triggered = self._evaluate_condition(item.condition, context)

            if triggered:
                message = f"{item.name}: {item.description}"

                # 根据严重程度生成消息
                if item.severity == "error":
                    message = f"🔴 {message}"
                elif item.severity == "warning":
                    message = f"🟡 {message}"
                else:
                    message = f"🔵 {message}"

                return EvaluationResult(
                    item_id=item.id,
                    triggered=True,
                    message=message,
                    severity=item.severity,
                    metadata={"condition": item.condition, "action": item.action}
                )

        except Exception as e:
            logger.warning(f"Failed to evaluate item {item.id}: {e}")

        return None

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式

        Args:
            condition: 条件表达式
            context: 上下文

        Returns:
            bool: 是否触发
        """
        # 安全评估：只支持有限的变量和操作符
        # 格式: variable operator value

        # 提取变量名
        match = re.match(r"(\w+)\s*(>|<|>=|<=|==|!=)\s*(.+)", condition.strip())
        if not match:
            return False

        var_name, operator, value_str = match.groups()

        # 获取变量值
        context_value = context.get(var_name)

        # 解析比较值
        try:
            if value_str.lower() == "true":
                compare_value = True
            elif value_str.lower() == "false":
                compare_value = False
            else:
                compare_value = float(value_str)
        except ValueError:
            compare_value = value_str.strip("'\"")

        # 比较
        if context_value is None:
            return False

        if isinstance(context_value, bool):
            context_value = bool(context_value)
            if not isinstance(compare_value, bool):
                compare_value = compare_value == "True"

        try:
            if operator == ">":
                return context_value > compare_value
            elif operator == "<":
                return context_value < compare_value
            elif operator == ">=":
                return context_value >= compare_value
            elif operator == "<=":
                return context_value <= compare_value
            elif operator == "==":
                return context_value == compare_value
            elif operator == "!=":
                return context_value != compare_value
        except Exception:
            return False

        return False

    def _generate_response(
        self,
        results: List[EvaluationResult],
        context: Dict[str, Any]
    ) -> HeartbeatResponse:
        """生成响应

        Args:
            results: 评估结果列表
            context: 上下文

        Returns:
            HeartbeatResponse: 响应
        """
        if not results:
            # 没有触发项，返回 OK
            return HeartbeatResponse.ok({"checklist": "all clear"})

        # 分类结果
        errors = [r for r in results if r.severity == "error"]
        warnings = [r for r in results if r.severity == "warning"]
        infos = [r for r in results if r.severity == "info"]

        # 生成消息
        lines = ["## Heartbeat 检查报告\n"]

        if errors:
            lines.append(f"### 🔴 错误 ({len(errors)})")
            for r in errors:
                lines.append(f"- {r.message}")

        if warnings:
            lines.append(f"\n### 🟡 警告 ({len(warnings)})")
            for r in warnings:
                lines.append(f"- {r.message}")

        if infos:
            lines.append(f"\n### 🔵 信息 ({len(infos)})")
            for r in infos:
                lines.append(f"- {r.message}")

        content = "\n".join(lines)

        # 确定状态
        if errors:
            status = HeartbeatStatus.ERROR
        elif warnings:
            status = HeartbeatStatus.ALERT
        else:
            status = HeartbeatStatus.ALERT

        # 获取目标通道
        channel = context.get("channel", self.default_channel)

        return HeartbeatResponse(
            status=status,
            content=content,
            channel=channel,
            suppress=False,
            metadata={
                "results": [
                    {
                        "id": r.item_id,
                        "message": r.message,
                        "severity": r.severity
                    }
                    for r in results
                ],
                "error_count": len(errors),
                "warning_count": len(warnings),
                "info_count": len(infos),
            }
        )

    async def save(self, items: Optional[List[ChecklistItem]] = None):
        """保存检查清单

        Args:
            items: 检查项列表，None 则保存当前项
        """
        items = items or self.items

        # 确保目录存在
        self.checklist_path.parent.mkdir(parents=True, exist_ok=True)

        # 生成 Markdown 内容
        lines = ["# Heartbeat 检查清单\n"]
        lines.append("使用 `[ ]` 标记启用/禁用检查项\n")

        for item in items:
            checkbox = " " if item.enabled else "x"
            lines.append(f"- [{checkbox}] {item.id}: {item.description}")

        content = "\n".join(lines)
        self.checklist_path.write_text(content, encoding="utf-8")

        logger.info(f"Saved checklist to {self.checklist_path}")


# ==================== 便捷函数 ====================

async def create_default_checklist(path: Path = DEFAULT_CHECKLIST_PATH):
    """创建默认检查清单

    Args:
        path: 清单路径
    """
    checklist = HeartbeatChecklist(path)
    await checklist.load()
    await checklist.save()


# ==================== 测试 ====================

if __name__ == "__main__":
    async def test():
        # 测试评估
        checklist = HeartbeatChecklist()
        await checklist.load()

        # 模拟上下文
        context = {
            "error_rate": 0.15,  # > 0.1, should trigger
            "thumbs_down_count": 0,
            "inactive_hours": 2,
            "pending_updates": 0,
            "unhealthy_components": 0,
        }

        response = await checklist.evaluate(context)

        print(f"Response status: {response.status}")
        print(f"Should push: {response.should_push()}")
        print(f"Content:\n{response.content}")

    asyncio.run(test())

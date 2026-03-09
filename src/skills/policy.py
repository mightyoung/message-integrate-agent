"""
Tool Policy - 工具访问策略

实现 OpenClaw 风格的工具访问控制：
- 分层 allow/deny 策略
- 核心工具定义
- Agent 特定策略

参考:
- OpenClaw: Tool allow/deny policy
- https://gist.github.com/royosherove/971c7b4a350a30ac8a8dad41604a95a0
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from loguru import logger


class PolicyEffect(str, Enum):
    """策略效果"""
    ALLOW = "allow"
    DENY = "deny"


# 核心工具 - 始终可用的基础工具
CORE_TOOLS: Set[str] = {
    # 文件操作
    "read",
    "write",
    "edit",
    "delete",
    "list",

    # 执行
    "exec",
    "process",
    "run",

    # 记忆
    "search_memory",
    "write_memory",
    "read_memory",

    # 子 Agent
    "sub_agent",
    "spawn_agent",

    # 消息
    "send_message",
    "receive_message",

    # 系统
    "health_check",
    "get_status",
}


@dataclass
class ToolPolicyRule:
    """工具策略规则"""
    tool_pattern: str  # 工具名称或通配符
    effect: PolicyEffect
    agent_id: Optional[str] = None  # None 表示全局规则


class ToolPolicy:
    """工具访问策略控制器

    策略优先级（从高到低）：
    1. global_deny: 全局拒绝
    2. agent_deny: Agent 特定拒绝
    3. global_allow: 全局允许
    4. agent_allow: Agent 特定允许
    5. default: 默认拒绝

    核心工具始终可用，不受策略影响。
    """

    def __init__(self, default_effect: PolicyEffect = PolicyEffect.DENY):
        """初始化策略控制器

        Args:
            default_effect: 默认效果
        """
        self.default_effect = default_effect
        self._rules: List[ToolPolicyRule] = []

        # 缓存
        self._cache: Dict[str, bool] = {}
        self._cache_enabled = True

        logger.info(f"ToolPolicy initialized with default: {default_effect.value}")

    def add_rule(
        self,
        tool_pattern: str,
        effect: PolicyEffect,
        agent_id: Optional[str] = None
    ):
        """添加策略规则

        Args:
            tool_pattern: 工具名称或通配符 (*, ?)
            effect: 效果 (allow/deny)
            agent_id: Agent ID，None 表示全局规则
        """
        rule = ToolPolicyRule(
            tool_pattern=tool_pattern,
            effect=effect,
            agent_id=agent_id
        )
        self._rules.append(rule)

        # 清除缓存
        self._clear_cache()

        logger.debug(f"Added rule: {effect.value} {tool_pattern}" +
                    (f" for agent {agent_id}" if agent_id else " (global)"))

    def remove_rule(
        self,
        tool_pattern: str,
        agent_id: Optional[str] = None
    ) -> bool:
        """移除策略规则

        Args:
            tool_pattern: 工具名称
            agent_id: Agent ID

        Returns:
            bool: 是否成功移除
        """
        original_count = len(self._rules)
        self._rules = [
            r for r in self._rules
            if not (r.tool_pattern == tool_pattern and
                   (agent_id is None or r.agent_id == agent_id))
        ]

        removed = len(self._rules) < original_count
        if removed:
            self._clear_cache()

        return removed

    def is_allowed(
        self,
        tool_name: str,
        agent_id: Optional[str] = None
    ) -> bool:
        """检查工具是否允许访问

        Args:
            tool_name: 工具名称
            agent_id: Agent ID

        Returns:
            bool: 是否允许
        """
        # 核心工具始终允许
        if tool_name in CORE_TOOLS:
            return True

        # 检查缓存
        cache_key = f"{agent_id or 'global'}:{tool_name}"
        if self._cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]

        # 按优先级检查规则
        result = self._evaluate(tool_name, agent_id)

        # 缓存结果
        if self._cache_enabled:
            self._cache[cache_key] = result

        return result

    def _evaluate(
        self,
        tool_name: str,
        agent_id: Optional[str]
    ) -> bool:
        """评估工具访问

        Args:
            tool_name: 工具名称
            agent_id: Agent ID

        Returns:
            bool: 是否允许
        """
        # 优先级列表（从高到低）
        priority_rules = [
            # 1. 全局拒绝
            (PolicyEffect.DENY, None),
            # 2. Agent 特定拒绝
            (PolicyEffect.DENY, agent_id),
            # 3. 全局允许
            (PolicyEffect.ALLOW, None),
            # 4. Agent 特定允许
            (PolicyEffect.ALLOW, agent_id),
        ]

        for effect, rule_agent_id in priority_rules:
            # 查找匹配的规则
            matching_rules = [
                r for r in self._rules
                if r.effect == effect and
                   (rule_agent_id is None or r.agent_id == rule_agent_id) and
                   self._match_pattern(tool_name, r.tool_pattern)
            ]

            if matching_rules:
                return effect == PolicyEffect.ALLOW

        # 使用默认策略
        return self.default_effect == PolicyEffect.ALLOW

    def _match_pattern(self, tool_name: str, pattern: str) -> bool:
        """匹配工具名称模式

        Args:
            tool_name: 工具名称
            pattern: 模式（支持 * 和 ?）

        Returns:
            bool: 是否匹配
        """
        if pattern == tool_name:
            return True

        if "*" in pattern or "?" in pattern:
            import re
            # 转换通配符为正则表达式
            regex_pattern = pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
            regex_pattern = f"^{regex_pattern}$"
            return bool(re.match(regex_pattern, tool_name))

        return False

    def _clear_cache(self):
        """清除缓存"""
        self._cache.clear()

    def disable_cache(self):
        """禁用缓存"""
        self._cache_enabled = False
        self._clear_cache()

    def enable_cache(self):
        """启用缓存"""
        self._cache_enabled = True

    def get_rules(
        self,
        agent_id: Optional[str] = None
    ) -> List[ToolPolicyRule]:
        """获取规则列表

        Args:
            agent_id: Agent ID，None 表示全局规则

        Returns:
            List[ToolPolicyRule]: 规则列表
        """
        if agent_id is None:
            return [r for r in self._rules if r.agent_id is None]
        return [r for r in self._rules if r.agent_id == agent_id]

    def get_allowed_tools(
        self,
        agent_id: Optional[str] = None
    ) -> Set[str]:
        """获取允许的工具列表

        Args:
            agent_id: Agent ID

        Returns:
            Set[str]: 允许的工具集合
        """
        # 从规则推断允许的工具
        allowed = set(CORE_TOOLS)

        for rule in self._rules:
            if rule.agent_id is None or rule.agent_id == agent_id:
                if rule.effect == PolicyEffect.ALLOW:
                    # 添加工具到允许列表
                    if "*" in rule.tool_pattern or "?" in rule.tool_pattern:
                        # 需要更复杂的处理
                        pass
                    else:
                        allowed.add(rule.tool_pattern)
                elif rule.effect == PolicyEffect.DENY:
                    # 从允许列表移除
                    allowed.discard(rule.tool_pattern)

        return allowed

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            Dict: 策略字典
        """
        return {
            "default_effect": self.default_effect.value,
            "core_tools": list(CORE_TOOLS),
            "rules": [
                {
                    "tool_pattern": r.tool_pattern,
                    "effect": r.effect.value,
                    "agent_id": r.agent_id
                }
                for r in self._rules
            ]
        }


# ==================== 全局策略实例 ====================

# 全局工具策略
_default_policy = ToolPolicy()


def get_default_policy() -> ToolPolicy:
    """获取默认策略

    Returns:
        ToolPolicy: 默认策略
    """
    return _default_policy


def is_tool_allowed(tool_name: str, agent_id: Optional[str] = None) -> bool:
    """快速检查工具是否允许

    Args:
        tool_name: 工具名称
        agent_id: Agent ID

    Returns:
        bool: 是否允许
    """
    return _default_policy.is_allowed(tool_name, agent_id)


# ==================== 测试 ====================

if __name__ == "__main__":
    # 测试
    policy = ToolPolicy()

    # 添加规则
    policy.add_rule("file.*", PolicyEffect.ALLOW)  # 允许所有文件操作
    policy.add_rule("network.*", PolicyEffect.DENY)  # 拒绝所有网络操作
    policy.add_rule("dangerous_tool", PolicyEffect.DENY, "agent_123")

    # 测试
    print(f"read allowed: {policy.is_allowed('read')}")  # True (core)
    print(f"file.write allowed: {policy.is_allowed('file.write')}")  # True
    print(f"network.fetch allowed: {policy.is_allowed('network.fetch')}")  # False
    print(f"dangerous_tool allowed (no agent): {policy.is_allowed('dangerous_tool')}")  # False
    print(f"dangerous_tool allowed (agent_123): {policy.is_allowed('dangerous_tool', 'agent_123')}")  # False

    # 获取允许的工具
    allowed = policy.get_allowed_tools()
    print(f"Allowed tools: {allowed}")

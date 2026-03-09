"""
Agents module - Agent 循环与协作系统

包含:
- AgentLoop: 标准化 Agent 循环 (THINK→ACT→OBSERVE→REFLECT)
- CheckpointManager: 状态持久化
- AgentCollaborationSystem: 多角色协作
- TodoEnforcer: 任务监督
"""
from src.agents.loop import (
    AgentLoop,
    AgentContext,
    LoopStep,
    LoopResult,
    LoopState,
    StepStatus,
    create_loop,
)
from src.agents.checkpoint import (
    CheckpointManager,
    Checkpoint,
    create_checkpoint_manager,
)
from src.agents.roles import (
    AgentCollaborationSystem,
    BaseRole,
    PrometheusRole,
    HephaestusRole,
    SisyphusRole,
    RoleType,
    AgentStatus,
    create_collaboration_system,
)
from src.agents.enforcer import (
    TodoEnforcer,
    TodoItem,
    TodoStatus,
    TaskPriority,
    EnforcerConfig,
    create_enforcer,
)

__all__ = [
    # Loop
    "AgentLoop",
    "AgentContext",
    "LoopStep",
    "LoopResult",
    "LoopState",
    "StepStatus",
    "create_loop",
    # Checkpoint
    "CheckpointManager",
    "Checkpoint",
    "create_checkpoint_manager",
    # Roles
    "AgentCollaborationSystem",
    "BaseRole",
    "PrometheusRole",
    "HephaestusRole",
    "SisyphusRole",
    "RoleType",
    "AgentStatus",
    "create_collaboration_system",
    # Enforcer
    "TodoEnforcer",
    "TodoItem",
    "TodoStatus",
    "TaskPriority",
    "EnforcerConfig",
    "create_enforcer",
]

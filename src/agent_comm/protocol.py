"""
Agent Communication Protocols

定义 Agent 间通信的协议格式
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(Enum):
    """消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    EVENT = "event"


class Priority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class AgentMessage:
    """Agent 间通信消息格式"""
    id: str
    type: MessageType
    sender: str
    receiver: str
    content: Any
    action: Optional[str] = None
    priority: Priority = Priority.NORMAL
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "action": self.action,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(
            id=data["id"],
            type=MessageType(data["type"]),
            sender=data["sender"],
            receiver=data["receiver"],
            content=data["content"],
            action=data.get("action"),
            priority=Priority(data.get("priority", 2)),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
            correlation_id=data.get("correlation_id"),
        )


@dataclass
class AgentStatus:
    """Agent 状态"""
    name: str
    status: str  # online, offline, busy, error
    capabilities: List[str] = field(default_factory=list)
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Command:
    """指令格式"""
    id: str
    type: str  # execute, query, subscribe
    target: str  # agent name or service name
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    retry: int = 0


@dataclass
class CommandResult:
    """指令执行结果"""
    command_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

"""
Heartbeat Response Contract - 心跳响应契约

实现 OpenClaw 风格的响应契约：
- HEARTBEAT_OK: 静默，不推送
- HEARTBEAT_ALERT: 推送到指定通道
- HEARTBEAT_ERROR: 错误状态

参考:
- OpenClaw: https://gist.github.com/royosherove/971c7b4a350a30ac8a8dad41604a95a0
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import hashlib
import time


class HeartbeatStatus(str, Enum):
    """心跳状态枚举"""
    OK = "ok"
    ALERT = "alert"
    ERROR = "error"


class Channel(str, Enum):
    """预定义通道"""
    DEFAULT = "default"
    TELEGRAM = "telegram"
    FEISHU = "feishu"
    WECHAT = "wechat"
    ALL = "all"


@dataclass
class HeartbeatResponse:
    """心跳响应契约

    Attributes:
        status: 响应状态 (ok/alert/error)
        content: 推送内容 (alert/error 时)
        channel: 目标通道 (telegram:user_id / feishu:open_id)
        suppress: 是否静默 (True = 不推送)
        metadata: 附加元数据
        timestamp: 响应时间戳
    """
    status: HeartbeatStatus
    content: str = ""
    channel: str = Channel.DEFAULT.value
    suppress: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    # 特殊标记
    IS_HEARTBEAT_OK: bool = field(default=False, repr=False)
    IS_HEARTBEAT_ERROR: bool = field(default=False, repr=False)

    def __post_init__(self):
        """后处理初始化"""
        if isinstance(self.status, str):
            self.status = HeartbeatStatus(self.status)

        # 设置特殊标记
        self.IS_HEARTBEAT_OK = self.status == HeartbeatStatus.OK
        self.IS_HEARTBEAT_ERROR = self.status == HeartbeatStatus.ERROR

        # 如果是 ok 状态，自动设置 suppress=True
        if self.status == HeartbeatStatus.OK:
            self.suppress = True

    # ==================== 工厂方法 ====================

    @classmethod
    def ok(cls, metadata: Optional[Dict[str, Any]] = None) -> "HeartbeatResponse":
        """创建 OK 响应 - 静默，不推送

        Args:
            metadata: 附加元数据

        Returns:
            HeartbeatResponse: OK 响应
        """
        return cls(
            status=HeartbeatStatus.OK,
            content="",
            channel=Channel.DEFAULT.value,
            suppress=True,
            metadata=metadata or {},
        )

    @classmethod
    def alert(
        cls,
        content: str,
        channel: str = Channel.DEFAULT.value,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "HeartbeatResponse":
        """创建 ALERT 响应 - 推送到指定通道

        Args:
            content: 推送内容
            channel: 目标通道 (格式: "platform:user_id")
            metadata: 附加元数据

        Returns:
            HeartbeatResponse: 告警响应
        """
        return cls(
            status=HeartbeatStatus.ALERT,
            content=content,
            channel=channel,
            suppress=False,
            metadata=metadata or {},
        )

    @classmethod
    def error(
        cls,
        content: str,
        channel: str = Channel.DEFAULT.value,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "HeartbeatResponse":
        """创建 ERROR 响应 - 错误状态

        Args:
            content: 错误信息
            channel: 目标通道
            metadata: 附加元数据

        Returns:
            HeartbeatResponse: 错误响应
        """
        return cls(
            status=HeartbeatStatus.ERROR,
            content=content,
            channel=channel,
            suppress=False,
            metadata=metadata or {},
        )

    # ==================== 便捷方法 ====================

    def should_push(self) -> bool:
        """判断是否应该推送

        Returns:
            bool: True 如果需要推送
        """
        return not self.suppress and self.content

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            Dict: 响应字典
        """
        return {
            "status": self.status.value,
            "content": self.content,
            "channel": self.channel,
            "suppress": self.suppress,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "should_push": self.should_push(),
        }

    def to_push_message(self) -> Optional[Dict[str, Any]]:
        """转换为推送消息格式

        Returns:
            Optional[Dict]: 推送消息，如果不应该推送则返回 None
        """
        if not self.should_push():
            return None

        return {
            "content": self.content,
            "channel": self.channel,
            "metadata": {
                "type": "heartbeat_alert",
                "status": self.status.value,
                "timestamp": self.timestamp,
                **self.metadata,
            },
        }

    # ==================== 解析方法 ====================

    @classmethod
    def from_agent_result(
        cls,
        result: Dict[str, Any],
        default_channel: str = Channel.DEFAULT.value
    ) -> "HeartbeatResponse":
        """从 Agent 结果解析响应

        Args:
            result: Agent 执行结果
            default_channel: 默认通道

        Returns:
            HeartbeatResponse: 解析后的响应
        """
        # 检查特殊标记
        content = result.get("content", "")
        status_str = result.get("status", "").upper()

        if status_str == "HEARTBEAT_OK" or "HEARTBEAT_OK" in content:
            return cls.ok(result.get("metadata"))

        if status_str == "HEARTBEAT_ERROR" or "ERROR" in status_str:
            return cls.error(
                content=result.get("error", content) or "Unknown error",
                channel=result.get("channel", default_channel),
                metadata=result.get("metadata"),
            )

        # 检查是否需要告警
        if result.get("needs_alert") or result.get("alert"):
            return cls.alert(
                content=content,
                channel=result.get("channel", default_channel),
                metadata=result.get("metadata"),
            )

        # 默认返回 OK
        return cls.ok(result.get("metadata"))


# ==================== 便捷函数 ====================

def create_idempotency_key(command: str, args: Dict[str, Any]) -> str:
    """创建幂等性 key

    Args:
        command: 命令名称
        args: 命令参数

    Returns:
        str: 幂等性 key
    """
    # 排序键值对以确保一致性
    sorted_args = sorted(args.items())
    key_data = f"{command}:{sorted_args}:{int(time.time() // 3600)}"  # 小时级精度

    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


def parse_channel(channel_str: str) -> tuple[str, str]:
    """解析通道字符串

    Args:
        channel_str: 通道字符串 (格式: "platform:user_id")

    Returns:
        tuple[str, str]: (平台, 用户ID)
    """
    if ":" in channel_str:
        platform, user_id = channel_str.split(":", 1)
        return platform, user_id

    return channel_str, ""


# ==================== 测试 ====================

if __name__ == "__main__":
    # 测试工厂方法
    response_ok = HeartbeatResponse.ok({"test": "metadata"})
    print(f"OK Response: {response_ok}")
    print(f"  should_push: {response_ok.should_push()}")
    print(f"  suppress: {response_ok.suppress}")

    response_alert = HeartbeatResponse.alert(
        "System error rate > 10%",
        channel="telegram:123456",
        metadata={"error_rate": 0.15}
    )
    print(f"\nAlert Response: {response_alert}")
    print(f"  should_push: {response_alert.should_push()}")
    print(f"  to_push_message: {response_alert.to_push_message()}")

    response_error = HeartbeatResponse.error("Connection failed")
    print(f"\nError Response: {response_error}")
    print(f"  should_push: {response_error.should_push()}")

    # 测试从 Agent 结果解析
    result = {"content": "All systems normal", "status": "HEARTBEAT_OK"}
    parsed = HeartbeatResponse.from_agent_result(result)
    print(f"\nParsed from agent result: {parsed}")

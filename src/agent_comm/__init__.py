"""
Agent Communication Module

实现 Agent 间通信：
- Service Registry: 服务注册与发现
- RPC Client: 远程过程调用
- Message Queue: 异步消息队列

设计参考：
- Consul/etcd: 服务注册与发现
- gRPC: 远程过程调用
- Redis Pub/Sub: 消息队列
"""
import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

from loguru import logger


class ServiceStatus(Enum):
    """服务状态"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPED = "stopped"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    host: str
    port: int
    protocol: str = "http"
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_heartbeat: Optional[datetime] = None
    version: str = "1.0.0"


@dataclass
class RPCRequest:
    """RPC 请求"""
    id: str
    service: str
    method: str
    params: Dict[str, Any]
    timeout: float = 30.0


@dataclass
class RPCResponse:
    """RPC 响应"""
    id: str
    success: bool
    result: Any = None
    error: Optional[str] = None


class ServiceRegistry:
    """
    服务注册中心

    实现服务注册、发现和健康检查
    类似于 Consul/etcd 的简化版
    """

    def __init__(self, heartbeat_ttl: int = 30):
        """
        初始化服务注册中心

        Args:
            heartbeat_ttl: 心跳超时时间（秒）
        """
        self.heartbeat_ttl = heartbeat_ttl
        self.services: Dict[str, ServiceInfo] = {}
        self.handlers: Dict[str, Callable] = {}

        # 健康检查任务
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False

    def register(self, service: ServiceInfo) -> bool:
        """
        注册服务

        Args:
            service: 服务信息

        Returns:
            是否注册成功
        """
        service.last_heartbeat = datetime.now()
        self.services[service.name] = service
        logger.info(f"📝 注册服务: {service.name} ({service.host}:{service.port})")
        return True

    def unregister(self, service_name: str) -> bool:
        """
        注销服务

        Args:
            service_name: 服务名称

        Returns:
            是否注销成功
        """
        if service_name in self.services:
            del self.services[service_name]
            logger.info(f"🗑️ 注销服务: {service_name}")
            return True
        return False

    def discover(self, service_name: str) -> Optional[ServiceInfo]:
        """
        发现服务

        Args:
            service_name: 服务名称

        Returns:
            服务信息或 None
        """
        service = self.services.get(service_name)
        if service and service.status == ServiceStatus.HEALTHY:
            return service
        return None

    def discover_all(self, status: Optional[ServiceStatus] = None) -> List[ServiceInfo]:
        """
        发现所有服务

        Args:
            status: 服务状态过滤

        Returns:
            服务列表
        """
        if status:
            return [
                s for s in self.services.values()
                if s.status == status
            ]
        return list(self.services.values())

    def update_heartbeat(self, service_name: str) -> bool:
        """
        更新服务心跳

        Args:
            service_name: 服务名称

        Returns:
            是否更新成功
        """
        if service_name in self.services:
            self.services[service_name].last_heartbeat = datetime.now()
            self.services[service_name].status = ServiceStatus.HEALTHY
            return True
        return False

    def register_handler(self, service_name: str, handler: Callable):
        """
        注册服务处理器

        Args:
            service_name: 服务名称
            handler: 处理函数
        """
        self.handlers[service_name] = handler

    async def call_handler(
        self,
        service_name: str,
        method: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        调用服务处理器

        Args:
            service_name: 服务名称
            method: 方法名
            params: 参数

        Returns:
            调用结果
        """
        handler = self.handlers.get(service_name)
        if not handler:
            raise ValueError(f"服务处理器未注册: {service_name}")

        if asyncio.iscoroutinefunction(handler):
            return await handler(method, params)
        return handler(method, params)

    async def start_health_check(self):
        """启动健康检查"""
        if self._running:
            return

        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("💓 服务健康检查已启动")

    async def stop_health_check(self):
        """停止健康检查"""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("💓 服务健康检查已停止")

    async def _health_check_loop(self):
        """健康检查循环"""
        while self._running:
            try:
                await self._check_services()
            except Exception as e:
                logger.error(f"健康检查错误: {e}")

            await asyncio.sleep(5)

    async def _check_services(self):
        """检查服务健康状态"""
        now = datetime.now()
        timeout = timedelta(seconds=self.heartbeat_ttl)

        for name, service in list(self.services.items()):
            if service.last_heartbeat:
                if now - service.last_heartbeat > timeout:
                    service.status = ServiceStatus.UNHEALTHY
                    logger.warning(f"⚠️ 服务超时: {name}")


# 全局服务注册中心
_service_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """获取全局服务注册中心"""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry


class RPCClient:
    """
    RPC 客户端

    用于远程调用其他 Agent 的服务
    """

    def __init__(self, registry: ServiceRegistry):
        """
        初始化 RPC 客户端

        Args:
            registry: 服务注册中心
        """
        self.registry = registry

    async def call(
        self,
        service: str,
        method: str,
        params: Dict[str, Any],
        timeout: float = 30.0
    ) -> Any:
        """
        发起 RPC 调用

        Args:
            service: 服务名称
            method: 方法名
            params: 参数
            timeout: 超时时间

        Returns:
            调用结果

        Raises:
            ValueError: 服务不存在
            asyncio.TimeoutError: 调用超时
        """
        # 发现服务
        service_info = self.registry.discover(service)
        if not service_info:
            # 尝试本地处理器
            try:
                return await self.registry.call_handler(service, method, params)
            except ValueError:
                raise ValueError(f"服务未发现: {service}")

        # 构建请求
        request = RPCRequest(
            id=f"{service}:{method}:{datetime.now().timestamp()}",
            service=service,
            method=method,
            params=params,
            timeout=timeout
        )

        # 使用 HTTP 调用（简化实现）
        import httpx
        url = f"{service_info.protocol}://{service_info.host}:{service_info.port}/rpc/{method}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json={
                    "id": request.id,
                    "params": request.params
                })

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        return data.get("result")
                    else:
                        raise Exception(data.get("error", "Unknown error"))
                else:
                    raise Exception(f"HTTP {response.status_code}")

        except asyncio.TimeoutError:
            logger.error(f"⏱️ RPC 调用超时: {service}.{method}")
            raise
        except Exception as e:
            logger.error(f"❌ RPC 调用失败: {service}.{method} - {e}")
            raise


class MessageQueue:
    """
    消息队列

    实现异步消息传递
    类似于 Redis Pub/Sub 的简化版
    """

    def __init__(self):
        """初始化消息队列"""
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._running = False

    def subscribe(self, topic: str) -> asyncio.Queue:
        """
        订阅主题

        Args:
            topic: 主题名称

        Returns:
            消息队列
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = []

        queue = asyncio.Queue()
        self.subscribers[topic].append(queue)
        logger.info(f"📥 订阅主题: {topic}")
        return queue

    def unsubscribe(self, topic: str, queue: asyncio.Queue):
        """
        取消订阅

        Args:
            topic: 主题名称
            queue: 队列
        """
        if topic in self.subscribers:
            if queue in self.subscribers[topic]:
                self.subscribers[topic].remove(queue)
                logger.info(f"📤 取消订阅: {topic}")

    async def publish(self, topic: str, message: Any):
        """
        发布消息

        Args:
            topic: 主题名称
            message: 消息内容
        """
        if topic not in self.subscribers:
            return

        for queue in self.subscribers[topic]:
            await queue.put(message)

        logger.debug(f"📨 发布消息: {topic}")

    async def publish_json(self, topic: str, data: Dict[str, Any]):
        """发布 JSON 消息"""
        await self.publish(topic, json.dumps(data))


# 全局消息队列
_message_queue: Optional[MessageQueue] = None


def get_message_queue() -> MessageQueue:
    """获取全局消息队列"""
    global _message_queue
    if _message_queue is None:
        _message_queue = MessageQueue()
    return _message_queue


class AgentCommunicator:
    """
    Agent 通信器

    统一接口，整合服务注册、RPC 和消息队列
    """

    def __init__(self):
        self.registry = get_service_registry()
        self.rpc = RPCClient(self.registry)
        self.queue = get_message_queue()

        # 本地服务
        self.local_services: Dict[str, Callable] = {}

    def register_local_service(
        self,
        name: str,
        handler: Callable,
        host: str = "localhost",
        port: int = 8080
    ):
        """
        注册本地服务

        Args:
            name: 服务名称
            handler: 处理函数
            host: 主机
            port: 端口
        """
        service = ServiceInfo(
            name=name,
            host=host,
            port=port,
            status=ServiceStatus.HEALTHY
        )
        self.registry.register(service)
        self.registry.register_handler(name, handler)
        self.local_services[name] = handler

    async def send_to_agent(
        self,
        agent_name: str,
        action: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        发送消息给 Agent

        Args:
            agent_name: Agent 名称
            action: 动作
            params: 参数

        Returns:
            响应
        """
        return await self.rpc.call(agent_name, action, params)

    async def broadcast_to_agents(
        self,
        message: Dict[str, Any],
        agent_filter: Optional[List[str]] = None
    ):
        """
        广播消息给多个 Agent

        Args:
            message: 消息
            agent_filter: Agent 过滤列表
        """
        agents = self.registry.discover_all(ServiceStatus.HEALTHY)

        if agent_filter:
            agents = [a for a in agents if a.name in agent_filter]

        tasks = []
        for agent in agents:
            try:
                task = asyncio.create_task(
                    self.rpc.call(agent.name, "handle", message)
                )
                tasks.append(task)
            except Exception as e:
                logger.error(f"广播失败 {agent.name}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def subscribe_to_agent(self, agent_name: str) -> asyncio.Queue:
        """
        订阅 Agent 消息

        Args:
            agent_name: Agent 名称

        Returns:
            消息队列
        """
        return self.queue.subscribe(f"agent:{agent_name}")

    async def publish_to_agent(
        self,
        agent_name: str,
        message: Dict[str, Any]
    ):
        """
        发布消息给 Agent

        Args:
            agent_name: Agent 名称
            message: 消息
        """
        await self.queue.publish(f"agent:{agent_name}", message)


# 全局通信器
_communicator: Optional[AgentCommunicator] = None


def get_agent_communicator() -> AgentCommunicator:
    """获取全局 Agent 通信器"""
    global _communicator
    if _communicator is None:
        _communicator = AgentCommunicator()
    return _communicator

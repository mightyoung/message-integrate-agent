"""
A2A Protocol - Agent-to-Agent Communication

基于 Google A2A Protocol 实现:
- JSON-RPC over HTTP
- Task 提交、状态查询、结果获取
- Event streaming for task updates
- Agent Card discovery

参考: https://github.com/a2aproject/A2A
"""
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from loguru import logger


class TaskState(Enum):
    """任务状态"""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class Task:
    """A2A Task"""
    id: str
    agent_name: str
    input_data: Dict[str, Any]
    state: TaskState = TaskState.SUBMITTED
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    history: List[Dict[str, Any]] = field(default_factory=list)

    def add_history(self, event: Dict[str, Any]):
        """添加历史事件"""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            **event
        })
        self.updated_at = datetime.now().isoformat()


@dataclass
class A2ARequest:
    """A2A JSON-RPC Request"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class A2AResponse:
    """A2A JSON-RPC Response"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        if self.error:
            return {
                "jsonrpc": self.jsonrpc,
                "id": self.id,
                "error": self.error,
            }
        return {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "result": self.result,
        }


class A2AServer:
    """
    A2A Protocol Server

    实现核心 A2A 端点:
    - tasks/send: 提交任务
    - tasks/get: 获取任务状态
    - tasks/cancel: 取消任务
    - agentCards/list: 列出可用 Agent
    """

    def __init__(
        self,
        agent_card_registry=None,
        host: str = "0.0.0.0",
        port: int = 8000,
    ):
        self.host = host
        self.port = port
        self.card_registry = agent_card_registry

        # Task storage
        self._tasks: Dict[str, Task] = {}
        self._task_handlers: Dict[str, Callable] = {}

        # Event queues for streaming
        self._event_queues: Dict[str, asyncio.Queue] = {}

        logger.info(f"📡 A2A Server initialized on {host}:{port}")

    def register_handler(self, agent_name: str, handler: Callable):
        """
        注册任务处理器

        Args:
            agent_name: Agent 名称
            handler: 异步处理函数 (task: Task) -> result
        """
        self._task_handlers[agent_name] = handler
        logger.info(f"✅ Registered handler for agent: {agent_name}")

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理 A2A 请求

        Args:
            request: JSON-RPC 请求

        Returns:
            JSON-RPC 响应
        """
        try:
            # Parse request
            req = A2ARequest(
                jsonrpc=request.get("jsonrpc", "2.0"),
                id=request.get("id"),
                method=request.get("method", ""),
                params=request.get("params", {}),
            )

            # Route to handler
            if req.method == "tasks/send":
                result = await self._handle_send_task(req.params)
            elif req.method == "tasks/get":
                result = await self._handle_get_task(req.params)
            elif req.method == "tasks/cancel":
                result = await self._handle_cancel_task(req.params)
            elif req.method == "tasks/subscribe":
                result = await self._handle_subscribe(req.params)
            elif req.method == "agents/list":
                result = await self._handle_list_agents()
            elif req.method == "agents/get":
                result = await self._handle_get_agent(req.params)
            else:
                return A2AResponse(
                    id=req.id,
                    error={
                        "code": -32601,
                        "message": f"Method not found: {req.method}",
                    },
                ).to_dict()

            return A2AResponse(id=req.id, result=result).to_dict()

        except Exception as e:
            logger.error(f"❌ A2A request error: {e}")
            return A2AResponse(
                id=request.get("id"),
                error={
                    "code": -32603,
                    "message": str(e),
                },
            ).to_dict()

    async def _handle_send_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务提交"""
        agent_name = params.get("agentName")
        input_data = params.get("input", {})

        if not agent_name:
            raise ValueError("agentName is required")

        # Create task
        task_id = params.get("taskId") or f"task_{uuid4().hex[:12]}"
        task = Task(
            id=task_id,
            agent_name=agent_name,
            input_data=input_data,
        )
        task.add_history({"event": "submitted", "agent": agent_name})

        self._tasks[task_id] = task
        logger.info(f"📝 Task submitted: {task_id} -> {agent_name}")

        # Process async
        asyncio.create_task(self._process_task(task))

        return {
            "taskId": task_id,
            "state": task.state.value,
        }

    async def _process_task(self, task: Task):
        """异步处理任务"""
        try:
            task.state = TaskState.WORKING
            task.add_history({"event": "working"})

            handler = self._task_handlers.get(task.agent_name)
            if not handler:
                raise ValueError(f"No handler for agent: {task.agent_name}")

            # Execute handler
            result = await handler(task)

            # Complete
            task.state = TaskState.COMPLETED
            task.output_data = result
            task.add_history({"event": "completed", "result": result})

            logger.info(f"✅ Task completed: {task.id}")

        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            task.add_history({"event": "failed", "error": str(e)})
            logger.error(f"❌ Task failed: {task.id} - {e}")

    async def _handle_get_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取任务状态"""
        task_id = params.get("taskId")
        if not task_id:
            raise ValueError("taskId is required")

        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        return {
            "taskId": task.id,
            "state": task.state.value,
            "output": task.output_data,
            "error": task.error,
            "history": task.history,
        }

    async def _handle_cancel_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取消任务"""
        task_id = params.get("taskId")
        if not task_id:
            raise ValueError("taskId is required")

        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if task.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED]:
            return {"taskId": task_id, "canceled": False}

        task.state = TaskState.CANCELED
        task.add_history({"event": "canceled"})

        return {"taskId": task_id, "canceled": True}

    async def _handle_subscribe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """订阅任务事件"""
        task_id = params.get("taskId")
        if not task_id:
            raise ValueError("taskId is required")

        # Create event queue
        queue = asyncio.Queue()
        self._event_queues[task_id] = queue

        return {"taskId": task_id, "subscribed": True}

    async def _handle_list_agents(self) -> Dict[str, Any]:
        """列出所有 Agent"""
        if not self.card_registry:
            return {"agents": []}

        cards = self.card_registry.list_all()
        return {
            "agents": [card.to_dict() for card in cards]
        }

    async def _handle_get_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取单个 Agent"""
        name = params.get("name")
        if not self.card_registry:
            raise ValueError("Registry not configured")

        card = self.card_registry.get(name)
        if not card:
            raise ValueError(f"Agent not found: {name}")

        return card.to_dict()


class A2AClient:
    """A2A Client - 用于调用远程 Agent"""

    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.headers = {"Content-Type": "application/json"}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"

    async def send_task(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """提交任务"""
        import httpx

        request = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "agentName": agent_name,
                "input": input_data,
            },
            "id": task_id or str(uuid4()),
        }
        if task_id:
            request["params"]["taskId"] = task_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/a2a",
                json=request,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        import httpx

        request = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"taskId": task_id},
            "id": str(uuid4()),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/a2a",
                json=request,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """取消任务"""
        import httpx

        request = {
            "jsonrpc": "2.0",
            "method": "tasks/cancel",
            "params": {"taskId": task_id},
            "id": str(uuid4()),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/a2a",
                json=request,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_agents(self) -> List[Dict[str, Any]]:
        """列出可用 Agent"""
        import httpx

        request = {
            "jsonrpc": "2.0",
            "method": "agents/list",
            "params": {},
            "id": str(uuid4()),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/a2a",
                json=request,
                headers=self.headers,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("result", {}).get("agents", [])

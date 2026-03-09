"""
Agent Roles - 角色协作系统

实现 oh-my-openagent 风格的多 Agent 协作：
- Sisyphus: 编排者，协调其他 agents
- Hephaestus: 深度工作者，执行复杂任务
- Prometheus: 规划者，制定计划

参考:
- oh-my-openagent Ralph Roles
- AutoGPT Forge Multi-Agent
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class RoleType(str, Enum):
    """角色类型"""
    SISYPHUS = "sisyphus"      # 编排者
    HEPHAESTUS = "hephaestus"  # 深度工作者
    PROMETHEUS = "prometheus"  # 规划者


class AgentStatus(str, Enum):
    """Agent 状态"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RoleConfig:
    """角色配置"""
    role_type: RoleType
    name: str
    description: str
    capabilities: List[str]
    max_concurrent_tasks: int = 3
    timeout_seconds: float = 300.0
    retry_on_failure: bool = True
    max_retries: int = 3


@dataclass
class TaskAssignment:
    """任务分配"""
    task_id: str
    task_name: str
    assigned_to: str  # agent_id
    status: AgentStatus = AgentStatus.IDLE
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Any = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class AgentMetadata:
    """Agent 元数据"""
    agent_id: str
    role_type: RoleType
    name: str
    status: AgentStatus = AgentStatus.IDLE
    current_tasks: List[str] = field(default_factory=list)
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_execution_time: float = 0.0
    capabilities: List[str] = field(default_factory=list)
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())


class BaseRole:
    """角色基类"""

    def __init__(self, config: RoleConfig):
        self.config = config
        self.agent_id = f"{config.role_type.value}_{uuid.uuid4().hex[:8]}"
        self.metadata = AgentMetadata(
            agent_id=self.agent_id,
            role_type=config.role_type,
            name=config.name,
            capabilities=config.capabilities,
        )

    async def execute(self, task: TaskAssignment) -> Any:
        """执行任务

        Args:
            task: 任务分配

        Returns:
            Any: 任务结果
        """
        raise NotImplementedError

    async def can_handle(self, task: TaskAssignment) -> bool:
        """检查是否可以处理任务

        Args:
            task: 任务分配

        Returns:
            bool: 是否可以处理
        """
        # 检查并发限制
        if len(self.metadata.current_tasks) >= self.config.max_concurrent_tasks:
            return False
        return True


class PrometheusRole(BaseRole):
    """Prometheus - 规划者

    负责分析任务，制定计划，分解子任务
    """

    def __init__(self, config: Optional[RoleConfig] = None):
        if config is None:
            config = RoleConfig(
                role_type=RoleType.PROMETHEUS,
                name="Prometheus",
                description="规划者 - 分析任务，制定计划",
                capabilities=["task_analysis", "planning", "decomposition", "priority_ranking"],
                max_concurrent_tasks=5,
            )
        super().__init__(config)
        self.planning_model = "prometheus"

    async def execute(self, task: TaskAssignment) -> Dict[str, Any]:
        """执行规划任务

        Args:
            task: 任务分配

        Returns:
            Dict: 规划结果
        """
        logger.info(f"[Prometheus] Planning for task: {task.task_name}")

        # 分析任务
        analysis = await self._analyze_task(task)

        # 制定计划
        plan = await self._create_plan(task, analysis)

        # 分解子任务
        subtasks = await self._decompose(task, plan)

        return {
            "analysis": analysis,
            "plan": plan,
            "subtasks": subtasks,
            "priority": self._calculate_priority(task),
        }

    async def _analyze_task(self, task: TaskAssignment) -> Dict[str, Any]:
        """分析任务"""
        input_data = task.input_data
        message = input_data.get("message", "")

        # 简单分析
        analysis = {
            "task_type": self._classify_task(message),
            "complexity": self._estimate_complexity(message),
            "required_capabilities": self._extract_capabilities(message),
            "constraints": input_data.get("constraints", {}),
        }

        return analysis

    async def _create_plan(self, task: TaskAssignment, analysis: Dict) -> List[Dict]:
        """创建计划"""
        plan = []
        task_type = analysis.get("task_type", "general")
        complexity = analysis.get("complexity", "medium")

        # 根据任务类型生成步骤
        if task_type == "search":
            plan = [
                {"step": 1, "action": "search", "description": "搜索信息"},
                {"step": 2, "action": "process", "description": "处理结果"},
                {"step": 3, "action": "format", "description": "格式化输出"},
            ]
        elif task_type == "translation":
            plan = [
                {"step": 1, "action": "detect_language", "description": "检测语言"},
                {"step": 2, "action": "translate", "description": "翻译内容"},
                {"step": 3, "action": "verify", "description": "验证翻译"},
            ]
        elif task_type == "code":
            plan = [
                {"step": 1, "action": "understand_requirements", "description": "理解需求"},
                {"step": 2, "action": "generate_code", "description": "生成代码"},
                {"step": 3, "action": "validate", "description": "验证代码"},
            ]
        else:
            plan = [
                {"step": 1, "action": "analyze", "description": "分析请求"},
                {"step": 2, "action": "execute", "description": "执行任务"},
                {"step": 3, "action": "respond", "description": "返回结果"},
            ]

        return plan

    async def _decompose(self, task: TaskAssignment, plan: List[Dict]) -> List[Dict]:
        """分解子任务"""
        subtasks = []

        for step in plan:
            subtask = {
                "id": f"{task.task_id}_step_{step['step']}",
                "parent_id": task.task_id,
                "action": step["action"],
                "description": step["description"],
                "status": "pending",
                "depends_on": [],
            }

            # 设置依赖
            if step["step"] > 1:
                subtask["depends_on"] = [f"{task.task_id}_step_{step['step'] - 1}"]

            subtasks.append(subtask)

        return subtasks

    def _classify_task(self, message: str) -> str:
        """分类任务"""
        message_lower = message.lower()

        if any(kw in message_lower for kw in ["search", "搜索", "查找", "找"]):
            return "search"
        elif any(kw in message_lower for kw in ["translate", "翻译"]):
            return "translation"
        elif any(kw in message_lower for kw in ["code", "代码", "写", "开发"]):
            return "code"
        elif any(kw in message_lower for kw in ["analyze", "分析", "研究"]):
            return "analysis"
        else:
            return "general"

    def _estimate_complexity(self, message: str) -> str:
        """估计复杂度"""
        length = len(message)

        if length < 50:
            return "low"
        elif length < 200:
            return "medium"
        else:
            return "high"

    def _extract_capabilities(self, message: str) -> List[str]:
        """提取所需能力"""
        capabilities = []

        message_lower = message.lower()
        if "search" in message_lower or "搜索" in message_lower:
            capabilities.append("web_search")
        if "translate" in message_lower or "翻译" in message_lower:
            capabilities.append("translation")
        if "code" in message_lower or "代码" in message_lower:
            capabilities.append("code_generation")
        if "file" in message_lower or "文件" in message_lower:
            capabilities.append("file_operations")

        if not capabilities:
            capabilities.append("general_query")

        return capabilities

    def _calculate_priority(self, task: TaskAssignment) -> int:
        """计算优先级"""
        input_data = task.input_data
        base_priority = input_data.get("priority", 5)

        # 根据复杂度调整
        complexity = self._estimate_complexity(
            input_data.get("message", "")
        )
        if complexity == "high":
            base_priority -= 1
        elif complexity == "low":
            base_priority += 1

        return max(1, min(10, base_priority))


class HephaestusRole(BaseRole):
    """Hephaestus - 深度工作者

    负责执行复杂任务，处理详细工作
    """

    def __init__(self, config: Optional[RoleConfig] = None):
        if config is None:
            config = RoleConfig(
                role_type=RoleType.HEPHAESTUS,
                name="Hephaestus",
                description="深度工作者 - 执行复杂任务",
                capabilities=["deep_work", "detailed_processing", "quality_assurance", "error_recovery"],
                max_concurrent_tasks=2,
                timeout_seconds=600.0,
            )
        super().__init__(config)
        self.tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable):
        """注册工具

        Args:
            name: 工具名称
            func: 工具函数
        """
        self.tools[name] = func
        logger.debug(f"[Hephaestus] Registered tool: {name}")

    async def execute(self, task: TaskAssignment) -> Any:
        """执行深度工作

        Args:
            task: 任务分配

        Returns:
            Any: 执行结果
        """
        logger.info(f"[Hephaestus] Executing task: {task.task_name}")

        action = task.input_data.get("action", "execute")
        params = task.input_data.get("params", {})

        # 检查工具是否存在
        if action in self.tools:
            tool = self.tools[action]
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**params)
            else:
                result = tool(**params)
        else:
            # 默认执行
            result = await self._default_execute(task)

        return result

    async def _default_execute(self, task: TaskAssignment) -> Dict[str, Any]:
        """默认执行逻辑"""
        action = task.input_data.get("action", "execute")

        # 模拟执行
        await asyncio.sleep(0.1)

        return {
            "status": "completed",
            "action": action,
            "result": f"Executed {action}",
        }

    async def validate_output(self, output: Any) -> bool:
        """验证输出质量

        Args:
            output: 输出内容

        Returns:
            bool: 是否通过验证
        """
        if output is None:
            return False

        if isinstance(output, dict):
            if output.get("status") == "failed":
                return False

        return True


class SisyphusRole(BaseRole):
    """Sisyphus - 编排者

    负责协调其他 agents，管理任务流程
    """

    def __init__(self, config: Optional[RoleConfig] = None):
        if config is None:
            config = RoleConfig(
                role_type=RoleType.SISYPHUS,
                name="Sisyphus",
                description="编排者 - 协调 agents",
                capabilities=["orchestration", "coordination", "task_assignment", "result_aggregation"],
                max_concurrent_tasks=10,
            )
        super().__init__(config)

        # 子 agents
        self.prometheus: Optional[PrometheusRole] = None
        self.hephaestus_list: List[HephaestusRole] = []

        # 任务队列
        self.pending_tasks: asyncio.Queue = asyncio.Queue()
        self.task_results: Dict[str, Any] = {}

    def assign_planner(self, prometheus: PrometheusRole):
        """分配规划者

        Args:
            prometheus: Prometheus 实例
        """
        self.prometheus = prometheus
        logger.info("[Sisyphus] Assigned Prometheus as planner")

    def assign_worker(self, hephaestus: HephaestusRole):
        """分配工作者

        Args:
            hephaestus: Hephaestus 实例
        """
        self.hephaestus_list.append(hephaestus)
        logger.info(f"[Sisyphus] Assigned Hephaestus as worker (total: {len(self.hephaestus_list)})")

    async def execute(self, task: TaskAssignment) -> Any:
        """执行编排任务

        Args:
            task: 任务分配

        Returns:
            Any: 编排结果
        """
        logger.info(f"[Sisyphus] Orchestrating task: {task.task_name}")

        # 1. 让 Prometheus 规划
        if not self.prometheus:
            raise ValueError("No Prometheus assigned")

        planning_task = TaskAssignment(
            task_id=f"{task.task_id}_planning",
            task_name=f"Plan for {task.task_name}",
            input_data=task.input_data,
        )

        plan_result = await self.prometheus.execute(planning_task)

        # 2. 分配子任务给 Hephaestus
        subtasks = plan_result.get("subtasks", [])
        task_futures = []

        for subtask in subtasks:
            # 找空闲的 worker
            worker = self._get_available_worker()
            if worker:
                subtask_assignment = TaskAssignment(
                    task_id=subtask["id"],
                    task_name=subtask["description"],
                    input_data={
                        "action": subtask["action"],
                        "params": subtask,
                        "parent_id": task.task_id,
                    },
                )
                task_futures.append(self._execute_subtask(worker, subtask_assignment))

        # 3. 并行执行子任务
        if task_futures:
            results = await asyncio.gather(*task_futures, return_exceptions=True)
        else:
            results = []

        # 4. 聚合结果
        aggregated = await self._aggregate_results(task, plan_result, results)

        return aggregated

    async def _execute_subtask(self, worker: HephaestusRole, task: TaskAssignment) -> Any:
        """执行子任务

        Args:
            worker:工作者
            task: 子任务

        Returns:
            Any: 执行结果
        """
        try:
            worker.metadata.current_tasks.append(task.task_id)
            task.status = AgentStatus.RUNNING
            task.started_at = datetime.now().isoformat()

            result = await worker.execute(task)

            task.status = AgentStatus.COMPLETED
            task.output_data = result
            task.completed_at = datetime.now().isoformat()

            worker.metadata.current_tasks.remove(task.task_id)
            worker.metadata.completed_tasks += 1

            return result

        except Exception as e:
            task.status = AgentStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()

            if task.task_id in worker.metadata.current_tasks:
                worker.metadata.current_tasks.remove(task.task_id)
            worker.metadata.failed_tasks += 1

            logger.error(f"[Sisyphus] Subtask {task.task_id} failed: {e}")
            return {"error": str(e)}

    def _get_available_worker(self) -> Optional[HephaestusRole]:
        """获取可用的工作者

        Returns:
            Optional[HephaestusRole]: 可用的 worker
        """
        for worker in self.hephaestus_list:
            if len(worker.metadata.current_tasks) < worker.config.max_concurrent_tasks:
                return worker

        # 如果没有完全空闲的，返回负载最低的
        if self.hephaestus_list:
            return min(
                self.hephaestus_list,
                key=lambda w: len(w.metadata.current_tasks)
            )

        return None

    async def _aggregate_results(
        self,
        task: TaskAssignment,
        plan_result: Dict,
        subtask_results: List[Any]
    ) -> Dict[str, Any]:
        """聚合结果

        Args:
            task: 主任务
            plan_result: 计划结果
            subtask_results: 子任务结果

        Returns:
            Dict: 聚合后的结果
        """
        successful_results = [r for r in subtask_results if not isinstance(r, Exception)]
        failed_results = [r for r in subtask_results if isinstance(r, Exception)]

        return {
            "task_id": task.task_id,
            "status": "completed" if not failed_results else "partial",
            "plan": plan_result.get("plan", []),
            "subtask_count": len(subtask_results),
            "successful": len(successful_results),
            "failed": len(failed_results),
            "results": successful_results,
            "errors": [str(e) for e in failed_results],
        }


class AgentCollaborationSystem:
    """Agent 协作系统

    统一管理多角色协作
    """

    def __init__(self):
        # 创建默认角色
        self.prometheus = PrometheusRole()
        self.sisyphus = SisyphusRole()
        self.hephaestus = HephaestusRole()

        # 建立连接
        self.sisyphus.assign_planner(self.prometheus)
        self.sisyphus.assign_worker(self.hephaestus)

        # 注册到系统
        self.agents: Dict[str, BaseRole] = {
            self.prometheus.agent_id: self.prometheus,
            self.sisyphus.agent_id: self.sisyphus,
            self.hephaestus.agent_id: self.hephaestus,
        }

        logger.info("AgentCollaborationSystem initialized")

    async def execute_task(
        self,
        message: str,
        session_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行任务

        Args:
            message: 用户消息
            session_id: 会话 ID
            user_id: 用户 ID
            context: 上下文

        Returns:
            Dict: 执行结果
        """
        # 创建主任务
        task = TaskAssignment(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            task_name="Main Task",
            input_data={
                "message": message,
                "session_id": session_id,
                "user_id": user_id,
                "context": context or {},
            },
        )

        # 通过 Sisyphus 编排执行
        result = await self.sisyphus.execute(task)

        return result

    def get_status(self) -> Dict[str, Any]:
        """获取系统状态

        Returns:
            Dict: 状态信息
        """
        return {
            "agents": {
                agent_id: {
                    "role": agent.metadata.role_type.value,
                    "name": agent.metadata.name,
                    "status": agent.metadata.status.value,
                    "completed_tasks": agent.metadata.completed_tasks,
                    "failed_tasks": agent.metadata.failed_tasks,
                }
                for agent_id, agent in self.agents.items()
            },
            "total_agents": len(self.agents),
        }


# ==================== 便捷函数 ====================


def create_collaboration_system() -> AgentCollaborationSystem:
    """创建协作系统

    Returns:
        AgentCollaborationSystem: 协作系统实例
    """
    return AgentCollaborationSystem()


# ==================== 测试 ====================

if __name__ == "__main__":
    async def test():
        # 创建系统
        system = create_collaboration_system()

        # 执行任务
        result = await system.execute_task(
            message="搜索最新的 AI 新闻",
            session_id="test_session",
            user_id="test_user",
        )

        print(f"Result: {result}")

        # 状态
        status = system.get_status()
        print(f"Status: {status}")

    asyncio.run(test())

"""
Agent Loop - 标准化 Agent 循环

实现 oh-my-openagent Ralph Loop 风格的标准化 Agent 循环：
- THINK: 推理分析，分解任务步骤
- ACT: 执行工具或 LLM 调用
- OBSERVE: 获取结果
- REFLECT: 评估是否完成，循环

参考:
- oh-my-openagent Ralph Loop
- AutoGPT Forge Agent Loop
- LangGraph 状态机
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class LoopState(str, Enum):
    """循环状态"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class StepStatus(str, Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class LoopStep:
    """循环步骤"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""  # THINK/ACT/OBSERVE/REFLECT
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Any = None
    status: StepStatus = StepStatus.PENDING
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopResult:
    """循环结果"""
    success: bool
    final_output: Any = None
    steps: List[LoopStep] = field(default_factory=list)
    total_steps: int = 0
    completed_steps: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Agent 上下文"""
    session_id: str
    user_id: str
    original_message: str
    current_plan: List[str] = field(default_factory=list)
    executed_steps: List[LoopStep] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentLoop:
    """标准化 Agent 循环

    实现 Ralph Loop 风格的 4 步循环：
    1. THINK: 分析任务，分解步骤，制定计划
    2. ACT: 执行工具或 LLM 调用
    3. OBSERVE: 获取工具返回结果
    4. REFLECT: 评估是否完成，决定下一步

    特点：
    - 每步都可被 checkpoint
    - 支持最大循环次数
    - 支持超时控制
    - 可观测性强
    """

    def __init__(
        self,
        max_iterations: int = 10,
        timeout_seconds: float = 300.0,
        checkpoint_enabled: bool = True,
    ):
        """初始化 Agent 循环

        Args:
            max_iterations: 最大迭代次数
            timeout_seconds: 超时时间（秒）
            checkpoint_enabled: 是否启用检查点
        """
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds
        self.checkpoint_enabled = checkpoint_enabled

        # 状态
        self.state = LoopState.IDLE
        self.context: Optional[AgentContext] = None
        self.steps: List[LoopStep] = []

        # 回调
        self.think_handler: Optional[Callable] = None
        self.act_handler: Optional[Callable] = None
        self.observe_handler: Optional[Callable] = None
        self.reflect_handler: Optional[Callable] = None

        # Checkpoint 管理器（可选注入）
        self.checkpoint_manager = None

        logger.info(f"AgentLoop initialized (max_iterations={max_iterations}, timeout={timeout_seconds}s)")

    def set_handlers(
        self,
        think: Callable,
        act: Callable,
        observe: Callable,
        reflect: Callable,
    ):
        """设置循环处理器

        Args:
            think: THINK 阶段处理器
            act: ACT 阶段处理器
            observe: OBSERVE 阶段处理器
            reflect: REFLECT 阶段处理器
        """
        self.think_handler = think
        self.act_handler = act
        self.observe_handler = observe
        self.reflect_handler = reflect
        logger.debug("AgentLoop handlers registered")

    def set_checkpoint_manager(self, manager):
        """设置检查点管理器

        Args:
            manager: CheckpointManager 实例
        """
        self.checkpoint_manager = manager

    async def run(
        self,
        message: str,
        session_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> LoopResult:
        """运行 Agent 循环

        Args:
            message: 用户消息
            session_id: 会话 ID
            user_id: 用户 ID
            context: 初始上下文

        Returns:
            LoopResult: 循环结果
        """
        # 初始化上下文
        self.context = AgentContext(
            session_id=session_id,
            user_id=user_id,
            original_message=message,
            metadata=context or {}
        )

        self.state = LoopState.THINKING
        self.steps = []

        logger.info(f"🚀 Starting AgentLoop for session {session_id}")

        iteration = 0
        start_time = asyncio.get_event_loop().time()

        while iteration < self.max_iterations:
            # 检查超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.timeout_seconds:
                logger.warning(f"AgentLoop timeout after {elapsed:.1f}s")
                return LoopResult(
                    success=False,
                    error=f"Timeout after {elapsed:.1f}s",
                    steps=self.steps,
                    total_steps=self.max_iterations,
                    completed_steps=iteration,
                )

            iteration += 1
            logger.debug(f"🔄 Iteration {iteration}/{self.max_iterations}")

            try:
                # 1. THINK
                self.state = LoopState.THINKING
                think_step = await self._execute_step("THINK", self._do_think)
                self.steps.append(think_step)

                # 检查是否需要停止
                if think_step.metadata.get("should_stop"):
                    break

                # 2. ACT
                self.state = LoopState.ACTING
                act_step = await self._execute_step("ACT", self._do_act)
                self.steps.append(act_step)

                if act_step.status == StepStatus.FAILED:
                    break

                # 3. OBSERVE
                self.state = LoopState.OBSERVING
                observe_step = await self._execute_step("OBSERVE", self._do_observe)
                self.steps.append(observe_step)

                # 4. REFLECT
                self.state = LoopState.REFLECTING
                reflect_step = await self._execute_step("REFLECT", self._do_reflect)
                self.steps.append(reflect_step)

                # 检查是否完成
                if reflect_step.metadata.get("is_completed"):
                    self.state = LoopState.COMPLETED
                    logger.info(f"✅ AgentLoop completed in {iteration} iterations")
                    return LoopResult(
                        success=True,
                        final_output=reflect_step.output_data,
                        steps=self.steps,
                        total_steps=self.max_iterations,
                        completed_steps=iteration,
                    )

                # 保存检查点
                if self.checkpoint_enabled and self.checkpoint_manager:
                    await self.checkpoint_manager.save(self.context, self.steps)

            except Exception as e:
                logger.error(f"AgentLoop error at iteration {iteration}: {e}")
                self.state = LoopState.FAILED
                return LoopResult(
                    success=False,
                    error=str(e),
                    steps=self.steps,
                    total_steps=self.max_iterations,
                    completed_steps=iteration,
                )

        # 达到最大迭代次数
        self.state = LoopState.PAUSED
        logger.warning(f"AgentLoop reached max iterations ({self.max_iterations})")
        return LoopResult(
            success=False,
            error=f"Max iterations ({self.max_iterations}) reached",
            steps=self.steps,
            total_steps=self.max_iterations,
            completed_steps=iteration,
        )

    async def _execute_step(self, name: str, handler: Callable) -> LoopStep:
        """执行单个步骤

        Args:
            name: 步骤名称
            handler: 处理器

        Returns:
            LoopStep: 步骤结果
        """
        step = LoopStep(
            name=name,
            started_at=datetime.now(),
            status=StepStatus.RUNNING,
        )

        try:
            # 调用处理器
            if asyncio.iscoroutinefunction(handler):
                result = await handler()
            else:
                result = handler()

            step.output_data = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now()

        except Exception as e:
            step.error = str(e)
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now()
            logger.error(f"Step {name} failed: {e}")

        return step

    # ==================== 步骤实现 ====================

    async def _do_think(self) -> Dict[str, Any]:
        """THINK: 分析任务，分解步骤"""
        if self.think_handler:
            return await self.think_handler(self.context)

        # 默认实现：简单解析
        message = self.context.original_message

        # 提取任务步骤
        plan = []
        if "search" in message.lower() or "搜索" in message:
            plan.append("search_web")
        if "translate" in message.lower() or "翻译" in message:
            plan.append("translate")
        if "write" in message.lower() or "写" in message:
            plan.append("write")

        if not plan:
            plan = ["general_query"]

        self.context.current_plan = plan

        return {
            "plan": plan,
            "analysis": f"Task: {message}",
            "should_stop": False,
        }

    async def _do_act(self) -> Dict[str, Any]:
        """ACT: 执行工具或 LLM"""
        if self.act_handler:
            return await self.act_handler(self.context)

        # 默认实现：返回待执行的动作
        current_action = self.context.current_plan[len(self.context.executed_steps)] if self.context.current_plan else "noop"

        return {
            "action": current_action,
            "pending": True,
        }

    async def _do_observe(self) -> Dict[str, Any]:
        """OBSERVE: 获取结果"""
        if self.observe_handler:
            return await self.observe_handler(self.context)

        # 默认实现
        return {
            "observation": "No observation handler",
        }

    async def _do_reflect(self) -> Dict[str, Any]:
        """REFLECT: 评估是否完成"""
        if self.reflect_handler:
            return await self.reflect_handler(self.context)

        # 默认实现：检查是否还有未完成步骤
        plan = self.context.current_plan
        executed = len(self.context.executed_steps)

        is_completed = executed >= len(plan) if plan else True

        return {
            "is_completed": is_completed,
            "remaining_steps": len(plan) - executed if plan else 0,
            "should_stop": is_completed,
        }

    # ==================== 控制方法 ====================

    async def pause(self):
        """暂停循环"""
        self.state = LoopState.PAUSED
        logger.info("AgentLoop paused")

    async def resume(self):
        """恢复循环"""
        if self.state == LoopState.PAUSED:
            self.state = LoopState.THINKING
            logger.info("AgentLoop resumed")

    async def stop(self):
        """停止循环"""
        self.state = LoopState.IDLE
        logger.info("AgentLoop stopped")

    def get_status(self) -> Dict[str, Any]:
        """获取状态

        Returns:
            Dict: 状态信息
        """
        return {
            "state": self.state.value,
            "iteration": len(self.steps) // 4 + 1,
            "max_iterations": self.max_iterations,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status.value,
                    "error": s.error,
                }
                for s in self.steps[-4:]  # 最近4步
            ],
        }


# ==================== 便捷函数 ====================

def create_loop(
    max_iterations: int = 10,
    timeout_seconds: float = 300.0,
) -> AgentLoop:
    """创建 Agent 循环

    Args:
        max_iterations: 最大迭代次数
        timeout_seconds: 超时时间

    Returns:
        AgentLoop: Agent 循环实例
    """
    return AgentLoop(
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
    )


# ==================== 测试 ====================

if __name__ == "__main__":
    async def test():
        # 创建循环
        loop = AgentLoop(max_iterations=5, timeout_seconds=60.0)

        # 自定义处理器
        async def custom_think(ctx):
            return {"plan": ["step1", "step2"], "should_stop": False}

        async def custom_act(ctx):
            return {"action": "doing_something", "result": "done"}

        async def custom_observe(ctx):
            return {"observation": "action completed"}

        async def custom_reflect(ctx):
            return {"is_completed": True, "should_stop": True}

        loop.set_handlers(
            think=custom_think,
            act=custom_act,
            observe=custom_observe,
            reflect=custom_reflect,
        )

        # 运行
        result = await loop.run(
            message="Test task",
            session_id="test_session",
            user_id="test_user",
        )

        print(f"Success: {result.success}")
        print(f"Iterations: {result.completed_steps}")
        print(f"Steps: {len(result.steps)}")

    asyncio.run(test())

# coding=utf-8
"""
Unified Message Handler - 统一消息处理器

整合菜单事件和消息事件的统一入口:
1. 菜单事件处理 (FeishuMenuHandler)
2. 消息事件处理 (KeywordRouter + AIRouter)
3. 任务执行 (IntelligencePipeline)

设计目标:
- 统一入口: 菜单点击和消息发送使用相同处理逻辑
- 降级处理: 各组件失败时优雅降级
- 完整流程: 从触发到推送的完整闭环
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from src.router.menu_handler import FeishuMenuHandler, IntentResult
from src.router.keyword_router import KeywordRouter
from src.router.ai_router import AIRouter
from src.intelligence.pipeline import IntelligencePipeline, PipelineConfig


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    message: str
    data: Any = None
    execution_time: float = 0.0
    steps: List[Dict[str, Any]] = field(default_factory=list)


class UnifiedMessageHandler:
    """统一消息处理器

    整合菜单事件和消息事件的统一入口

    处理流程:
    1. 事件接收 (menu/message)
    2. 意图识别 (menu/keyword/AI)
    3. 任务执行 (intelligence/search/system)
    4. 响应格式化
    """

    def __init__(self):
        """初始化统一消息处理器"""
        # 组件初始化
        self.menu_handler = FeishuMenuHandler()
        self.keyword_router = KeywordRouter()
        self.ai_router = AIRouter()

        # 初始化关键词路由规则
        self._init_keyword_rules()

        # 统计信息
        self.stats = {
            "menu_events": 0,
            "message_events": 0,
            "total_requests": 0,
            "success_count": 0,
            "failure_count": 0,
        }

    def _init_keyword_rules(self):
        """初始化关键词路由规则"""
        # 情报相关
        self.keyword_router.add_rule(
            ["热点新闻", "今日新闻", "最新新闻", "热门新闻"],
            "intelligence",
            "view_hot_news"
        )
        self.keyword_router.add_rule(
            ["科技", "技术", "AI", "人工智能", "大模型"],
            "intelligence",
            "view_category_news"
        )
        self.keyword_router.add_rule(
            ["投资", "融资", "并购", "商业"],
            "intelligence",
            "view_category_news"
        )
        self.keyword_router.add_rule(
            ["报告", "行业报告", "分析报告"],
            "intelligence",
            "view_category_news"
        )

        # 搜索相关
        self.keyword_router.add_rule(
            ["搜索", "查找", "查一下", "帮我找"],
            "search",
            "search_intelligence"
        )

        # 设置相关
        self.keyword_router.add_rule(
            ["设置", "配置", "偏好"],
            "system",
            "get_settings"
        )

        # 设置默认agent
        self.keyword_router.set_default("llm")

    async def handle(self, event: Dict[str, Any]) -> ExecutionResult:
        """统一处理入口

        Args:
            event: 事件字典，支持以下类型:
                - menu: 菜单点击事件
                - message: 消息事件
                - text: 文本消息 (简化格式)

        Returns:
            ExecutionResult: 执行结果
        """
        start_time = time.time()
        result = ExecutionResult(
            success=False,
            message="",
            steps=[]
        )

        try:
            self.stats["total_requests"] += 1

            # 1. 事件类型判断
            event_type = self._get_event_type(event)
            logger.info(f"收到事件类型: {event_type}")

            # 2. 根据类型处理
            if event_type == "menu":
                result = await self._handle_menu(event)
                self.stats["menu_events"] += 1
            elif event_type == "message":
                result = await self._handle_message(event)
                self.stats["message_events"] += 1
            elif event_type == "text":
                result = await self._handle_text(event)
            else:
                result.message = f"未知事件类型: {event_type}"
                result.steps.append({
                    "step": "event_parse",
                    "status": "error",
                    "message": result.message
                })

            # 3. 统计
            if result.success:
                self.stats["success_count"] += 1
            else:
                self.stats["failure_count"] += 1

        except Exception as e:
            logger.error(f"处理事件失败: {e}")
            result.message = f"处理失败: {str(e)}"
            result.steps.append({
                "step": "handle",
                "status": "error",
                "message": str(e)
            })

        result.execution_time = time.time() - start_time
        return result

    def _get_event_type(self, event: Dict[str, Any]) -> str:
        """判断事件类型"""
        if isinstance(event, str):
            return "text"

        event_data = event.get("event", {})

        # 菜单事件
        if event_data.get("type") == "im.menu":
            return "menu"

        # 消息事件
        if event_data.get("type") == "im.message":
            return "message"

        # 默认尝试作为文本处理
        if "message" in event or "text" in event:
            return "text"

        return "unknown"

    async def _handle_menu(self, event: Dict[str, Any]) -> ExecutionResult:
        """处理菜单事件"""
        result = ExecutionResult(success=False, message="")
        result.steps.append({
            "step": "menu_parse",
            "status": "start",
            "message": "开始解析菜单事件"
        })

        try:
            # 1. 解析菜单事件
            intent_result = await self.menu_handler.handle_menu_event(event)

            if not intent_result:
                result.message = "无法解析菜单事件"
                result.steps.append({
                    "step": "menu_parse",
                    "status": "error",
                    "message": result.message
                })
                return result

            result.steps.append({
                "step": "intent_recognition",
                "status": "success",
                "source": "menu",
                "confidence": intent_result.confidence,
                "intent": intent_result.intent,
                "agent": intent_result.agent
            })

            # 2. 执行任务
            result = await self._execute_intent(intent_result)

        except Exception as e:
            logger.error(f"处理菜单事件失败: {e}")
            result.message = f"处理失败: {str(e)}"

        return result

    async def _handle_message(self, event: Dict[str, Any]) -> ExecutionResult:
        """处理消息事件"""
        result = ExecutionResult(success=False, message="")
        result.steps.append({
            "step": "message_parse",
            "status": "start",
            "message": "开始解析消息事件"
        })

        try:
            # 1. 提取消息内容
            message_content = self._extract_message_content(event)
            user_id = self._extract_user_id(event)

            if not message_content:
                result.message = "无法提取消息内容"
                result.steps.append({
                    "step": "message_parse",
                    "status": "error",
                    "message": result.message
                })
                return result

            result.steps.append({
                "step": "message_parse",
                "status": "success",
                "content": message_content[:50]
            })

            # 2. 意图识别
            intent_result = await self._recognize_intent(message_content, user_id)

            result.steps.append({
                "step": "intent_recognition",
                "status": "success",
                "source": intent_result.source,
                "confidence": intent_result.confidence,
                "intent": intent_result.intent,
                "agent": intent_result.agent
            })

            # 3. 执行任务
            result = await self._execute_intent(intent_result)

        except Exception as e:
            logger.error(f"处理消息事件失败: {e}")
            result.message = f"处理失败: {str(e)}"

        return result

    async def _handle_text(self, event: Dict[str, Any]) -> ExecutionResult:
        """处理文本事件 (简化格式)"""
        text = event.get("message", event.get("text", ""))
        user_id = event.get("user_id", "unknown")

        return await self._handle_message({
            "event": {
                "message": {
                    "body": {
                        "content": text
                    },
                    "from": {
                        "user_id": user_id
                    }
                }
            }
        })

    async def _recognize_intent(self, message: str, user_id: str) -> IntentResult:
        """意图识别

        优先级:
        1. Keyword路由 (高置信度)
        2. AI路由 (低置信度)
        3. 默认 (LLM)
        """
        # 1. 关键词路由
        keyword_result = self.keyword_router.route(message)

        if keyword_result:
            confidence = 0.9  # 关键词匹配高置信度
            if keyword_result.get("action"):
                intent = keyword_result["action"]
            else:
                intent = f"handle_{keyword_result['agent']}"

            return IntentResult(
                intent=intent,
                agent=keyword_result["agent"],
                params={},
                confidence=confidence,
                source="keyword",
                user_id=user_id,
                message=message
            )

        # 2. AI路由
        try:
            ai_result = await self.ai_router.route(message)

            if ai_result and ai_result.get("agent"):
                return IntentResult(
                    intent=ai_result.get("action", f"handle_{ai_result['agent']}"),
                    agent=ai_result["agent"],
                    params={},
                    confidence=0.7,
                    source="ai",
                    user_id=user_id,
                    message=message
                )
        except Exception as e:
            logger.warning(f"AI路由失败: {e}")

        # 3. 默认
        return IntentResult(
            intent="handle_llm",
            agent="llm",
            params={},
            confidence=0.5,
            source="default",
            user_id=user_id,
            message=message
        )

    async def _execute_intent(self, intent_result: IntentResult) -> ExecutionResult:
        """执行意图"""
        result = ExecutionResult(success=False, message="")

        try:
            # 根据agent执行不同任务
            if intent_result.agent == "intelligence":
                result = await self._execute_intelligence(intent_result)
            elif intent_result.agent == "search":
                result = await self._execute_search(intent_result)
            elif intent_result.agent == "system":
                result = await self._execute_system(intent_result)
            elif intent_result.agent == "llm":
                result = await self._execute_llm(intent_result)
            else:
                result.message = f"未知Agent: {intent_result.agent}"

        except Exception as e:
            logger.error(f"执行意图失败: {e}")
            result.message = f"执行失败: {str(e)}"

        return result

    async def _execute_intelligence(self, intent_result: IntentResult) -> ExecutionResult:
        """执行情报任务"""
        result = ExecutionResult(success=False, message="")

        # 确定分类
        category = intent_result.params.get("category", "hot")
        if intent_result.intent == "view_hot_news":
            category = "hot"

        result.steps.append({
            "step": "task_execution",
            "status": "start",
            "agent": "intelligence",
            "category": category
        })

        try:
            # 创建流水线配置
            config = PipelineConfig(
                rss_categories=[category],
                rss_lang="zh" if category in ["hot", "investment"] else "en",
                rss_max_tier=2,
            )

            # 执行流水线
            pipeline = IntelligencePipeline(config)
            pipeline_result = await pipeline.process(user_id=intent_result.user_id)

            # 格式化结果
            if pipeline_result.get("status") == "success":
                result.success = True
                result.data = pipeline_result

                # 生成摘要
                fetched = pipeline_result.get("fetched", 0)
                result.message = f"✅ 情报获取成功! 共获取 {fetched} 条情报"

                result.steps.append({
                    "step": "task_execution",
                    "status": "success",
                    "fetched": fetched
                })
            else:
                result.message = pipeline_result.get("message", "情报获取失败")

                result.steps.append({
                    "step": "task_execution",
                    "status": "warning",
                    "message": result.message
                })

        except Exception as e:
            logger.error(f"执行情报任务失败: {e}")
            result.message = f"情报获取失败: {str(e)}"

            result.steps.append({
                "step": "task_execution",
                "status": "error",
                "message": str(e)
            })

        return result

    async def _execute_search(self, intent_result: IntentResult) -> ExecutionResult:
        """执行搜索任务"""
        result = ExecutionResult(success=False, message="")

        result.steps.append({
            "step": "task_execution",
            "status": "start",
            "agent": "search"
        })

        # TODO: 实现搜索功能
        result.message = "🔍 搜索功能开发中..."

        result.steps.append({
            "step": "task_execution",
            "status": "success"
        })

        return result

    async def _execute_system(self, intent_result: IntentResult) -> ExecutionResult:
        """执行系统任务"""
        result = ExecutionResult(success=False, message="")

        result.steps.append({
            "step": "task_execution",
            "status": "start",
            "agent": "system",
            "intent": intent_result.intent
        })

        if intent_result.intent == "get_settings":
            result.message = "⚙️ 当前配置:\n- 推送频率: 每日\n- 语言: 中文"
        elif intent_result.intent == "clear_history":
            result.message = "🗑️ 会话历史已清除"
        else:
            result.message = f"⚙️ 执行操作: {intent_result.intent}"

        result.success = True

        result.steps.append({
            "step": "task_execution",
            "status": "success"
        })

        return result

    async def _execute_llm(self, intent_result: IntentResult) -> ExecutionResult:
        """执行LLM任务"""
        result = ExecutionResult(success=False, message="")

        result.steps.append({
            "step": "task_execution",
            "status": "start",
            "agent": "llm"
        })

        # TODO: 实现LLM功能
        result.message = f"💬 {intent_result.message}\n\n(LLM回复开发中...)"

        result.success = True

        result.steps.append({
            "step": "task_execution",
            "status": "success"
        })

        return result

    def _extract_message_content(self, event: Dict) -> Optional[str]:
        """提取消息内容"""
        try:
            message = event.get("event", {}).get("message", {})
            body = message.get("body", {})
            return body.get("content", "")
        except:
            return None

    def _extract_user_id(self, event: Dict) -> str:
        """提取用户ID"""
        try:
            message = event.get("event", {}).get("message", {})
            sender = message.get("sender", {})
            return sender.get("user_id", "unknown")
        except:
            return "unknown"

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()


# 全局实例
_handler: Optional[UnifiedMessageHandler] = None


def get_unified_handler() -> UnifiedMessageHandler:
    """获取全局统一消息处理器"""
    global _handler
    if _handler is None:
        _handler = UnifiedMessageHandler()
    return _handler

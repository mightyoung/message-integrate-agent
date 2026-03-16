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
import re
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
        # 学术论文相关 - 新增
        self.keyword_router.add_rule(
            ["论文", "arXiv", "arxiv", "学术", "研究"],
            "intelligence",
            "view_category_news"
        )
        # HuggingFace 相关 - 新增
        self.keyword_router.add_rule(
            ["huggingface", "hf", "Hugging Face", "模型", "GPT", "LLaMA", "transformer"],
            "intelligence",
            "view_category_news"
        )

        # 论文深度分析 - 新增更多触发关键词
        self.keyword_router.add_rule(
            ["深入解析", "深度分析", "详细分析", "解读论文", "分析论文", "解析论文", "细致解析", "解析"],
            "paper_deep_analysis",
            "analyze_paper"
        )

        # 舆情分析 - 通过ID分析指定情报
        self.keyword_router.add_rule(
            ["id=", "分析 ", "情感分析"],
            "sentiment_analysis",
            "analyze_by_id"
        )

        # 预测分析 - 通过URL或内容进行预测
        self.keyword_router.add_rule(
            ["预测", "推演", "未来趋势", "预测分析"],
            "prediction",
            "analyze_prediction"
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
            elif intent_result.agent == "paper_deep_analysis":
                result = await self._execute_paper_deep_analysis(intent_result)
            elif intent_result.agent == "sentiment_analysis":
                result = await self._execute_sentiment_analysis(intent_result)
            elif intent_result.agent == "prediction":
                result = await self._execute_prediction(intent_result)
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

    async def _execute_paper_deep_analysis(self, intent_result: IntentResult) -> ExecutionResult:
        """执行论文深度分析任务"""
        import asyncio

        result = ExecutionResult(success=False, message="")

        try:
            # 提取论文查询关键词或URL
            message = intent_result.message
            trigger_words = ["深入解析", "深度分析", "详细分析", "解读论文", "分析论文", "解析论文", "细致解析", "解析"]
            for word in trigger_words:
                message = message.replace(word, "").strip()

            # 提取URL
            query = message
            query_type = "keyword"
            url_match = re.search(r"https?://[^\s]+", message)
            if url_match:
                query = url_match.group(0)
                # 自动识别URL类型
                if "arxiv.org" in query:
                    query_type = "arxiv_url"
                elif "huggingface.co" in query:
                    query_type = "huggingface_url"
                else:
                    query_type = "generic_url"

            if not query:
                result.message = "请提供要分析的论文标题或关键词"
                return result

            # 立即返回反馈
            result.success = True
            display_query = query if len(query) <= 50 else query[:50] + "..."
            result.message = f"✅ 已收到，正在深度分析「{display_query}」，请稍候..."

            # 异步执行深度分析
            asyncio.create_task(self._run_paper_deep_analysis(query, query_type, intent_result.user_id))

        except Exception as e:
            logger.error(f"论文深度分析失败: {e}")
            result.message = f"处理失败: {str(e)}"

        return result

    async def _run_paper_deep_analysis(self, query: str, query_type: str, user_id: str):
        """后台运行论文深度分析"""
        try:
            from src.intelligence.paper_deep_analyzer import PaperDeepAnalyzer

            # 创建分析器并执行
            analyzer = PaperDeepAnalyzer()
            analysis_result = await analyzer.analyze(query, query_type=query_type)

            # 发送结果给用户
            if analysis_result.success and analysis_result.analysis:
                message = f"📄 论文深度分析完成：{analysis_result.paper.title}\n\n{analysis_result.analysis}"

                # 发送到飞书
                from src.adapters.feishu_adapter import FeishuAdapter
                feishu = FeishuAdapter()
                await feishu.send_message(
                    chat_id=user_id,
                    content=message,
                    chat_type="direct"
                )
            else:
                error_msg = analysis_result.error or "分析失败"
                from src.adapters.feishu_adapter import FeishuAdapter
                feishu = FeishuAdapter()
                await feishu.send_message(
                    chat_id=user_id,
                    content=f"❌ 论文分析失败: {error_msg}",
                    chat_type="direct"
                )

        except Exception as e:
            logger.error(f"后台论文分析失败: {e}")

    async def _execute_sentiment_analysis(self, intent_result: IntentResult) -> ExecutionResult:
        """执行情报舆情分析任务 - 通过ID分析指定情报"""
        import asyncio

        result = ExecutionResult(success=False, message="")

        try:
            # 从消息中提取ID
            message = intent_result.message

            # 解析 id=xxxx 格式 (支持 int_xxxxxx 或纯数字 xxxxxx)
            # 用户可能输入: "分析 id=123456" 或 "分析 int_123456"
            id_match = re.search(r"id[=：:]?\s*(?:int_)?(\d+)", message, re.IGNORECASE)
            if not id_match:
                result.message = "请提供要分析的情报ID，格式如：分析 id=123456 或 分析 int_123456"
                return result

            info_id = id_match.group(1)
            logger.info(f"开始舆情分析，info_id={info_id}")

            # 立即返回反馈
            result.success = True
            result.message = f"✅ 已收到，正在对情报 #{info_id} 进行舆情分析，请稍候..."

            # 异步执行分析
            asyncio.create_task(self._run_sentiment_analysis(info_id, intent_result.user_id))

        except Exception as e:
            logger.error(f"舆情分析失败: {e}")
            result.message = f"处理失败: {str(e)}"

        return result

    async def _run_sentiment_analysis(self, info_id: str, user_id: str):
        """后台运行舆情分析"""
        try:
            from src.storage import get_storage_manager

            # 获取存储管理器
            storage = get_storage_manager()

            if not storage or not storage.postgres:
                await self._send_error_to_user(user_id, "存储服务不可用")
                return

            # 获取情报记录
            news = storage.postgres.get_by_info_id(info_id)
            if not news:
                await self._send_error_to_user(user_id, f"未找到ID为 {info_id} 的情报")
                return

            # 执行情感分析（使用LLM）
            sentiment_result = await self._analyze_sentiment_llm(news)

            # 生成报告
            report = self._generate_sentiment_report(news, sentiment_result)

            # 发送结果给用户
            from src.adapters.feishu_adapter import FeishuAdapter
            feishu = FeishuAdapter()
            await feishu.send_message(
                chat_id=user_id,
                content=report,
                chat_type="direct"
            )

        except Exception as e:
            logger.error(f"后台舆情分析失败: {e}")
            await self._send_error_to_user(user_id, f"分析失败: {str(e)}")

    async def _analyze_sentiment_llm(self, news: Dict) -> Dict:
        """使用LLM进行情感分析"""
        try:
            from src.mcp.tools.llm import chat_with_llm
            from src.prompts import get_prompt

            content = news.get("content", "") or news.get("summary", "")
            if not content:
                return {"sentiment": "neutral", "confidence": 0.5, "summary": "内容为空"}

            # 构建提示
            prompt = f"""请分析以下内容的情感倾向，需要返回JSON格式：
{{
    "sentiment": "正面/负面/中性",
    "confidence": 0.0-1.0,
    "key_points": ["观点1", "观点2"],
    "summary": "50字情感摘要"
}}

分析内容：
{content[:2000]}
"""

            response = await chat_with_llm(
                prompt=prompt,
                model="deepseek-chat",
                system_message="你是一个专业的舆情分析助手，擅长分析文本情感和观点。",
                temperature=0.3,
            )

            # 解析JSON响应
            import json
            import re

            # 尝试提取JSON
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                    return result
                except:
                    pass

            # 如果解析失败，返回默认值
            return {"sentiment": "neutral", "confidence": 0.5, "summary": response[:100]}

        except Exception as e:
            logger.error(f"LLM情感分析失败: {e}")
            return {"sentiment": "neutral", "confidence": 0.5, "summary": f"分析失败: {str(e)}"}

    def _generate_sentiment_report(self, news: Dict, sentiment: Dict) -> str:
        """生成舆情分析报告"""
        title = news.get("title", "未知标题")
        url = news.get("url", "")
        sentiment_label = sentiment.get("sentiment", "中性")
        confidence = sentiment.get("confidence", 0.0)
        key_points = sentiment.get("key_points", [])
        summary = sentiment.get("summary", "")

        # 情感emoji映射
        emoji_map = {
            "正面": "😄",
            "负面": "😟",
            "中性": "😐"
        }
        emoji = emoji_map.get(sentiment_label, "😐")

        report_lines = [
            f"📊 舆情分析报告",
            "",
            f"**标题**: {title}",
            "",
            f"**情感倾向**: {emoji} {sentiment_label} (置信度: {confidence:.1%})",
            "",
        ]

        if summary:
            report_lines.append(f"**情感摘要**: {summary}")
            report_lines.append("")

        if key_points:
            report_lines.append("**关键观点**:")
            for point in key_points[:3]:
                report_lines.append(f"- {point}")
            report_lines.append("")

        if url:
            report_lines.append(f"**原文链接**: {url}")

        report_lines.append("")
        report_lines.append(f"*由 AI 舆情分析助手生成*")

        return "\n".join(report_lines)

    async def _execute_prediction(self, intent_result: IntentResult) -> ExecutionResult:
        """执行预测分析任务"""
        import asyncio

        result = ExecutionResult(success=False, message="")

        try:
            # 从消息中提取内容（URL或文本）
            message = intent_result.message

            # 移除预测关键词
            trigger_words = ["预测", "推演", "未来趋势", "预测分析"]
            for word in trigger_words:
                message = message.replace(word, "").strip()

            # 提取URL
            url_match = re.search(r"https?://[^\s]+", message)
            target_content = ""
            content_source = ""

            if url_match:
                # 有URL，获取URL内容
                url = url_match.group(0)
                result.message = f"✅ 已收到，正在分析预测：{url[:50]}..."
                content_source = url
            elif message.strip():
                # 使用用户输入的文本
                target_content = message.strip()[:5000]
                result.message = f"✅ 已收到，正在进行预测分析..."
                content_source = "用户输入"
            else:
                result.message = "请提供要预测的内容（URL或描述）"
                return result

            result.success = True

            # 异步执行预测
            asyncio.create_task(self._run_prediction(target_content, content_source, intent_result.user_id))

        except Exception as e:
            logger.error(f"预测分析失败: {e}")
            result.message = f"处理失败: {str(e)}"

        return result

    async def _run_prediction(self, content: str, content_source: str, user_id: str):
        """后台运行预测分析"""
        try:
            from src.mcp.tools.llm import chat_with_llm
            from src.prompts import get_prompt

            # 如果有URL，先获取内容
            if content_source.startswith("http"):
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(content_source)
                        if response.status_code == 200:
                            # 提取文本内容（简单处理）
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(response.text, 'html.parser')
                            content = soup.get_text()[:8000]
                        else:
                            await self._send_error_to_user(user_id, f"获取URL内容失败: {response.status_code}")
                            return
                except Exception as e:
                    await self._send_error_to_user(user_id, f"获取内容失败: {str(e)}")
                    return

            if not content or len(content) < 50:
                await self._send_error_to_user(user_id, "内容太短，无法进行预测分析")
                return

            # 构建预测提示
            system_prompt = get_prompt("mirofish_predictor")

            prompt = f"""请基于以下内容进行预测性分析：

{content}

请从以下维度进行分析：
1. 可能的发展情景（至少2个）
2. 每个情景的发生概率
3. 预测的时间跨度
4. 建议的应对行动

请以JSON格式输出。"""

            # 调用LLM
            response = await chat_with_llm(
                prompt=prompt,
                model="deepseek-chat",
                system_message=system_prompt or "你是一个趋势预测专家，擅长基于现有信息进行情景推演和趋势预测。",
                temperature=0.5,
            )

            # 解析结果并生成报告
            report = self._generate_prediction_report(response, content_source)

            # 发送结果给用户
            from src.adapters.feishu_adapter import FeishuAdapter
            feishu = FeishuAdapter()
            await feishu.send_message(
                chat_id=user_id,
                content=report,
                chat_type="direct"
            )

        except Exception as e:
            logger.error(f"后台预测分析失败: {e}")
            await self._send_error_to_user(user_id, f"预测分析失败: {str(e)}")

    def _generate_prediction_report(self, llm_response: str, source: str) -> str:
        """生成预测分析报告"""
        import json
        import re

        # 尝试解析JSON
        prediction_data = None
        json_match = re.search(r'\{[^{}]*\}', llm_response, re.DOTALL)
        if json_match:
            try:
                prediction_data = json.loads(json_match.group(0))
            except:
                pass

        if not prediction_data:
            # 如果解析失败，直接返回LLM响应
            return f"📈 预测分析报告\n\n来源: {source}\n\n{llm_response[:3000]}"

        # 构建报告
        report_lines = [
            "📈 预测分析报告",
            "",
            f"**来源**: {source}",
            ""
        ]

        # 场景描述
        if "scenario" in prediction_data:
            report_lines.append(f"**预测场景**: {prediction_data['scenario']}")
            report_lines.append("")

        # 预测结果
        if "predictions" in prediction_data:
            report_lines.append("## 🔮 情景预测")
            report_lines.append("")
            for i, pred in enumerate(prediction_data.get("predictions", []), 1):
                title = pred.get("title", f"情景{i}")
                probability = pred.get("probability", "未知")
                reasoning = pred.get("reasoning", "")[:200]
                report_lines.append(f"**{i}. {title}** (概率: {probability})")
                if reasoning:
                    report_lines.append(f"   {reasoning}")
                report_lines.append("")

        # 趋势分析
        if "trends" in prediction_data:
            report_lines.append("## 📊 趋势预测")
            report_lines.append("")
            for trend in prediction_data.get("trends", []):
                report_lines.append(f"- {trend}")
            report_lines.append("")

        # 时间跨度
        if "time_horizon" in prediction_data:
            report_lines.append(f"**⏱️ 预测时间跨度**: {prediction_data['time_horizon']}")
            report_lines.append("")

        # 建议行动
        if "recommended_actions" in prediction_data:
            report_lines.append("## 💡 建议行动")
            report_lines.append("")
            for action in prediction_data.get("recommended_actions", []):
                report_lines.append(f"- {action}")
            report_lines.append("")

        report_lines.append("*由 AI 预测分析助手生成*")

        return "\n".join(report_lines)

    async def _send_error_to_user(self, user_id: str, error_msg: str):
        """发送错误消息给用户"""
        try:
            from src.adapters.feishu_adapter import FeishuAdapter
            feishu = FeishuAdapter()
            await feishu.send_message(
                chat_id=user_id,
                content=f"❌ {error_msg}",
                chat_type="direct"
            )
        except Exception as e:
            logger.error(f"发送错误消息失败: {e}")

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

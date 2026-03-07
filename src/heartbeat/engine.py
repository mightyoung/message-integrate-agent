"""
Heartbeat Cycle Engine - 自主驱动的"脉搏"

实现 OpenClaw 风格的心跳循环机制：
- 定期唤醒与感知
- 认知升级循环（7步）
- 从"用中学"到"中学用"

设计参考：
- APScheduler: Python 定时任务标准
- Celery Beat: 分布式定时调度
- OpenClaw: 自主智能体心跳机制
- Self-Healing AI: 自主监控系统
"""
import asyncio
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class HeartbeatState(Enum):
    """心跳状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class HeartbeatStep(Enum):
    """心跳循环的7个步骤"""
    INFORMATION_INTAKE = "information_intake"      # 信息摄入
    VALUE_JUDGMENT = "value_judgment"            # 价值判断
    KNOWLEDGE_OUTPUT = "knowledge_output"        # 知识输出
    SOCIAL_MAINTENANCE = "social_maintenance"    # 社交维护
    SELF_REFLECTION = "self_reflection"          # 自我反思
    SKILL_UPDATE = "skill_update"               # 技能更新
    NOTIFICATION_CHECK = "notification_check"   # 通知检查


class HeartbeatTask(ABC):
    """心跳任务基类"""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.run_count: int = 0
        self.error_count: int = 0

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务

        Args:
            context: 共享上下文

        Returns:
            任务结果
        """
        pass

    def mark_success(self):
        """标记成功"""
        self.last_run = datetime.now()
        self.run_count += 1

    def mark_error(self):
        """标记错误"""
        self.error_count += 1


class InformationIntakeTask(HeartbeatTask):
    """信息摄入任务 - 使用搜索工具获取最新信息"""

    def __init__(self):
        super().__init__("information_intake", enabled=True)
        self.topics = [
            "AI agent architecture",
            "autonomous AI systems",
            "LLM self-improvement",
        ]
        self.max_articles = 5

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行信息摄入 - 真实调用搜索API"""
        logger.info("🔍 [Heartbeat] 开始信息摄入...")

        articles = []

        # 使用已有的搜索工具
        try:
            from src.mcp.tools.search import search_web

            for topic in self.topics[:2]:  # 限制主题数量
                try:
                    # 调用搜索工具
                    results = await search_web(topic, max_results=self.max_articles)
                    if isinstance(results, list):
                        for r in results:
                            articles.append({
                                "source": r.get("url", "unknown"),
                                "title": r.get("title", "Untitled"),
                                "summary": r.get("content", "")[:200],
                                "topic": topic,
                                "timestamp": datetime.now().isoformat(),
                            })
                except Exception as e:
                    logger.warning(f"搜索 {topic} 失败: {e}")

        except ImportError:
            logger.warning("搜索工具不可用，使用本地信息源")
            # 备用：从本地日志和配置读取
            articles = await self._fallback_intake()

        logger.info(f"📖 [Heartbeat] 读取了 {len(articles)} 篇内容")

        self.mark_success()
        return {
            "articles": articles,
            "count": len(articles),
        }

    async def _fallback_intake(self) -> List[Dict]:
        """备用信息摄入 - 从本地读取"""
        articles = []

        # 读取最近的日志文件
        log_path = Path("logs/app.log")
        if log_path.exists():
            try:
                content = log_path.read_text()
                # 提取错误和警告
                lines = content.split("\n")
                errors = [l for l in lines if "ERROR" in l][-5:]
                for err in errors:
                    articles.append({
                        "source": "local_logs",
                        "title": "System Error Pattern",
                        "summary": err[:200],
                        "topic": "system_health",
                        "timestamp": datetime.now().isoformat(),
                    })
            except Exception as e:
                logger.warning(f"读取日志失败: {e}")

        return articles


class ValueJudgmentTask(HeartbeatTask):
    """价值判断任务 - 分析信息质量"""

    def __init__(self):
        super().__init__("value_judgment", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行价值判断 - 使用LLM评分或规则判断"""
        logger.info("🗳️ [Heartbeat] 开始价值判断...")

        articles = context.get("information_inttake", {}).get("articles", [])
        if not articles:
            articles = context.get("intake", {}).get("articles", [])

        votes = []

        for article in articles:
            # 使用规则进行评分
            score = self._calculate_score(article)
            votes.append({
                "article": article,
                "score": score,
                "approved": score > 0.5,
            })

        approved = [v for v in votes if v["approved"]]
        rejected = [v for v in votes if not v["approved"]]

        logger.info(f"🗳️ [Heartbeat] 筛选了 {len(approved)}/{len(articles)} 篇高质量内容")

        self.mark_success()
        return {
            "votes": votes,
            "approved_count": len(approved),
            "rejected_count": len(rejected),
        }

    def _calculate_score(self, article: Dict) -> float:
        """计算文章质量分数"""
        score = 0.5

        title = article.get("title", "").lower()
        summary = article.get("summary", "").lower()

        # 关键词加分
        positive_keywords = ["agent", "autonomous", "self-improving", "llm", "ai"]
        for kw in positive_keywords:
            if kw in title or kw in summary:
                score += 0.1

        # 长度加分
        if len(summary) > 100:
            score += 0.1

        return min(score, 1.0)


class KnowledgeOutputTask(HeartbeatTask):
    """知识输出任务 - 保存有价值的见解到经验库"""

    def __init__(self):
        super().__init__("knowledge_output", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行知识输出 - 写入经验日志"""
        logger.info("✍️ [Heartbeat] 开始知识输出...")

        # 获取高价值内容
        judgment_result = context.get("value_judgment", {})
        votes = judgment_result.get("votes", [])
        if not votes:
            votes = context.get("judgment", {}).get("votes", [])

        outputs = []
        learnings_path = Path(".learnings")

        for item in votes[:3]:
            if not item.get("approved"):
                continue

            article = item.get("article", {})
            output = {
                "article_title": article.get("title"),
                "summary": article.get("summary", "")[:300],
                "score": item.get("score"),
                "timestamp": datetime.now().isoformat(),
            }

            # 写入经验库
            try:
                learnings_path.mkdir(exist_ok=True)
                insight_file = learnings_path / f"insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                insight_file.write_text(json.dumps(output, ensure_ascii=False, indent=2))
                output["saved"] = True
            except Exception as e:
                logger.warning(f"保存见解失败: {e}")
                output["saved"] = False

            outputs.append(output)

        logger.info(f"✍️ [Heartbeat] 保存了 {len(outputs)} 篇见解到经验库")

        self.mark_success()
        return {
            "outputs": outputs,
            "count": len(outputs),
        }


class SocialMaintenanceTask(HeartbeatTask):
    """社交维护任务 - 检查各平台健康状态"""

    def __init__(self):
        super().__init__("social_maintenance", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行社交维护 - 检查平台状态"""
        logger.info("👥 [Heartbeat] 开始社交维护...")

        platforms = ["telegram", "feishu", "wechat"]
        messages = []
        health_status = {}

        # 检查各平台适配器状态
        try:
            from src.adapters.registry import get_adapter_registry
            registry = get_adapter_registry()

            for platform in platforms:
                try:
                    adapter = registry.get_adapter(platform)
                    if adapter:
                        # 调用健康检查
                        health = await adapter.health_check()
                        health_status[platform] = health
                        messages.append({
                            "platform": platform,
                            "status": "healthy" if health.get("status") == "ok" else "unhealthy",
                            "details": health,
                        })
                    else:
                        messages.append({
                            "platform": platform,
                            "status": "not_registered",
                        })
                except Exception as e:
                    messages.append({
                        "platform": platform,
                        "status": "error",
                        "error": str(e),
                    })

        except ImportError:
            logger.warning("适配器注册表不可用")
            for platform in platforms:
                messages.append({
                    "platform": platform,
                    "status": "unknown",
                })

        # 检查活跃连接
        try:
            from src.gateway.websocket_server import WebSocketGateway
            # 简化：记录需要检查
            active_connections = 0
        except ImportError:
            active_connections = 0

        logger.info(f"👥 [Heartbeat] 检查了 {len(messages)} 个平台")

        self.mark_success()
        return {
            "messages": messages,
            "health_status": health_status,
            "active_connections": active_connections,
        }


class SelfReflectionTask(HeartbeatTask):
    """自我反思任务 - 分析系统表现和反馈"""

    def __init__(self):
        super().__init__("self_reflection", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行自我反思 - 分析指标和反馈"""
        logger.info("🔄 [Heartbeat] 开始自我反思...")

        # 获取各项指标
        skill_updates = []
        notifications = []

        # 1. 从可观测性服务获取指标
        try:
            from src.observability import get_observability_service
            observability = get_observability_service()
            metrics = observability.metrics.get_metrics()

            total_requests = metrics.get("counters", {}).get("requests_total", 0)
            total_errors = metrics.get("counters", {}).get("errors_total", 0)
            error_rate = total_errors / total_requests if total_requests > 0 else 0

            # 如果错误率过高，触发技能更新
            if error_rate > 0.1:
                skill_updates.append({
                    "type": "error_rate_high",
                    "value": error_rate,
                    "action": "需要检查错误率上升原因",
                })

        except ImportError:
            logger.warning("可观测性服务不可用")

        # 2. 从反馈服务获取用户反馈
        try:
            from src.feedback import get_feedback_service
            feedback_service = get_feedback_service()
            stats = feedback_service.get_stats()

            if stats.thumbs_down_count > stats.thumbs_up_count * 0.2:
                skill_updates.append({
                    "type": "negative_feedback_high",
                    "value": stats.thumbs_down_count,
                    "action": "需要分析负面反馈原因",
                })

        except ImportError:
            logger.warning("反馈服务不可用")

        # 3. 从心跳获取任务统计
        engine_status = context.get("_engine_status", {})
        tasks = engine_status.get("tasks", {})

        # 统计失败的任务
        failed_tasks = [
            step for step, status in tasks.items()
            if status.get("error_count", 0) > 0
        ]

        if failed_tasks:
            skill_updates.append({
                "type": "task_failures",
                "tasks": failed_tasks,
                "action": "需要调查失败任务",
            })

        # 4. 检查系统通知
        try:
            # 检查是否有新的日志错误
            log_errors = self._check_recent_errors()
            if log_errors:
                notifications.extend(log_errors)
        except Exception as e:
            logger.warning(f"检查日志错误失败: {e}")

        stats = {
            "total_tasks": len(tasks),
            "failed_tasks": len(failed_tasks),
            "skill_updates": len(skill_updates),
            "notifications": len(notifications),
        }

        logger.info(f"🔄 [Heartbeat] 自我反思完成: {len(skill_updates)} 个更新项")

        self.mark_success()
        return {
            "skill_updates": skill_updates,
            "notifications": notifications,
            "stats": stats,
        }

    def _check_recent_errors(self) -> List[Dict]:
        """检查最近的错误"""
        errors = []
        log_path = Path("logs/app.log")

        if log_path.exists():
            try:
                content = log_path.read_text()
                lines = content.split("\n")
                recent_errors = [l for l in lines if "ERROR" in l][-5:]

                for err in recent_errors:
                    errors.append({
                        "type": "log_error",
                        "message": err[:100],
                        "timestamp": datetime.now().isoformat(),
                    })
            except Exception as e:
                logger.warning(f"读取日志失败: {e}")

        return errors


class SkillUpdateTask(HeartbeatTask):
    """技能更新任务 - 检查并更新技能"""

    def __init__(self):
        super().__init__("skill_update", enabled=True)
        self.skills_dir = Path("skills")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能更新 - 扫描并加载新技能"""
        logger.info("⚡ [Heartbeat] 开始技能更新检查...")

        updates = []

        # 1. 检查技能目录
        if self.skills_dir.exists():
            try:
                skill_files = list(self.skills_dir.glob("*.py"))
                for sf in skill_files:
                    if sf.name.startswith("_"):
                        continue

                    # 检查文件修改时间
                    mtime = datetime.fromtimestamp(sf.stat().st_mtime)
                    hours_since_modified = (datetime.now() - mtime).total_seconds() / 3600

                    # 如果最近1小时有更新
                    if hours_since_modified < 1:
                        updates.append({
                            "type": "skill_modified",
                            "file": str(sf),
                            "action": "reload_skill",
                        })

            except Exception as e:
                logger.warning(f"扫描技能目录失败: {e}")

        # 2. 检查自我反思建议
        reflection = context.get("self_reflection", {})
        skill_updates = reflection.get("skill_updates", [])

        for su in skill_updates:
            updates.append({
                "type": "reflection_action",
                "action": su.get("action"),
                "reason": su.get("type"),
            })

        # 3. 尝试重新加载技能
        if updates:
            try:
                from src.skills.loader import get_skills_loader
                loader = get_skills_loader()
                await loader.reload_skills()
                logger.info(f"⚡ [Heartbeat] 重新加载了技能")
            except Exception as e:
                logger.warning(f"重新加载技能失败: {e}")

        if updates:
            logger.info(f"⚡ [Heartbeat] 发现 {len(updates)} 个技能更新")
        else:
            logger.info("⚡ [Heartbeat] 技能已是最新")

        self.mark_success()
        return {
            "updates": updates,
            "count": len(updates),
        }


class NotificationCheckTask(HeartbeatTask):
    """通知检查任务 - 检查系统通知和告警"""

    def __init__(self):
        super().__init__("notification_check", enabled=True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行通知检查 - 检查各渠道通知"""
        logger.info("🔔 [Heartbeat] 开始通知检查...")

        notifications = []

        # 1. 检查系统健康
        try:
            health = await self._check_system_health()
            if health.get("issues"):
                notifications.extend(health.get("issues"))
        except Exception as e:
            logger.warning(f"系统健康检查失败: {e}")

        # 2. 检查待处理任务
        try:
            pending = await self._check_pending_tasks()
            notifications.extend(pending)
        except Exception as e:
            logger.warning(f"检查待处理任务失败: {e}")

        # 3. 检查用户活动
        try:
            user_activity = await self._check_user_activity()
            if user_activity:
                notifications.extend(user_activity)
        except Exception as e:
            logger.warning(f"检查用户活动失败: {e}")

        logger.info(f"🔔 [Heartbeat] 发现 {len(notifications)} 个通知")

        self.mark_success()
        return {
            "notifications": notifications,
            "count": len(notifications),
        }

    async def _check_system_health(self) -> Dict:
        """检查系统健康状态"""
        issues = []

        # 检查日志错误
        log_path = Path("logs/app.log")
        if log_path.exists():
            try:
                content = log_path.read_text()
                recent_errors = [l for l in content.split("\n") if "ERROR" in l][-10:]
                if len(recent_errors) > 5:
                    issues.append({
                        "type": "error_spike",
                        "severity": "warning",
                        "count": len(recent_errors),
                    })
            except Exception:
                pass

        # 检查磁盘空间
        try:
            import shutil
            disk_usage = shutil.disk_usage(".")
            percent_used = disk_usage.used / disk_usage.total * 100
            if percent_used > 90:
                issues.append({
                    "type": "disk_space_low",
                    "severity": "critical",
                    "percent": percent_used,
                })
        except Exception:
            pass

        return {"issues": issues}

    async def _check_pending_tasks(self) -> List[Dict]:
        """检查待处理任务"""
        pending = []

        # 检查推送队列
        try:
            from src.push import get_push_service
            # 简化：返回空列表
        except ImportError:
            pass

        return pending

    async def _check_user_activity(self) -> List[Dict]:
        """检查用户活动"""
        activity = []

        # 检查新用户反馈
        try:
            from src.feedback import get_feedback_service
            # 简化：返回空列表
        except ImportError:
            pass

        return activity


class HeartbeatEngine:
    """
    心跳循环引擎

    核心特性：
    - 事件驱动：不阻塞主消息处理
    - 可配置：支持不同间隔的不同任务
    - 错误隔离：单个任务失败不影响整体
    - 可观测：每个步骤都有日志和状态
    """

    def __init__(
        self,
        interval_hours: float = 4,
        enabled: bool = True,
    ):
        """
        初始化心跳引擎

        Args:
            interval_hours: 心跳间隔（小时）
            enabled: 是否启用
        """
        self.interval_seconds = interval_hours * 3600
        self.enabled = enabled
        self.state = HeartbeatState.IDLE

        # 任务注册表
        self.tasks: Dict[HeartbeatStep, HeartbeatTask] = {}

        # 统计信息
        self.total_cycles = 0
        self.last_cycle_time: Optional[datetime] = None

        # 上下文（心跳步骤之间共享）
        self.context: Dict[str, Any] = {}

        # 注册默认任务
        self._register_default_tasks()

        logger.info(f"💓 心跳引擎初始化完成，间隔: {interval_hours}小时")

    def _register_default_tasks(self):
        """注册默认任务"""
        self.register_task(HeartbeatStep.INFORMATION_INTAKE, InformationIntakeTask())
        self.register_task(HeartbeatStep.VALUE_JUDGMENT, ValueJudgmentTask())
        self.register_task(HeartbeatStep.KNOWLEDGE_OUTPUT, KnowledgeOutputTask())
        self.register_task(HeartbeatStep.SOCIAL_MAINTENANCE, SocialMaintenanceTask())
        self.register_task(HeartbeatStep.SELF_REFLECTION, SelfReflectionTask())
        self.register_task(HeartbeatStep.SKILL_UPDATE, SkillUpdateTask())
        self.register_task(HeartbeatStep.NOTIFICATION_CHECK, NotificationCheckTask())

    def register_task(self, step: HeartbeatStep, task: HeartbeatTask):
        """注册心跳任务"""
        self.tasks[step] = task
        logger.debug(f"📝 注册心跳任务: {step.value} -> {task.name}")

    def unregister_task(self, step: HeartbeatStep):
        """注销心跳任务"""
        if step in self.tasks:
            del self.tasks[step]
            logger.debug(f"🗑️ 注销心跳任务: {step.value}")

    async def start(self):
        """启动心跳循环"""
        if not self.enabled:
            logger.info("💓 心跳引擎已禁用")
            return

        if self.state == HeartbeatState.RUNNING:
            logger.warning("💓 心跳引擎已在运行中")
            return

        self.state = HeartbeatState.RUNNING
        logger.info("💓 心跳引擎启动")

        # 启动心跳循环
        asyncio.create_task(self._heartbeat_loop())

    async def stop(self):
        """停止心跳循环"""
        self.state = HeartbeatState.STOPPED
        logger.info("💓 心跳引擎已停止")

    async def pause(self):
        """暂停心跳"""
        self.state = HeartbeatState.PAUSED
        logger.info("💓 心跳引擎已暂停")

    async def resume(self):
        """恢复心跳"""
        if self.state == HeartbeatState.PAUSED:
            self.state = HeartbeatState.RUNNING
            logger.info("💓 心跳引擎已恢复")

    async def _heartbeat_loop(self):
        """心跳主循环"""
        while self.state == HeartbeatState.RUNNING:
            try:
                # 执行一个完整的心跳周期
                await self._execute_cycle()

                self.total_cycles += 1
                self.last_cycle_time = datetime.now()

                # 等待下一次心跳
                logger.info(f"💓 心跳周期 #{self.total_cycles} 完成，等待 {self.interval_seconds/3600} 小时")
                await asyncio.sleep(self.interval_seconds)

            except asyncio.CancelledError:
                logger.info("💓 心跳循环被取消")
                break
            except Exception as e:
                logger.error(f"💓 心跳循环错误: {e}")
                # 等待后重试
                await asyncio.sleep(60)

    async def _execute_cycle(self):
        """执行一个完整的心跳周期"""
        cycle_start = datetime.now()
        logger.info("=" * 50)
        logger.info(f"🫀 开始心跳周期 #{self.total_cycles + 1}")
        logger.info("=" * 50)

        # 清空上下文
        self.context = {
            "cycle_start": cycle_start.isoformat(),
            "cycle_number": self.total_cycles + 1,
            "_engine_status": self.get_status(),
        }

        # 按顺序执行7个步骤
        step_order = [
            HeartbeatStep.INFORMATION_INTAKE,
            HeartbeatStep.VALUE_JUDGMENT,
            HeartbeatStep.KNOWLEDGE_OUTPUT,
            HeartbeatStep.SOCIAL_MAINTENANCE,
            HeartbeatStep.SELF_REFLECTION,
            HeartbeatStep.SKILL_UPDATE,
            HeartbeatStep.NOTIFICATION_CHECK,
        ]

        for step in step_order:
            if self.state != HeartbeatState.RUNNING:
                break

            if step not in self.tasks:
                continue

            task = self.tasks[step]

            if not task.enabled:
                logger.debug(f"⏭️ 跳过任务: {step.value} (已禁用)")
                continue

            # 执行任务
            try:
                logger.info(f"▶️ 执行: {step.value}")
                result = await task.execute(self.context)

                # 将结果存入上下文，供后续步骤使用
                self.context[step.value] = result

                logger.info(f"✅ 完成: {step.value}")

            except Exception as e:
                logger.error(f"❌ 任务失败: {step.value} - {e}")
                task.mark_error()

        cycle_end = datetime.now()
        duration = (cycle_end - cycle_start).total_seconds()

        logger.info("=" * 50)
        logger.info(f"🫀 心跳周期完成，耗时: {duration:.2f}秒")
        logger.info("=" * 50)

    def get_status(self) -> Dict[str, Any]:
        """获取心跳引擎状态"""
        task_status = {}
        for step, task in self.tasks.items():
            task_status[step.value] = {
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "run_count": task.run_count,
                "error_count": task.error_count,
            }

        return {
            "state": self.state.value,
            "enabled": self.enabled,
            "interval_hours": self.interval_seconds / 3600,
            "total_cycles": self.total_cycles,
            "last_cycle_time": self.last_cycle_time.isoformat() if self.last_cycle_time else None,
            "tasks": task_status,
        }

    def set_interval(self, hours: float):
        """设置心跳间隔"""
        self.interval_seconds = hours * 3600
        logger.info(f"💓 心跳间隔已更新为 {hours} 小时")

    def enable_task(self, step: HeartbeatStep):
        """启用任务"""
        if step in self.tasks:
            self.tasks[step].enabled = True

    def disable_task(self, step: HeartbeatStep):
        """禁用任务"""
        if step in self.tasks:
            self.tasks[step].enabled = False


# 全局实例
_heartbeat_engine: Optional[HeartbeatEngine] = None


def get_heartbeat_engine() -> HeartbeatEngine:
    """获取全局心跳引擎实例"""
    global _heartbeat_engine
    if _heartbeat_engine is None:
        _heartbeat_engine = HeartbeatEngine()
    return _heartbeat_engine

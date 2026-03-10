# coding=utf-8
"""
Console Simulation - 控制台模拟输出 (简化版)

模拟用户点击菜单或发送消息的完整流程
不依赖 mcp 模块，直接测试核心逻辑

运行方式:
    python3 -m src.router.console_simulation_simple
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ConsoleSimulator:
    """控制台模拟器

    模拟用户交互完整流程
    """

    # 菜单选项
    MENU_OPTIONS = {
        "1": {
            "type": "menu",
            "menu_id": "menu_intelligence_hot",
            "name": "查看热点新闻",
            "description": "获取今日热点新闻"
        },
        "2": {
            "type": "menu",
            "menu_id": "menu_intelligence_tech",
            "name": "查看科技动态",
            "description": "获取最新科技资讯"
        },
        "3": {
            "type": "menu",
            "menu_id": "menu_intelligence_ai",
            "name": "查看AI进展",
            "description": "获取AI/大模型最新进展"
        },
        "4": {
            "type": "menu",
            "menu_id": "menu_intelligence_investment",
            "name": "查看投资并购",
            "description": "获取投资并购最新消息"
        },
        "5": {
            "type": "text",
            "content": "帮我看看今天的科技新闻",
            "name": "发送消息",
            "description": "发送文本消息触发"
        },
        "6": {
            "type": "text",
            "content": "有什么热点新闻",
            "name": "发送消息",
            "description": "发送文本消息触发"
        },
    }

    def print_header(self):
        """打印头部"""
        print("=" * 70)
        print("                    📬 用户交互流程模拟")
        print("=" * 70)

    def print_menu(self):
        """打印菜单选项"""
        print("\n【请选择操作】")
        print("-" * 40)
        for key, option in self.MENU_OPTIONS.items():
            print(f"  {key}. {option['name']}")
            print(f"     {option['description']}")
        print("-" * 40)
        print("  0. 退出")
        print("=" * 40)

    def print_user_action(self, option: dict):
        """打印用户操作"""
        print("\n" + "=" * 70)
        print("【用户操作】")
        print("-" * 40)

        if option["type"] == "menu":
            print(f"  类型: 菜单点击")
            print(f"  内容: {option['name']}")
        else:
            print(f"  类型: 发送消息")
            print(f"  内容: {option['content']}")

        print(f"  用户ID: test_user_001")
        print("-" * 40)

    def print_system_processing(self):
        """打印系统处理"""
        print("\n【系统处理】")

    def print_step(self, step: dict, indent: int = 2):
        """打印步骤"""
        prefix = " " * indent
        status_icon = {
            "start": "⏳",
            "success": "✓",
            "error": "✗",
            "warning": "⚠️",
        }

        icon = status_icon.get(step.get("status", "start"), "⏳")

        # 步骤名称
        step_name = step.get("step", "unknown")
        step_name_display = {
            "menu_parse": "1. 事件解析",
            "message_parse": "1. 消息解析",
            "intent_recognition": "2. 意图识别",
            "task_execution": "3. 任务执行",
            "response": "4. 响应生成",
        }.get(step_name, step_name)

        print(f"{prefix}{icon} {step_name_display}")

        # 详细信息
        if step.get("status") == "start":
            print(f"{prefix}   {step.get('message', '开始处理')}")
        elif step.get("status") == "success":
            details = []
            if step.get("source"):
                details.append(f"来源: {step.get('source')}")
            if step.get("confidence"):
                details.append(f"置信度: {step.get('confidence')}")
            if step.get("intent"):
                details.append(f"意图: {step.get('intent')}")
            if step.get("agent"):
                details.append(f"Agent: {step.get('agent')}")
            if step.get("category"):
                details.append(f"分类: {step.get('category')}")
            if step.get("fetched"):
                details.append(f"获取: {step.get('fetched')}条")

            if details:
                print(f"{prefix}   {', '.join(details)}")
        elif step.get("status") == "error":
            print(f"{prefix}   ✗ {step.get('message', '处理失败')}")
        elif step.get("status") == "warning":
            print(f"{prefix}   ⚠️ {step.get('message', '')}")

    def print_result(self, result):
        """打印执行结果"""
        print("\n【执行结果】")
        print("-" * 40)

        if result.success:
            print(f"  ✅ 状态: 成功")
        else:
            print(f"  ❌ 状态: 失败")

        print(f"  ⏱️  耗时: {result.execution_time:.2f}s")
        print(f"  📝 消息: {result.message[:100]}...")

    def print_stats(self, handler):
        """打印统计信息"""
        stats = handler.get_stats()
        print("\n【统计信息】")
        print("-" * 40)
        print(f"  总请求: {stats['total_requests']}")
        print(f"  菜单事件: {stats['menu_events']}")
        print(f"  消息事件: {stats['message_events']}")
        print(f"  成功: {stats['success_count']}")
        print(f"  失败: {stats['failure_count']}")

    async def run(self):
        """运行模拟器"""
        # 直接导入避免通过 __init__.py 导入 mcp
        from src.router.menu_handler import FeishuMenuHandler
        from src.router.keyword_router import KeywordRouter, KeywordRule
        from src.intelligence.pipeline import IntelligencePipeline, PipelineConfig

        print("=" * 70)
        print("                    📬 用户交互流程模拟")
        print("=" * 70)

        # 初始化组件
        menu_handler = FeishuMenuHandler()
        keyword_router = KeywordRouter()

        # 添加关键词规则
        keyword_router.add_rule(
            ["热点新闻", "今日新闻", "最新新闻", "热门新闻"],
            "intelligence",
            "view_hot_news"
        )
        keyword_router.add_rule(
            ["科技", "技术", "AI", "人工智能"],
            "intelligence",
            "view_category_news"
        )
        keyword_router.add_rule(
            ["投资", "融资", "并购"],
            "intelligence",
            "view_category_news"
        )
        keyword_router.set_default("llm")

        while True:
            self.print_menu()

            # 获取用户输入
            choice = input("\n请输入选项 (0-6): ").strip()

            if choice == "0":
                print("\n👋 再见!")
                break

            if choice not in self.MENU_OPTIONS:
                print("\n⚠️  无效选项，请重新选择")
                continue

            # 获取选项
            option = self.MENU_OPTIONS[choice]

            # 打印用户操作
            self.print_user_action(option)

            # 打印系统处理开始
            self.print_system_processing()

            try:
                # 构建事件
                if option["type"] == "menu":
                    event = {
                        "event": {
                            "type": "im.menu",
                            "menu_event": {
                                "menu_event_id": option["menu_id"],
                                "user_id": "test_user_001",
                                "chat_id": "oc_test_chat"
                            }
                        }
                    }

                    # 1. 解析菜单事件
                    print("  ⏳ 1. 事件解析")
                    intent_result = await menu_handler.handle_menu_event(event)

                    if intent_result:
                        print(f"  ✓ 1. 事件解析成功")
                        print(f"      意图: {intent_result.intent}")
                        print(f"      Agent: {intent_result.agent}")

                        # 2. 意图识别
                        print("  ✓ 2. 意图识别")
                        print(f"      来源: menu")
                        print(f"      置信度: {intent_result.confidence}")

                        # 3. 任务执行
                        print("  ⏳ 3. 任务执行")

                        if intent_result.agent == "intelligence":
                            category = intent_result.params.get("category", "hot")
                            if intent_result.intent == "view_hot_news":
                                category = "hot"

                            print(f"      分类: {category}")

                            # 执行情报流水线
                            config = PipelineConfig(
                                rss_categories=[category],
                                rss_lang="zh" if category in ["hot", "investment"] else "en",
                                rss_max_tier=2,
                            )

                            pipeline = IntelligencePipeline(config)
                            pipeline.storage = None  # 禁用存储
                            result = await pipeline.process(user_id="test_user_001")

                            print(f"  ✓ 3. 任务执行成功")

                            fetched = result.get("fetched", 0)
                            status = result.get("status", "unknown")

                            print(f"\n【执行结果】")
                            print("-" * 40)
                            print(f"  ✅ 状态: {status}")
                            print(f"  📝 获取情报: {fetched}条")
                        else:
                            print(f"  ✓ 3. 任务执行 (Agent: {intent_result.agent})")
                    else:
                        print("  ✗ 1. 事件解析失败")

                else:
                    # 文本消息处理
                    content = option["content"]

                    # 1. 消息解析
                    print("  ⏳ 1. 消息解析")
                    print(f"      内容: {content}")
                    print(f"  ✓ 1. 消息解析成功")

                    # 2. 意图识别 (关键词路由)
                    print("  ⏳ 2. 意图识别")
                    route_result = keyword_router.route(content)

                    if route_result:
                        agent = route_result.get("agent", "llm")
                        action = route_result.get("action", "")
                        print(f"  ✓ 2. 意图识别成功")
                        print(f"      来源: keyword")
                        print(f"      置信度: 0.9")
                        print(f"      Agent: {agent}")
                        print(f"      Action: {action}")

                        # 3. 任务执行
                        print("  ⏳ 3. 任务执行")

                        if agent == "intelligence":
                            category = "tech"
                            if "科技" in content:
                                category = "tech"
                            elif "投资" in content:
                                category = "investment"
                            elif "热点" in content or "新闻" in content:
                                category = "hot"

                            print(f"      分类: {category}")

                            # 执行情报流水线
                            config = PipelineConfig(
                                rss_categories=[category],
                                rss_lang="zh" if category in ["hot", "investment"] else "en",
                                rss_max_tier=2,
                            )

                            pipeline = IntelligencePipeline(config)
                            pipeline.storage = None  # 禁用存储
                            result = await pipeline.process(user_id="test_user_001")

                            print(f"  ✓ 3. 任务执行成功")

                            fetched = result.get("fetched", 0)
                            status = result.get("status", "unknown")

                            print(f"\n【执行结果】")
                            print("-" * 40)
                            print(f"  ✅ 状态: {status}")
                            print(f"  📝 获取情报: {fetched}条")
                        else:
                            print(f"  ✓ 3. 任务执行 (Agent: {agent})")

                            print(f"\n【执行结果】")
                            print("-" * 40)
                            print(f"  ✅ 状态: success")
                            print(f"  📝 消息: {agent} Agent 处理中...")
                    else:
                        # 默认使用LLM
                        print(f"  ✓ 2. 意图识别 (默认)")

                        print(f"\n【执行结果】")
                        print("-" * 40)
                        print(f"  ✅ 状态: success")
                        print(f"  📝 消息: LLM 处理中...")

            except Exception as e:
                print(f"\n❌ 执行失败: {e}")
                import traceback
                traceback.print_exc()

            # 等待用户继续
            input("\n按回车继续...")


async def quick_demo():
    """快速演示"""
    # 直接导入避免通过 __init__.py 导入 mcp
    from src.router.menu_handler import FeishuMenuHandler
    from src.router.keyword_router import KeywordRouter
    from src.intelligence.pipeline import IntelligencePipeline, PipelineConfig

    print("=" * 70)
    print("                    🚀 快速演示模式")
    print("=" * 70)

    # 初始化组件
    menu_handler = FeishuMenuHandler()
    keyword_router = KeywordRouter()

    # 添加关键词规则
    keyword_router.add_rule(
        ["热点新闻", "新闻"],
        "intelligence",
        "view_hot_news"
    )
    keyword_router.add_rule(
        ["科技", "技术", "AI"],
        "intelligence",
        "view_category_news"
    )
    keyword_router.set_default("llm")

    # 测试1: 菜单点击
    print("\n\n【测试1: 菜单点击 - 查看热点新闻】")
    event1 = {
        "event": {
            "type": "im.menu",
            "menu_event": {
                "menu_event_id": "menu_intelligence_hot",
                "user_id": "test_user",
                "chat_id": "oc_test"
            }
        }
    }

    intent_result = await menu_handler.handle_menu_event(event1)
    print(f"意图: {intent_result.intent}")
    print(f"Agent: {intent_result.agent}")
    print(f"置信度: {intent_result.confidence}")

    if intent_result and intent_result.agent == "intelligence":
        config = PipelineConfig(
            rss_categories=["hot"],
            rss_lang="zh",
            rss_max_tier=2,
        )
        pipeline = IntelligencePipeline(config)
        # 禁用存储以避免 Redis 连接问题
        pipeline.storage = None
        result = await pipeline.process(user_id="test_user")
        print(f"流水线结果: {result.get('status')}")
        print(f"获取情报: {result.get('fetched', 0)}条")

    # 测试2: 文本消息
    print("\n\n【测试2: 文本消息 - 科技动态】")
    content = "帮我看看科技新闻"
    route_result = keyword_router.route(content)
    print(f"Agent: {route_result.get('agent')}")
    print(f"Action: {route_result.get('action')}")

    if route_result.get("agent") == "intelligence":
        config = PipelineConfig(
            rss_categories=["tech"],
            rss_lang="en",
            rss_max_tier=2,
        )
        pipeline = IntelligencePipeline(config)
        result = await pipeline.process(user_id="test_user")
        print(f"流水线结果: {result.get('status')}")
        print(f"获取情报: {result.get('fetched', 0)}条")

    print("\n\n✅ 演示完成!")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="用户交互流程模拟")
    parser.add_argument("--demo", action="store_true", help="快速演示模式")
    args = parser.parse_args()

    if args.demo:
        await quick_demo()
    else:
        simulator = ConsoleSimulator()
        await simulator.run()


if __name__ == "__main__":
    asyncio.run(main())

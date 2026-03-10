# coding=utf-8
"""
Console Simulation - 控制台模拟输出

模拟用户点击菜单或发送消息的完整流程

运行方式:
    python -m src.router.console_simulation
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

    def __init__(self):
        self.handler = None

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
        from src.router.unified_handler import get_unified_handler

        # 初始化处理器
        self.handler = get_unified_handler()

        while True:
            self.print_header()
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
            else:
                event = {
                    "event": {
                        "type": "im.message",
                        "message": {
                            "message_id": "msg_test_001",
                            "body": {
                                "content": option["content"]
                            },
                            "sender": {
                                "user_id": "test_user_001"
                            }
                        }
                    }
                }

            # 执行处理
            result = await self.handler.handle(event)

            # 打印处理步骤
            for step in result.steps:
                self.print_step(step)

            # 打印结果
            self.print_result(result)

            # 打印统计
            self.print_stats(self.handler)

            # 等待用户继续
            input("\n按回车继续...")


async def quick_demo():
    """快速演示"""
    from src.router.unified_handler import get_unified_handler

    print("=" * 70)
    print("                    🚀 快速演示模式")
    print("=" * 70)

    handler = get_unified_handler()

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

    result1 = await handler.handle(event1)
    print(f"\n执行结果: {result1.message}")
    print(f"执行时间: {result1.execution_time:.2f}s")

    # 测试2: 文本消息
    print("\n\n【测试2: 文本消息 - 科技动态】")
    event2 = {
        "event": {
            "type": "im.message",
            "message": {
                "message_id": "msg_002",
                "body": {
                    "content": "帮我看看科技新闻"
                },
                "sender": {
                    "user_id": "test_user"
                }
            }
        }
    }

    result2 = await handler.handle(event2)
    print(f"\n执行结果: {result2.message}")
    print(f"执行时间: {result2.execution_time:.2f}s")

    # 打印统计
    print("\n\n【统计信息】")
    stats = handler.get_stats()
    print(f"总请求: {stats['total_requests']}")
    print(f"成功: {stats['success_count']}")


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

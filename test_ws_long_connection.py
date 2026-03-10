#!/usr/bin/env python3
# coding=utf-8
"""
飞书 WebSocket 长连接测试服务

直接在本地启动，测试飞书长连接是否正常工作

使用 Python SDK 的 lark_oapi.ws.Client
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """主函数"""
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        print("错误: 请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET 环境变量")
        print(f"当前 FEISHU_APP_ID: {app_id}")
        print(f"当前 FEISHU_APP_SECRET: {'已设置' if app_secret else '未设置'}")
        return

    print(f"=" * 60)
    print(f"飞书 WebSocket 长连接测试")
    print(f"=" * 60)
    print(f"App ID: {app_id}")
    print(f"App Secret: {'*' * len(app_secret) if app_secret else '未设置'}")
    print()

    try:
        import lark_oapi
        from lark_oapi import ws
        from lark_oapi.core.enum import LogLevel

        # 创建事件处理器 - 使用 do 方法处理事件
        class MyEventHandler(lark_oapi.EventDispatcherHandler):
            def do(self, callback):
                """处理飞书事件"""
                # 打印事件内容
                print(f"\n📩 收到事件:")
                print(f"   Type: {callback.type}")
                print(f"   Timestamp: {callback.timestamp}")
                print(f"   Event: {callback.event}")
                return {"code": 0}

        # 创建事件处理器
        print("1. 创建事件处理器...")
        event_handler = MyEventHandler()
        print("✅ 事件处理器创建成功")

        # 创建 WebSocket 客户端
        print("2. 创建 WebSocket 客户端...")
        ws_client = ws.Client(
            app_id=app_id,
            app_secret=app_secret,
            log_level=LogLevel.DEBUG,
            event_handler=event_handler,
        )
        print("✅ WebSocket 客户端创建成功")

        print()
        print("3. 启动长连接...")
        print("   (按 Ctrl+C 停止)")
        print()

        # 启动连接 (会阻塞)
        # 使用新事件循环避免冲突
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        ws_client.start()

    except KeyboardInterrupt:
        print("\n正在停止...")
        print("已停止")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

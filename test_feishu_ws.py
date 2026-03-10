#!/usr/bin/env python3
# coding=utf-8
"""
飞书 WebSocket 长连接测试脚本

用法:
    python test_feishu_ws.py

环境变量:
    FEISHU_APP_ID
    FEISHU_APP_SECRET
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_connection():
    """测试飞书长连接"""
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        print("错误: 请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET 环境变量")
        return

    print(f"测试飞书长连接...")
    print(f"App ID: {app_id}")

    try:
        from lark_oapi import client
        from lark_oapi.ws import Client as WSClient

        # 创建配置
        config = client.Config.new_builder(
            app_id=app_id,
            app_secret=app_secret,
        ).build()

        # 创建客户端
        client_obj = client.Client(config)

        # 检查凭据
        print("获取 access token...")
        token = client_obj.get_tenant_access_token()
        if not token:
            print("✗ 获取 access token 失败")
            return

        print(f"✓ Access token 获取成功: {token[:20]}...")

        # 创建 WebSocket 客户端
        print("创建 WebSocket 客户端...")
        ws_client = WSClient(config)

        # 定义消息处理函数
        def on_message(data):
            print(f"收到消息: {data}")

        # 设置回调 (如果有API支持的话)
        print("✓ 准备启动 WebSocket 长连接...")
        print("注意: 必须在飞书开发者后台配置长连接事件!")
        print("按 Ctrl+C 退出")

        # 启动 (会阻塞)
        print("启动 WebSocket 连接...")
        ws_client.start()

    except KeyboardInterrupt:
        print("\n测试完成")
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_connection()

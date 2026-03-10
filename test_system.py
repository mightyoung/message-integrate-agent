#!/usr/bin/env python3
# coding=utf-8
"""
综合测试脚本：飞书长连接 + Mihomo 代理测试

用法:
    python3 test_system.py [--feishu] [--mihomo] [--all]

选项:
    --feishu    仅测试飞书长连接
    --mihomo    仅测试 mihomo 代理
    --all       测试所有（默认）
"""
import argparse
import asyncio
import os
import sys
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_mihomo():
    """测试 mihomo 代理"""
    print("=" * 60)
    print("Mihomo 代理测试")
    print("=" * 60)

    import httpx

    # 测试直连（无代理）
    print("\n[1] 测试直连访问百度...")
    try:
        response = httpx.get("https://www.baidu.com", timeout=10)
        print(f"    ✅ 百度访问成功: {response.status_code}")
    except Exception as e:
        print(f"    ❌ 百度访问失败: {e}")

    # 测试代理
    print("\n[2] 测试代理访问...")
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    print(f"    HTTP_PROXY: {http_proxy}")
    print(f"    HTTPS_PROXY: {https_proxy}")

    if not http_proxy and not https_proxy:
        print("    ⚠️  未配置代理环境变量")
        return False

    # 测试通过代理访问 Tavily
    print("\n[3] 测试代理访问 Tavily (需要代理)...")
    try:
        proxies = {
            "http://": http_proxy,
            "https://": https_proxy,
        }
        response = httpx.get(
            "https://api.tavily.com/health",
            proxies=proxies,
            timeout=15
        )
        print(f"    ✅ Tavily API 访问成功: {response.status_code}")
    except Exception as e:
        print(f"    ❌ Tavily API 访问失败: {e}")

    # 测试 GitHub（可能需要代理）
    print("\n[4] 测试代理访问 GitHub...")
    try:
        proxies = {
            "http://": http_proxy,
            "https://": https_proxy,
        }
        response = httpx.get(
            "https://api.github.com",
            proxies=proxies,
            timeout=15
        )
        print(f"    ✅ GitHub API 访问成功: {response.status_code}")
    except Exception as e:
        print(f"    ❌ GitHub API 访问失败: {e}")

    # 测试飞书直连（不需要代理）
    print("\n[5] 测试飞书直连（不应该走代理）...")
    try:
        # 飞书应该直连，不走代理
        response = httpx.get(
            "https://open.feishu.cn",
            timeout=15
        )
        print(f"    ✅ 飞书访问成功: {response.status_code}")
    except Exception as e:
        print(f"    ❌ 飞书访问失败: {e}")

    print("\n" + "=" * 60)
    print("Mihomo 代理测试完成")
    print("=" * 60)
    return True


def test_feishu_ws():
    """测试飞书 WebSocket 长连接"""
    print("=" * 60)
    print("飞书 WebSocket 长连接测试")
    print("=" * 60)

    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        print("错误: 请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET 环境变量")
        print(f"当前 FEISHU_APP_ID: {app_id}")
        print(f"当前 FEISHU_APP_SECRET: {'已设置' if app_secret else '未设置'}")
        return False

    print(f"\nApp ID: {app_id}")
    print(f"App Secret: {'*' * len(app_secret) if app_secret else '未设置'}")
    print()

    try:
        import lark_oapi
        from lark_oapi import ws
        from lark_oapi.core.enum import LogLevel

        # 创建事件处理器
        class MessageEventHandler(lark_oapi.EventDispatcherHandler):
            def __init__(self):
                super().__init__()
                self.message_count = 0

            def do(self, callback):
                self.message_count += 1
                print(f"\n📩 收到事件 #{self.message_count}:")
                print(f"   Type: {callback.type}")
                print(f"   Timestamp: {callback.timestamp}")
                if hasattr(callback, 'event') and callback.event:
                    print(f"   Event: {callback.event}")
                return {"code": 0}

        print("[1] 创建事件处理器...")
        event_handler = MessageEventHandler()
        print("    ✅ 事件处理器创建成功")

        print("\n[2] 创建 WebSocket 客户端...")
        ws_client = ws.Client(
            app_id=app_id,
            app_secret=app_secret,
            log_level=LogLevel.INFO,
            event_handler=event_handler,
        )
        print("    ✅ WebSocket 客户端创建成功")

        print("\n[3] 启动长连接...")
        print("    (将在 30 秒后自动断开)")
        print("    请在此期间向飞书机器人发送消息进行测试")
        print()

        # 启动连接
        ws_client.start()

    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("飞书 WebSocket 长连接测试完成")
    print("=" * 60)
    return True


async def test_feishu_adapter():
    """测试飞书 Adapter（集成测试）"""
    print("=" * 60)
    print("飞书 Adapter 集成测试")
    print("=" * 60)

    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")

    config = {
        "app_id": app_id,
        "app_secret": app_secret,
        "webhook_url": webhook_url,
        "connection_mode": "websocket",  # 使用 WebSocket 模式
    }

    from src.adapters.feishu_adapter import FeishuAdapter

    adapter = FeishuAdapter(config)

    print("\n[1] 连接飞书...")
    success = await adapter.connect()
    if success:
        print("    ✅ 飞书连接成功")
    else:
        print("    ❌ 飞书连接失败")
        return False

    print("\n[2] 测试发送消息...")
    # 这里使用 webhook 发送测试
    if webhook_url:
        test_content = f"🧪 测试消息 - {time.strftime('%H:%M:%S')}"
        result = await adapter._send_via_webhook(test_content)
        if result:
            print(f"    ✅ 消息发送成功: {test_content}")
        else:
            print("    ❌ 消息发送失败")
    else:
        print("    ⚠️  未配置 webhook，跳过发送测试")

    print("\n[3] 断开连接...")
    await adapter.disconnect()
    print("    ✅ 已断开连接")

    print("\n" + "=" * 60)
    print("飞书 Adapter 测试完成")
    print("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description="综合测试脚本")
    parser.add_argument("--feishu", action="store_true", help="仅测试飞书长连接")
    parser.add_argument("--mihomo", action="store_true", help="仅测试 mihomo 代理")
    parser.add_argument("--all", action="store_true", default=True, help="测试所有")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🧪 Message Integrate Agent 综合测试")
    print("=" * 60)
    print()

    if args.mihomo:
        test_mihomo()
    elif args.feishu:
        # 测试飞书长连接
        test_feishu_ws()
    else:
        # 测试全部
        print("请选择测试类型：")
        print("  1. 飞书长连接测试")
        print("  2. Mihomo 代理测试")
        print("  3. 飞书 Adapter 集成测试")
        print("  4. 全部测试")
        print()

        choice = input("请输入选项 (1-4): ").strip()

        if choice == "1":
            test_feishu_ws()
        elif choice == "2":
            test_mihomo()
        elif choice == "3":
            asyncio.run(test_feishu_adapter())
        elif choice == "4":
            print("\n>>> 开始 Mihomo 代理测试 <<<\n")
            test_mihomo()
            print("\n>>> 开始飞书 Adapter 测试 <<<\n")
            asyncio.run(test_feishu_adapter())
        else:
            print("无效选项")


if __name__ == "__main__":
    main()

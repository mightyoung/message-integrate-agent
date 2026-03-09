#!/usr/bin/env python3
# coding=utf-8
"""
Feishu Message Templates Test

测试消息模板和回调处理功能
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.adapters.feishu_templates import (
    FeishuCardBuilder,
    CallbackRouter,
    IntelligenceItem,
    MessageAction,
    MessagePriority,
    create_intelligence_card,
    create_feedback_card,
    create_agent_response,
    get_callback_router,
)


def test_intelligence_card():
    """测试情报推送卡片"""
    print("\n🧪 测试 1: 情报推送卡片")
    print("-" * 40)

    items = [
        IntelligenceItem(
            id="1",
            title="OpenAI 发布 GPT-5 带来重大突破",
            url="https://example.com/1",
            category="AI突破",
            score=0.95,
            source="TechCrunch"
        ),
        IntelligenceItem(
            id="2",
            title="地缘政治紧张局势加剧",
            url="https://example.com/2",
            category="地缘政治",
            score=0.88,
            source="Reuters"
        ),
        IntelligenceItem(
            id="3",
            title="NASA 发现新的宜居星球",
            url="https://example.com/3",
            category="科学",
            score=0.82,
            source="NASA"
        ),
    ]

    card = FeishuCardBuilder.build_intelligence_card(
        items=items,
        priority=MessagePriority.NORMAL,
        show_pagination=True,
        show_feedback=True,
    )

    # 验证结构
    assert card["msg_type"] == "interactive"
    assert "card" in card
    assert "header" in card["card"]
    assert "elements" in card["card"]

    # 打印预览
    print(f"✅ 卡片创建成功")
    print(f"   标题: {card['card']['header']['title']['content']}")
    print(f"   模板: {card['card']['header']['template']}")
    print(f"   元素数: {len(card['card']['elements'])}")

    # 打印 JSON 结构
    print(f"\n📄 JSON 结构预览:")
    print(json.dumps(card, indent=2, ensure_ascii=False)[:500] + "...")

    return True


def test_feedback_card():
    """测试反馈卡片"""
    print("\n🧪 测试 2: 反馈卡片")
    print("-" * 40)

    card = FeishuCardBuilder.build_feedback_card(
        title="📝 内容反馈",
        content="这篇关于 AI 的文章对您有帮助吗？",
        item_id="article_123"
    )

    assert card["msg_type"] == "interactive"
    assert "feedback_useful" in json.dumps(card)
    assert "feedback_not_useful" in json.dumps(card)

    print(f"✅ 反馈卡片创建成功")
    print(f"   按钮数: 3 (👍👎💬)")

    return True


def test_agent_response():
    """测试 Agent 响应卡片"""
    print("\n🧪 测试 3: Agent 响应卡片")
    print("-" * 40)

    actions = [
        MessageAction(
            id="search_more",
            label="🔍 搜索更多",
            action_type="callback",
            value="ai"
        ),
        MessageAction(
            id="open_link",
            label="📖 查看详情",
            action_type="url",
            value="https://example.com"
        ),
    ]

    card = FeishuCardBuilder.build_agent_response(
        response="根据搜索结果，GPT-5 是 OpenAI 最新发布的大语言模型，在多项基准测试中超越了现有模型。",
        actions=actions,
        quoted_content="用户询问: GPT-5 是什么？",
        priority=MessagePriority.NORMAL
    )

    assert card["msg_type"] == "interactive"
    assert "🤖 AI 助手" in card["card"]["header"]["title"]["content"]

    print(f"✅ Agent 响应卡片创建成功")
    print(f"   动作数: {len(actions)}")

    return True


def test_callback_router():
    """测试回调路由器"""
    print("\n🧪 测试 4: 回调路由器")
    print("-" * 40)

    router = get_callback_router()

    # 测试处理反馈回调
    async def test_callbacks():
        # 测试点赞回调
        response = await router.handle(
            "feedback_useful",
            {"item_id": "test_123"},
            "user_123",
            "msg_123"
        )

        assert "感谢" in response.get("content", {}).get("text", "")
        print(f"✅ 点赞回调处理成功")

        # 测试建议回调 (返回输入框卡片)
        response = await router.handle(
            "feedback_suggest",
            {"item_id": "test_456"},
            "user_456",
            "msg_456"
        )

        assert response["msg_type"] == "interactive"
        assert "input" in json.dumps(response)
        print(f"✅ 建议回调处理成功 (返回输入框)")

        # 测试未知回调
        response = await router.handle(
            "unknown_action",
            {},
            "user_789",
            "msg_789"
        )

        assert "未知" in response.get("content", {}).get("text", "")
        print(f"✅ 未知回调处理成功 (返回提示)")

    asyncio.run(test_callbacks())

    # 列出所有注册的处理器
    print(f"\n📋 已注册的回调处理器:")
    for action_id in router._handlers.keys():
        print(f"   - {action_id}")

    return True


def test_confirm_card():
    """测试确认卡片"""
    print("\n🧪 测试 5: 确认卡片")
    print("-" * 40)

    card = FeishuCardBuilder.build_confirm_card(
        title="📬 订阅确认",
        content="您确定要订阅每日简报吗？我们将每天为您推送精选情报。",
        confirm_action=MessageAction(
            id="confirm_subscribe",
            label="确认订阅",
            action_type="callback",
            value="daily"
        ),
        cancel_label="取消"
    )

    assert card["msg_type"] == "interactive"
    assert card["card"]["header"]["title"]["content"] == "📬 订阅确认"
    assert len(card["card"]["elements"][1]["actions"]) == 2

    print(f"✅ 确认卡片创建成功")
    print(f"   标题: {card['card']['header']['title']['content']}")
    print(f"   动作数: {len(card['card']['elements'][1]['actions'])}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🚀 Feishu 消息模板测试")
    print("=" * 60)

    tests = [
        ("情报推送卡片", test_intelligence_card),
        ("反馈卡片", test_feedback_card),
        ("Agent响应", test_agent_response),
        ("回调路由器", test_callback_router),
        ("确认卡片", test_confirm_card),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            if test_fn():
                passed += 1
        except Exception as e:
            print(f"❌ {name} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

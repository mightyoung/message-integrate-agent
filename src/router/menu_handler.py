# coding=utf-8
"""
Feishu Menu Handler - 飞书菜单事件处理器

处理用户点击飞书机器人自定义菜单时的事件。

设计参考:
- 飞书官方文档: https://open.feishu.cn/document/client-docs/bot-v3/bot-customized-menu
- pyfeishubot: https://github.com/yry0008/pyfeishubot
"""
from dataclasses import dataclass
from typing import Dict, Optional, Any
from loguru import logger


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: str
    agent: str
    params: Dict[str, Any]
    confidence: float
    source: str  # "menu", "rule", "vector", "llm"
    user_id: str = ""
    message: str = ""


class FeishuMenuHandler:
    """飞书菜单事件处理器

    处理用户点击菜单时的事件，将菜单项映射为意图。

    菜单配置:
    - 📰 情报: 热点新闻, 科技动态, AI进展, 投资并购, 行业报告
    - 🔍 搜索: 搜索新闻, 搜索资讯, 搜索趋势, 高级搜索
    - ⚙️ 设置: 获取当前配置, 切换推送频率, 语言设置, 清除会话历史
    """

    # 菜单 ID 到意图的映射
    MENU_MAPPING: Dict[str, Dict[str, Any]] = {
        # ==================== 主菜单: 情报 ====================
        "menu_intelligence_hot": {
            "intent": "view_hot_news",
            "name": "查看热点新闻",
            "agent": "intelligence",
            "params": {"category": "hot"}
        },
        "menu_intelligence_tech": {
            "intent": "view_category_news",
            "name": "查看科技动态",
            "agent": "intelligence",
            "params": {"category": "tech"}
        },
        "menu_intelligence_ai": {
            "intent": "view_category_news",
            "name": "查看AI进展",
            "agent": "intelligence",
            "params": {"category": "ai"}
        },
        "menu_intelligence_investment": {
            "intent": "view_category_news",
            "name": "查看投资并购",
            "agent": "intelligence",
            "params": {"category": "investment"}
        },
        "menu_intelligence_report": {
            "intent": "view_category_news",
            "name": "查看行业报告",
            "agent": "intelligence",
            "params": {"category": "report"}
        },

        # ==================== 主菜单: 搜索 ====================
        "menu_search_news": {
            "intent": "search_intelligence",
            "name": "搜索新闻",
            "agent": "search",
            "params": {"type": "news"}
        },
        "menu_search_info": {
            "intent": "search_intelligence",
            "name": "搜索资讯",
            "agent": "search",
            "params": {"type": "info"}
        },
        "menu_search_trend": {
            "intent": "search_intelligence",
            "name": "搜索趋势",
            "agent": "search",
            "params": {"type": "trend"}
        },
        "menu_search_advanced": {
            "intent": "search_advanced",
            "name": "高级搜索",
            "agent": "search",
            "params": {}
        },

        # ==================== 主菜单: 设置 ====================
        "menu_settings_get": {
            "intent": "get_settings",
            "name": "获取当前配置",
            "agent": "system",
            "params": {}
        },
        "menu_settings_frequency": {
            "intent": "change_settings",
            "name": "切换推送频率",
            "agent": "system",
            "params": {"key": "frequency"}
        },
        "menu_settings_language": {
            "intent": "change_settings",
            "name": "语言设置",
            "agent": "system",
            "params": {"key": "language"}
        },
        "menu_settings_clear": {
            "intent": "clear_history",
            "name": "清除会话历史",
            "agent": "system",
            "params": {}
        },
    }

    def __init__(self):
        """初始化菜单处理器"""
        self._build_reverse_lookup()

    def _build_reverse_lookup(self):
        """构建反向查找表 (intent -> menu_id)"""
        self._intent_to_menu: Dict[str, str] = {}
        for menu_id, config in self.MENU_MAPPING.items():
            intent = config["intent"]
            if intent not in self._intent_to_menu:
                self._intent_to_menu[intent] = []
            self._intent_to_menu[intent].append(menu_id)

    async def handle_menu_event(
        self,
        event: Dict[str, Any]
    ) -> Optional[IntentResult]:
        """处理菜单点击事件

        飞书发送的菜单事件格式:
        {
            "event": {
                "type": "im.menu",
                "menu_event": {
                    "chat_id": "oc_xxx",
                    "user_id": "ou_xxx",
                    "menu_event_id": "menu_intelligence_hot"
                }
            }
        }

        Args:
            event: 飞书 webhook 事件

        Returns:
            IntentResult: 意图识别结果
        """
        try:
            # 提取菜单事件数据
            menu_event = event.get("event", {}).get("menu_event", {})
            menu_id = menu_event.get("menu_event_id", "")
            user_id = menu_event.get("user_id", "")
            chat_id = menu_event.get("chat_id", "")

            if not menu_id:
                logger.warning("菜单事件缺少 menu_event_id")
                return None

            # 查找菜单配置
            if menu_id not in self.MENU_MAPPING:
                logger.warning(f"未知菜单项: {menu_id}")
                return None

            config = self.MENU_MAPPING[menu_id]

            logger.info(
                f"用户点击菜单: {menu_id} -> {config['name']} "
                f"(user: {user_id}, chat: {chat_id})"
            )

            # 返回意图结果 (100% 置信度，因为是确定性菜单操作)
            return IntentResult(
                intent=config["intent"],
                agent=config["agent"],
                params=config["params"],
                confidence=1.0,
                source="menu",
                user_id=user_id,
                message=config["name"]
            )

        except Exception as e:
            logger.error(f"处理菜单事件失败: {e}")
            return None

    def get_menu_by_intent(self, intent: str) -> Optional[Dict[str, Any]]:
        """根据意图获取菜单配置

        Args:
            intent: 意图 ID

        Returns:
            菜单配置或 None
        """
        menu_ids = self._intent_to_menu.get(intent, [])
        if menu_ids:
            menu_id = menu_ids[0]
            return self.MENU_MAPPING.get(menu_id)
        return None

    def get_all_menus(self) -> Dict[str, Dict[str, Any]]:
        """获取所有菜单配置"""
        return self.MENU_MAPPING.copy()

    def get_menu_names(self) -> Dict[str, str]:
        """获取菜单 ID 到名称的映射"""
        return {
            menu_id: config["name"]
            for menu_id, config in self.MENU_MAPPING.items()
        }


# ==================== 全局实例 ====================

_menu_handler: Optional[FeishuMenuHandler] = None


def get_menu_handler() -> FeishuMenuHandler:
    """获取全局菜单处理器实例"""
    global _menu_handler
    if _menu_handler is None:
        _menu_handler = FeishuMenuHandler()
    return _menu_handler


def get_callback_router():
    """获取回调路由器 (兼容现有代码)

    返回一个简单的回调路由器，
    将 action_id 映射到处理函数。
    """
    handler = get_menu_handler()

    # 构建 action_id 到意图的映射
    router = {}
    for menu_id, config in handler.MENU_MAPPING.items():
        router[menu_id] = config["intent"]

    return router

# coding=utf-8
"""
Tests for Feishu Menu Handler
"""
import pytest
from src.router.menu_handler import FeishuMenuHandler, IntentResult, get_menu_handler


class TestFeishuMenuHandler:
    """Test suite for FeishuMenuHandler"""

    def test_handler_creation(self):
        """Test handler can be created"""
        handler = FeishuMenuHandler()
        assert handler is not None
        assert len(handler.MENU_MAPPING) == 13

    def test_global_instance(self):
        """Test global instance creation"""
        handler1 = get_menu_handler()
        handler2 = get_menu_handler()
        assert handler1 is handler2  # Same instance

    def test_menu_mappings(self):
        """Test all menu mappings are defined"""
        handler = get_menu_handler()

        # Test key menus
        assert "menu_intelligence_hot" in handler.MENU_MAPPING
        assert "menu_search_news" in handler.MENU_MAPPING
        assert "menu_settings_get" in handler.MENU_MAPPING

        # Verify mappings
        hot_config = handler.MENU_MAPPING["menu_intelligence_hot"]
        assert hot_config["intent"] == "view_hot_news"
        assert hot_config["agent"] == "intelligence"

    def test_get_menu_names(self):
        """Test getting menu names"""
        handler = get_menu_handler()
        names = handler.get_menu_names()

        assert "menu_intelligence_hot" in names
        assert names["menu_intelligence_hot"] == "查看热点新闻"

    def test_reverse_lookup(self):
        """Test intent to menu reverse lookup"""
        handler = get_menu_handler()

        # view_category_news should have multiple menus
        menus = handler._intent_to_menu.get("view_category_news", [])
        assert len(menus) >= 4  # tech, ai, investment, report

    @pytest.mark.asyncio
    async def test_handle_menu_event(self):
        """Test handling menu event"""
        handler = get_menu_handler()

        # Build test event
        event = {
            "event": {
                "menu_event": {
                    "menu_event_id": "menu_intelligence_hot",
                    "user_id": "ou_123456",
                    "chat_id": "oc_789012"
                }
            }
        }

        result = await handler.handle_menu_event(event)

        assert result is not None
        assert result.intent == "view_hot_news"
        assert result.agent == "intelligence"
        assert result.confidence == 1.0
        assert result.source == "menu"
        assert result.user_id == "ou_123456"

    @pytest.mark.asyncio
    async def test_handle_unknown_menu(self):
        """Test handling unknown menu"""
        handler = get_menu_handler()

        event = {
            "event": {
                "menu_event": {
                    "menu_event_id": "unknown_menu",
                    "user_id": "ou_123456"
                }
            }
        }

        result = await handler.handle_menu_event(event)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_menu_event_missing_id(self):
        """Test handling menu event without menu_event_id"""
        handler = get_menu_handler()

        event = {
            "event": {
                "menu_event": {
                    "user_id": "ou_123456"
                }
            }
        }

        result = await handler.handle_menu_event(event)
        assert result is None


class TestIntentResult:
    """Test IntentResult dataclass"""

    def test_intent_result_creation(self):
        """Test creating IntentResult"""
        result = IntentResult(
            intent="view_hot_news",
            agent="intelligence",
            params={"category": "hot"},
            confidence=1.0,
            source="menu",
            user_id="ou_123456",
            message="查看热点新闻"
        )

        assert result.intent == "view_hot_news"
        assert result.agent == "intelligence"
        assert result.params == {"category": "hot"}
        assert result.confidence == 1.0
        assert result.source == "menu"
        assert result.user_id == "ou_123456"

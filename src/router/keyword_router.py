"""
Keyword-based router
"""
from typing import Any, Dict, List, Optional

from loguru import logger


class KeywordRule:
    """Represents a keyword routing rule."""

    def __init__(
        self,
        keywords: List[str],
        agent: str,
        action: Optional[str] = None,
    ):
        self.keywords = [k.lower() for k in keywords]
        self.agent = agent
        self.action = action

    def matches(self, text: str) -> bool:
        """Check if text contains any of the keywords."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.keywords)


class KeywordRouter:
    """
    Routes messages based on keyword matching.
    """

    def __init__(self):
        self.rules: List[KeywordRule] = []
        self.default_agent: Optional[str] = None

    def add_rule(
        self,
        keywords: List[str],
        agent: str,
        action: Optional[str] = None,
    ):
        """Add a routing rule."""
        rule = KeywordRule(keywords, agent, action)
        self.rules.append(rule)
        logger.info(f"Added keyword rule: {keywords} -> {agent}")

    def set_default(self, agent: str):
        """Set the default agent."""
        self.default_agent = agent
        logger.info(f"Default agent set to: {agent}")

    def route(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Route a message based on keywords.

        Args:
            text: Message text

        Returns:
            Dict with agent and action, or None
        """
        for rule in self.rules:
            if rule.matches(text):
                result = {"agent": rule.agent}
                if rule.action:
                    result["action"] = rule.action
                logger.info(f"Keyword routed to {rule.agent}: {rule.action or 'default'}")
                return result

        if self.default_agent:
            return {"agent": self.default_agent}

        logger.warning("No keyword match found")
        return None

    def load_from_config(self, config: Dict[str, Any]):
        """Load rules from configuration."""
        rules = config.get("rules", [])
        for rule_config in rules:
            self.add_rule(
                keywords=rule_config.get("keywords", []),
                agent=rule_config.get("agent", ""),
                action=rule_config.get("action"),
            )
        self.default_agent = config.get("default")

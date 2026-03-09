"""
Agent Card - Agent 能力描述与注册

基于 Google A2A Protocol Agent Card 规范:
- JSON 格式的 Agent 能力描述
- 支持认证方式
- 技能和能力列表
- 端点信息

参考: https://github.com/a2aproject/A2A
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class AuthType(Enum):
    """认证类型"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    OAuth2 = "oauth2"


class Capability(Enum):
    """Agent 能力"""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    SEARCH = "search"
    IMAGE_GENERATION = "image_generation"
    DATA_ANALYSIS = "data_analysis"
    REASONING = "reasoning"
    PLANNING = "planning"
    TOOL_USE = "tool_use"
    MEMORY = "memory"


@dataclass
class AgentSkill:
    """Agent 技能"""
    id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)


@dataclass
class AgentAuth:
    """Agent 认证配置"""
    type: AuthType
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCard:
    """
    Agent Card - Agent 能力描述

    包含:
    - name: Agent 名称
    - description: Agent 描述
    - url: Agent 端点 URL
    - version: Agent 版本
    - capabilities: 支持的能力列表
    - skills: 技能列表
    - auth: 认证配置
    - metadata: 额外元数据
    """

    name: str
    description: str
    url: str  # A2A Server endpoint
    version: str = "1.0.0"
    capabilities: List[Capability] = field(default_factory=list)
    skills: List[AgentSkill] = field(default_factory=list)
    auth: Optional[AgentAuth] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": [c.value for c in self.capabilities],
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "tags": s.tags,
                }
                for s in self.skills
            ],
            "auth": {
                "type": self.auth.type.value if self.auth else "none",
                "config": self.auth.config if self.auth else {},
            }
            if self.auth else None,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCard":
        """从字典创建"""
        # Parse capabilities
        capabilities = []
        for c in data.get("capabilities", []):
            if isinstance(c, str):
                capabilities.append(Capability(c))
            elif isinstance(c, Capability):
                capabilities.append(c)

        # Parse skills
        skills = []
        for s in data.get("skills", []):
            skills.append(AgentSkill(**s))

        # Parse auth
        auth_data = data.get("auth")
        auth = None
        if auth_data:
            auth_type = AuthType(auth_data.get("type", "none"))
            auth = AgentAuth(type=auth_type, config=auth_data.get("config", {}))

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            url=data["url"],
            version=data.get("version", "1.0.0"),
            capabilities=capabilities,
            skills=skills,
            auth=auth,
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )

    def has_capability(self, capability: Capability) -> bool:
        """检查是否具有某能力"""
        return capability in self.capabilities

    def has_skill(self, skill_id: str) -> bool:
        """检查是否具有某技能"""
        return any(s.id == skill_id for s in self.skills)


class AgentCardRegistry:
    """Agent Card 注册中心"""

    def __init__(self):
        self._cards: Dict[str, AgentCard] = {}
        self._by_capability: Dict[Capability, List[str]] = {}
        self._by_skill: Dict[str, List[str]] = {}

    def register(self, card: AgentCard) -> bool:
        """
        注册 Agent Card

        Args:
            card: Agent Card

        Returns:
            是否注册成功
        """
        if card.name in self._cards:
            logger.warning(f"Agent {card.name} already registered, updating")
            self._unregister_index(card.name)

        self._cards[card.name] = card
        self._build_index(card)

        logger.info(f"✅ Registered agent: {card.name}")
        return True

    def _build_index(self, card: AgentCard):
        """构建索引"""
        # By capability
        for cap in card.capabilities:
            if cap not in self._by_capability:
                self._by_capability[cap] = []
            self._by_capability[cap].append(card.name)

        # By skill
        for skill in card.skills:
            if skill.id not in self._by_skill:
                self._by_skill[skill.id] = []
            self._by_skill[skill.id].append(card.name)

    def _unregister_index(self, name: str):
        """移除索引"""
        card = self._cards.get(name)
        if not card:
            return

        for cap in card.capabilities:
            if cap in self._by_capability:
                self._by_capability[cap] = [
                    n for n in self._by_capability[cap] if n != name
                ]

        for skill in card.skills:
            if skill.id in self._by_skill:
                self._by_skill[skill.id] = [
                    n for n in self._by_skill[skill.id] if n != name
                ]

    def unregister(self, name: str) -> bool:
        """
        注销 Agent

        Args:
            name: Agent 名称

        Returns:
            是否注销成功
        """
        if name not in self._cards:
            return False

        self._unregister_index(name)
        del self._cards[name]

        logger.info(f"🗑️ Unregistered agent: {name}")
        return True

    def get(self, name: str) -> Optional[AgentCard]:
        """获取 Agent Card"""
        return self._cards.get(name)

    def list_all(self) -> List[AgentCard]:
        """列出所有 Agent"""
        return list(self._cards.values())

    def find_by_capability(self, capability: Capability) -> List[AgentCard]:
        """按能力查找"""
        names = self._by_capability.get(capability, [])
        return [self._cards[n] for n in names if n in self._cards]

    def find_by_skill(self, skill_id: str) -> List[AgentCard]:
        """按技能查找"""
        names = self._by_skill.get(skill_id, [])
        return [self._cards[n] for n in names if n in self._cards]

    def get_agent_cards_json(self) -> str:
        """获取所有 Agent Cards 的 JSON"""
        return json.dumps(
            [card.to_dict() for card in self._cards.values()],
            indent=2,
            ensure_ascii=False
        )


# Global registry
_card_registry: Optional[AgentCardRegistry] = None


def get_card_registry() -> AgentCardRegistry:
    """获取全局 Agent Card 注册中心"""
    global _card_registry
    if _card_registry is None:
        _card_registry = AgentCardRegistry()
    return _card_registry

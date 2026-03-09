# coding=utf-8
"""
Threat Classifier - 基于 WorldMonitor 的威胁分类

从 WorldMonitor (https://github.com/koala73/worldmonitor) 移植:
- 关键词分类
- 5级威胁等级
- 14类事件分类

特性:
- 优先级级联: critical → high → medium → low → info
- 复合升级检测
- 排除列表
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import re


class ThreatLevel(Enum):
    """威胁等级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EventCategory(Enum):
    """事件分类"""
    CONFLICT = "conflict"
    PROTEST = "protest"
    DISASTER = "disaster"
    DIPLOMATIC = "diplomatic"
    ECONOMIC = "economic"
    TERRORISM = "terrorism"
    CYBER = "cyber"
    HEALTH = "health"
    ENVIRONMENTAL = "environmental"
    MILITARY = "military"
    CRIME = "crime"
    INFRASTRUCTURE = "infrastructure"
    TECH = "tech"
    GENERAL = "general"


@dataclass
class ThreatClassification:
    """威胁分类结果"""
    level: ThreatLevel
    category: EventCategory
    confidence: float
    source: str = "keyword"  # keyword, ml, llm


# 威胁等级颜色
THREAT_COLORS = {
    ThreatLevel.CRITICAL: "#ef4444",
    ThreatLevel.HIGH: "#f97316",
    ThreatLevel.MEDIUM: "#eab308",
    ThreatLevel.LOW: "#22c55e",
    ThreatLevel.INFO: "#3b82f6",
}

THREAT_PRIORITY = {
    ThreatLevel.CRITICAL: 5,
    ThreatLevel.HIGH: 4,
    ThreatLevel.MEDIUM: 3,
    ThreatLevel.LOW: 2,
    ThreatLevel.INFO: 1,
}

# 关键词映射
CRITICAL_KEYWORDS = {
    "nuclear strike": EventCategory.MILITARY,
    "nuclear attack": EventCategory.MILITARY,
    "nuclear war": EventCategory.MILITARY,
    "invasion": EventCategory.CONFLICT,
    "declaration of war": EventCategory.CONFLICT,
    "declares war": EventCategory.CONFLICT,
    "all-out war": EventCategory.CONFLICT,
    "full-scale war": EventCategory.CONFLICT,
    "martial law": EventCategory.MILITARY,
    "coup": EventCategory.MILITARY,
    "coup attempt": EventCategory.MILITARY,
    "genocide": EventCategory.CONFLICT,
    "ethnic cleansing": EventCategory.CONFLICT,
    "chemical attack": EventCategory.TERRORISM,
    "biological attack": EventCategory.TERRORISM,
    "dirty bomb": EventCategory.TERRORISM,
    "mass casualty": EventCategory.CONFLICT,
    "massive strikes": EventCategory.MILITARY,
    "military strikes": EventCategory.MILITARY,
    "retaliatory strikes": EventCategory.MILITARY,
    "launches strikes": EventCategory.MILITARY,
    "pandemic declared": EventCategory.HEALTH,
    "health emergency": EventCategory.HEALTH,
    "nato article 5": EventCategory.MILITARY,
    "evacuation order": EventCategory.DISASTER,
    "meltdown": EventCategory.DISASTER,
    "nuclear meltdown": EventCategory.DISASTER,
    "major combat operations": EventCategory.MILITARY,
    "declared war": EventCategory.CONFLICT,
}

HIGH_KEYWORDS = {
    "war": EventCategory.CONFLICT,
    "armed conflict": EventCategory.CONFLICT,
    "airstrike": EventCategory.CONFLICT,
    "airstrikes": EventCategory.CONFLICT,
    "air strike": EventCategory.CONFLICT,
    "drone strike": EventCategory.CONFLICT,
    "drone strikes": EventCategory.CONFLICT,
    "strikes": EventCategory.CONFLICT,
    "missile": EventCategory.MILITARY,
    "missile launch": EventCategory.MILITARY,
    "missiles fired": EventCategory.MILITARY,
    "troops deployed": EventCategory.MILITARY,
    "military escalation": EventCategory.MILITARY,
    "military operation": EventCategory.MILITARY,
    "ground offensive": EventCategory.MILITARY,
    "bombing": EventCategory.CONFLICT,
    "bombardment": EventCategory.CONFLICT,
    "shelling": EventCategory.CONFLICT,
    "casualties": EventCategory.CONFLICT,
    "killed in": EventCategory.CONFLICT,
    "hostage": EventCategory.TERRORISM,
    "terrorist": EventCategory.TERRORISM,
    "terror attack": EventCategory.TERRORISM,
    "assassination": EventCategory.CRIME,
    "cyber attack": EventCategory.CYBER,
    "ransomware": EventCategory.CYBER,
    "data breach": EventCategory.CYBER,
    "sanctions": EventCategory.ECONOMIC,
    "embargo": EventCategory.ECONOMIC,
    "earthquake": EventCategory.DISASTER,
    "tsunami": EventCategory.DISASTER,
    "hurricane": EventCategory.DISASTER,
    "typhoon": EventCategory.DISASTER,
    "attack on": EventCategory.CONFLICT,
    "attacks on": EventCategory.CONFLICT,
    "launched attack": EventCategory.CONFLICT,
    "launched attacks": EventCategory.CONFLICT,
    "explosions": EventCategory.CONFLICT,
    "military operations": EventCategory.MILITARY,
    "combat operations": EventCategory.MILITARY,
    "retaliatory strike": EventCategory.MILITARY,
    "retaliatory attack": EventCategory.MILITARY,
    "preemptive strike": EventCategory.MILITARY,
    "ballistic missile": EventCategory.MILITARY,
    "cruise missile": EventCategory.MILITARY,
    "air defense intercepted": EventCategory.MILITARY,
    "forces struck": EventCategory.CONFLICT,
}

MEDIUM_KEYWORDS = {
    "protest": EventCategory.PROTEST,
    "protests": EventCategory.PROTEST,
    "riot": EventCategory.PROTEST,
    "riots": EventCategory.PROTEST,
    "unrest": EventCategory.PROTEST,
    "demonstration": EventCategory.PROTEST,
    "strike action": EventCategory.PROTEST,
    "military exercise": EventCategory.MILITARY,
    "naval exercise": EventCategory.MILITARY,
    "arms deal": EventCategory.MILITARY,
    "weapons sale": EventCategory.MILITARY,
    "diplomatic crisis": EventCategory.DIPLOMATIC,
    "ambassador recalled": EventCategory.DIPLOMATIC,
    "expel diplomats": EventCategory.DIPLOMATIC,
    "trade war": EventCategory.ECONOMIC,
    "tariff": EventCategory.ECONOMIC,
    "recession": EventCategory.ECONOMIC,
    "inflation": EventCategory.ECONOMIC,
    "market crash": EventCategory.ECONOMIC,
    "flood": EventCategory.DISASTER,
    "flooding": EventCategory.DISASTER,
    "wildfire": EventCategory.DISASTER,
    "volcano": EventCategory.DISASTER,
    "eruption": EventCategory.DISASTER,
    "outbreak": EventCategory.HEALTH,
    "epidemic": EventCategory.HEALTH,
    "infection spread": EventCategory.HEALTH,
    "oil spill": EventCategory.ENVIRONMENTAL,
    "pipeline explosion": EventCategory.INFRASTRUCTURE,
    "blackout": EventCategory.INFRASTRUCTURE,
    "power outage": EventCategory.INFRASTRUCTURE,
    "internet outage": EventCategory.INFRASTRUCTURE,
    "derailment": EventCategory.INFRASTRUCTURE,
}

LOW_KEYWORDS = {
    "election": EventCategory.DIPLOMATIC,
    "vote": EventCategory.DIPLOMATIC,
    "referendum": EventCategory.DIPLOMATIC,
    "summit": EventCategory.DIPLOMATIC,
    "treaty": EventCategory.DIPLOMATIC,
    "agreement": EventCategory.DIPLOMATIC,
    "negotiation": EventCategory.DIPLOMATIC,
    "talks": EventCategory.DIPLOMATIC,
    "peacekeeping": EventCategory.DIPLOMATIC,
    "humanitarian aid": EventCategory.DIPLOMATIC,
    "ceasefire": EventCategory.DIPLOMATIC,
    "peace treaty": EventCategory.DIPLOMATIC,
    "climate change": EventCategory.ENVIRONMENTAL,
    "emissions": EventCategory.ENVIRONMENTAL,
    "pollution": EventCategory.ENVIRONMENTAL,
    "deforestation": EventCategory.ENVIRONMENTAL,
    "drought": EventCategory.ENVIRONMENTAL,
    "vaccine": EventCategory.HEALTH,
    "vaccination": EventCategory.HEALTH,
    "disease": EventCategory.HEALTH,
    "virus": EventCategory.HEALTH,
    "public health": EventCategory.HEALTH,
    "interest rate": EventCategory.ECONOMIC,
    "gdp": EventCategory.ECONOMIC,
    "unemployment": EventCategory.ECONOMIC,
    "regulation": EventCategory.ECONOMIC,
}

# Tech 变体关键词
TECH_HIGH_KEYWORDS = {
    "major outage": EventCategory.INFRASTRUCTURE,
    "service down": EventCategory.INFRASTRUCTURE,
    "global outage": EventCategory.INFRASTRUCTURE,
    "zero-day": EventCategory.CYBER,
    "critical vulnerability": EventCategory.CYBER,
    "supply chain attack": EventCategory.CYBER,
    "mass layoff": EventCategory.ECONOMIC,
}

TECH_MEDIUM_KEYWORDS = {
    "outage": EventCategory.INFRASTRUCTURE,
    "breach": EventCategory.CYBER,
    "hack": EventCategory.CYBER,
    "vulnerability": EventCategory.CYBER,
    "layoff": EventCategory.ECONOMIC,
    "layoffs": EventCategory.ECONOMIC,
    "antitrust": EventCategory.ECONOMIC,
    "monopoly": EventCategory.ECONOMIC,
    "ban": EventCategory.ECONOMIC,
    "shutdown": EventCategory.INFRASTRUCTURE,
}

TECH_LOW_KEYWORDS = {
    "ipo": EventCategory.ECONOMIC,
    "funding": EventCategory.ECONOMIC,
    "acquisition": EventCategory.ECONOMIC,
    "merger": EventCategory.ECONOMIC,
    "launch": EventCategory.TECH,
    "release": EventCategory.TECH,
    "update": EventCategory.TECH,
    "partnership": EventCategory.ECONOMIC,
    "startup": EventCategory.TECH,
    "ai model": EventCategory.TECH,
    "open source": EventCategory.TECH,
}

# 排除列表
EXCLUSIONS = [
    "protein", "couples", "relationship", "dating", "diet", "fitness",
    "recipe", "cooking", "shopping", "fashion", "celebrity", "movie",
    "tv show", "sports", "game", "concert", "festival", "wedding",
    "vacation", "travel tips", "life hack", "self-care", "wellness",
    "strikes deal", "strikes agreement", "strikes partnership",
]

# 短关键词 (需要词边界)
SHORT_KEYWORDS = {"war", "coup", "ban", "vote", "riot", "riots", "hack", "talks", "ipo", "gdp", "virus", "disease", "flood", "strikes"}

# 编译正则表达式缓存
_regex_cache: Dict[str, re.Pattern] = {}


def _get_keyword_regex(kw: str) -> re.Pattern:
    """获取或创建关键词正则表达式"""
    if kw not in _regex_cache:
        escaped = re.escape(kw)
        if kw in SHORT_KEYWORDS:
            _regex_cache[kw] = re.compile(rf"\b{escaped}\b")
        else:
            _regex_cache[kw] = re.compile(escaped)
    return _regex_cache[kw]


def _match_keywords(title_lower: str, keywords: Dict[str, EventCategory]) -> Tuple[str, EventCategory] | None:
    """匹配关键词"""
    for kw, cat in keywords.items():
        if _get_keyword_regex(kw).search(title_lower):
            return kw, cat
    return None


# 复合升级检测
ESCALATION_ACTIONS = re.compile(
    r"\b(attack|attacks|attacked|strike|strikes|struck|bomb|bombs|bombed|bombing|shell|shelled|shelling|missile|missiles|intercept|intercepted|retaliates|retaliating|retaliation|killed|casualties|offensive|invaded|invades)\b"
)
ESCALATION_TARGETS = re.compile(
    r"\b(iran|tehran|isfahan|tabriz|russia|moscow|china|beijing|taiwan|taipei|north korea|pyongyang|nato|us base|us forces|american forces|us military)\b"
)


def _should_escalate_to_critical(lower: str, category: EventCategory) -> bool:
    """检测是否应该升级为 critical"""
    if category not in (EventCategory.CONFLICT, EventCategory.MILITARY):
        return False
    return bool(ESCALATION_ACTIONS.search(lower) and ESCALATION_TARGETS.search(lower))


def classify_by_keyword(title: str, variant: str = "full") -> ThreatClassification:
    """通过关键词分类威胁

    Args:
        title: 新闻标题
        variant: 变体 (full, tech, etc.)

    Returns:
        ThreatClassification: 威胁分类结果
    """
    lower = title.lower()

    # 排除列表检查
    if any(ex in lower for ex in EXCLUSIONS):
        return ThreatClassification(
            level=ThreatLevel.INFO,
            category=EventCategory.GENERAL,
            confidence=0.3,
            source="keyword"
        )

    is_tech = variant == "tech"

    # 优先级级联: critical → high → medium → low → info

    # Critical
    match = _match_keywords(lower, CRITICAL_KEYWORDS)
    if match:
        return ThreatClassification(
            level=ThreatLevel.CRITICAL,
            category=match[1],
            confidence=0.9,
            source="keyword"
        )

    # High
    match = _match_keywords(lower, HIGH_KEYWORDS)
    if match:
        # 复合升级检测
        if _should_escalate_to_critical(lower, match[1]):
            return ThreatClassification(
                level=ThreatLevel.CRITICAL,
                category=match[1],
                confidence=0.85,
                source="keyword"
            )
        return ThreatClassification(
            level=ThreatLevel.HIGH,
            category=match[1],
            confidence=0.8,
            source="keyword"
        )

    if is_tech:
        match = _match_keywords(lower, TECH_HIGH_KEYWORDS)
        if match:
            return ThreatClassification(
                level=ThreatLevel.HIGH,
                category=match[1],
                confidence=0.75,
                source="keyword"
            )

    # Medium
    match = _match_keywords(lower, MEDIUM_KEYWORDS)
    if match:
        return ThreatClassification(
            level=ThreatLevel.MEDIUM,
            category=match[1],
            confidence=0.7,
            source="keyword"
        )

    if is_tech:
        match = _match_keywords(lower, TECH_MEDIUM_KEYWORDS)
        if match:
            return ThreatClassification(
                level=ThreatLevel.MEDIUM,
                category=match[1],
                confidence=0.65,
                source="keyword"
            )

    # Low
    match = _match_keywords(lower, LOW_KEYWORDS)
    if match:
        return ThreatClassification(
            level=ThreatLevel.LOW,
            category=match[1],
            confidence=0.6,
            source="keyword"
        )

    if is_tech:
        match = _match_keywords(lower, TECH_LOW_KEYWORDS)
        if match:
            return ThreatClassification(
                level=ThreatLevel.LOW,
                category=match[1],
                confidence=0.55,
                source="keyword"
            )

    # Default
    return ThreatClassification(
        level=ThreatLevel.INFO,
        category=EventCategory.GENERAL,
        confidence=0.3,
        source="keyword"
    )


def aggregate_threats(items: List[ThreatClassification]) -> ThreatClassification:
    """聚合多个威胁分类

    Args:
        items: 威胁分类列表

    Returns:
        ThreatClassification: 聚合后的威胁分类
    """
    if not items:
        return ThreatClassification(
            level=ThreatLevel.INFO,
            category=EventCategory.GENERAL,
            confidence=0.3,
            source="keyword"
        )

    # 取最高级别
    max_level = ThreatLevel.INFO
    max_priority = 0
    for item in items:
        priority = THREAT_PRIORITY.get(item.level, 0)
        if priority > max_priority:
            max_priority = priority
            max_level = item.level

    # 取最常见分类
    cat_counts: Dict[EventCategory, int] = {}
    for item in items:
        cat = item.category
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    top_cat = EventCategory.GENERAL
    top_count = 0
    for cat, count in cat_counts.items():
        if count > top_count:
            top_count = count
            top_cat = cat

    # 加权平均置信度
    weighted_sum = sum(item.confidence for item in items)
    avg_confidence = weighted_sum / len(items)

    return ThreatClassification(
        level=max_level,
        category=top_cat,
        confidence=avg_confidence,
        source="keyword"
    )


# 便捷函数
def is_alert(threat: ThreatClassification) -> bool:
    """是否为告警级别"""
    return threat.level in (ThreatLevel.CRITICAL, ThreatLevel.HIGH)


def get_threat_color(level: ThreatLevel) -> str:
    """获取威胁等级颜色"""
    return THREAT_COLORS.get(level, "#3b82f6")


def get_threat_label(level: ThreatLevel) -> str:
    """获取威胁等级标签"""
    labels = {
        ThreatLevel.CRITICAL: "CRIT",
        ThreatLevel.HIGH: "HIGH",
        ThreatLevel.MEDIUM: "MED",
        ThreatLevel.LOW: "LOW",
        ThreatLevel.INFO: "INFO",
    }
    return labels.get(level, "INFO")

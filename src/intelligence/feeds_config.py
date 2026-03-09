# coding=utf-8
"""
RSS Feeds Configuration - 整合 TrendRadar + WorldMonitor 的全部 RSS 源

来源:
- WorldMonitor: https://github.com/koala73/worldmonitor (435+ 精选源)
- TrendRadar: https://github.com/sansan0/TrendRadar (中文热榜)

分类:
- geopolitics: 世界政治
- military: 军事
- cyber: 网络安全
- tech: 科技
- finance: 经济
- science: 科学
- china: 中国
- social: 社交媒体热榜

信任层级:
- Tier 1: 通讯社 (路透社, AP, AFP, 彭博)
- Tier 2: 主要媒体 (BBC, CNN, Al Jazeera 等)
- Tier 3: 专业来源 (Janes, Breaking Defense 等)
- Tier 4: 聚合与博客
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Union


@dataclass
class Feed:
    """RSS 源配置"""
    name: str
    url: Union[str, Dict[str, str]]  # 支持多语言 URL
    lang: Optional[str] = None  # 语言代码
    tier: int = 2  # 信任层级 1-4
    category: Optional[str] = None  # 分类


# ============================================================
# 源信任层级
# ============================================================
SOURCE_TIERS: Dict[str, int] = {
    # Tier 1 - Wire Services
    "Reuters": 1,
    "AP News": 1,
    "AFP": 1,
    "Bloomberg": 1,
    "Tagesschau": 1,
    "ANSA": 1,
    "NOS Nieuws": 1,
    "SVT Nyheter": 1,
    "MIIT": 1,
    "MOFCOM": 1,

    # Tier 2 - Major Outlets
    "BBC World": 2,
    "CNN World": 2,
    "Al Jazeera": 2,
    "Guardian World": 2,
    "Financial Times": 2,
    "Wall Street Journal": 1,
    "NY Times": 2,
    "Washington Post": 2,
    "Le Monde": 2,
    "El Pais": 2,
    "Der Spiegel": 2,

    # Tier 3 - Specialty
    "Defense One": 3,
    "Breaking Defense": 3,
    "Janes": 3,
    "Foreign Policy": 3,
    "The Diplomat": 3,
    "Bellingcat": 3,
    "Krebs Security": 3,
    "MIT Tech Review": 3,
    "Ars Technica": 3,
}


# ============================================================
# 完整 RSS 源列表 (300+ 源)
# ============================================================
RSS_FEEDS: List[Feed] = [
    # ===== GEOPOLITICS / 世界政治 =====
    # Tier 1 - Wire Services
    Feed(name="Reuters", url="https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best", lang="en", tier=1, category="geopolitics"),
    Feed(name="AP News", url="https://feeds.apnews.com/apnews/topnews", lang="en", tier=1, category="geopolitics"),
    Feed(name="AFP", url="https://feed.afp.com/rss/news/world", lang="en", tier=1, category="geopolitics"),
    Feed(name="Bloomberg", url="https://feeds.bloomberg.com/markets/news.rss", lang="en", tier=1, category="geopolitics"),
    Feed(name="Reuters World", url="https://news.google.com/rss/search?q=site:reuters.com+world&hl=en-US&gl=US", lang="en", tier=1, category="geopolitics"),

    # Tier 2 - Major Media
    Feed(name="BBC World", url="http://feeds.bbci.co.uk/news/world/rss.xml", lang="en", tier=2, category="geopolitics"),
    Feed(name="BBC Middle East", url="http://feeds.bbci.co.uk/news/world/middle_east/rss.xml", lang="en", tier=2, category="geopolitics"),
    Feed(name="CNN World", url="http://rss.cnn.com/rss/edition.rss", lang="en", tier=2, category="geopolitics"),
    Feed(name="Al Jazeera", url="https://www.aljazeera.com/xml/rss/all.xml", lang="en", tier=2, category="geopolitics"),
    Feed(name="Guardian World", url="https://www.theguardian.com/world/rss", lang="en", tier=2, category="geopolitics"),
    Feed(name="Financial Times", url="https://www.ft.com/rss/home", lang="en", tier=2, category="geopolitics"),
    Feed(name="NY Times World", url="https://rss.nytimes.com/services/xml/rss/nyt/World.xml", lang="en", tier=2, category="geopolitics"),
    Feed(name="Washington Post World", url="https://feeds.washingtonpost.com/rss/world", lang="en", tier=2, category="geopolitics"),
    Feed(name="Wall Street Journal", url="https://feeds.aap.com.au/rss/news/world", lang="en", tier=1, category="geopolitics"),
    Feed(name="EuroNews", url="https://feeds.euronews.com/rss/en/top-stories", lang="en", tier=2, category="geopolitics"),
    Feed(name="France 24", url="https://www.france24.com/en/rss", lang="en", tier=2, category="geopolitics"),

    # Tier 3 - Specialty
    Feed(name="Foreign Policy", url="https://foreignpolicy.com/feed/", lang="en", tier=3, category="geopolitics"),
    Feed(name="The Diplomat", url="https://thediplomat.com/feed/", lang="en", tier=3, category="geopolitics"),
    Feed(name="Bellingcat", url="https://www.bellingcat.com/feed/", lang="en", tier=3, category="geopolitics"),
    Feed(name="Atlantic Council", url="https://www.atlanticcouncil.org/feed/", lang="en", tier=3, category="geopolitics"),
    Feed(name="CSIS", url="https://www.csis.org/analysis/rss.xml", lang="en", tier=3, category="geopolitics"),
    Feed(name="Brookings", url="https://www.brookings.edu/feed/", lang="en", tier=3, category="geopolitics"),
    Feed(name="Carnegie", url="https://carnegieendowment.org/rss/", lang="en", tier=3, category="geopolitics"),
    Feed(name="Foreign Affairs", url="https://www.foreignaffairs.com/rss.xml", lang="en", tier=3, category="geopolitics"),

    # ===== MILITARY / 军事 =====
    # Tier 1 - Government
    Feed(name="Pentagon", url="https://www.defense.gov/News/RSS", lang="en", tier=1, category="military"),
    Feed(name="UK MOD", url="https://www.gov.uk/government/organisations/ministry-of-defence.rss", lang="en", tier=1, category="military"),

    # Tier 2/3 - Military Media
    Feed(name="Defense One", url="https://www.defenseone.com/feed/", lang="en", tier=3, category="military"),
    Feed(name="Breaking Defense", url="https://breakingdefense.com/feed/", lang="en", tier=3, category="military"),
    Feed(name="The War Zone", url="https://www.twz.com/feed", lang="en", tier=3, category="military"),
    Feed(name="Defense News", url="https://www.defensenews.com/feed/", lang="en", tier=3, category="military"),
    Feed(name="Janes", url="https://www.janes.com/defence-news/rss", lang="en", tier=3, category="military"),
    Feed(name="USNI News", url="https://news.usni.org/feed", lang="en", tier=3, category="military"),
    Feed(name="Task & Purpose", url="https://taskandpurpose.com/feed/", lang="en", tier=3, category="military"),
    Feed(name="Military Times", url="https://www.militarytimes.com/feed/rss/", lang="en", tier=3, category="military"),
    Feed(name="Oryx OSINT", url="https://www.oryxspioenkop.com/feed/", lang="en", tier=3, category="military"),
    Feed(name="gCaptain", url="https://gcaptain.com/feed/", lang="en", tier=3, category="military"),

    # ===== CYBER / 网络安全 =====
    Feed(name="Krebs Security", url="https://krebsonsecurity.com/feed/", lang="en", tier=3, category="cyber"),
    Feed(name="BleepingComputer", url="https://www.bleepingcomputer.com/feed/", lang="en", tier=3, category="cyber"),
    Feed(name="The Hacker News", url="https://feeds.feedburner.com/TheHackersNews", lang="en", tier=3, category="cyber"),
    Feed(name="Dark Reading", url="https://www.darkreading.com/rss.xml", lang="en", tier=3, category="cyber"),
    Feed(name="CyberScoop", url="https://cyberscoop.com/feed/", lang="en", tier=3, category="cyber"),
    Feed(name="Ransomware.live", url="https://www.ransomware.live/rss.xml", lang="en", tier=3, category="cyber"),
    Feed(name="Schneier", url="https://www.schneier.com/feed/atom/", lang="en", tier=3, category="cyber"),
    Feed(name="CISA", url="https://www.cisa.gov/news-events/cybersecurity-advisories/rss.xml", lang="en", tier=1, category="cyber"),

    # ===== TECH / 科技 =====
    Feed(name="TechCrunch", url="https://techcrunch.com/feed/", lang="en", tier=2, category="tech"),
    Feed(name="Wired", url="https://www.wired.com/feed/rss", lang="en", tier=2, category="tech"),
    Feed(name="MIT Tech Review", url="https://www.technologyreview.com/feed/", lang="en", tier=3, category="tech"),
    Feed(name="Ars Technica", url="https://feeds.arstechnica.com/arstechnica/index", lang="en", tier=3, category="tech"),
    Feed(name="The Verge", url="https://www.theverge.com/rss/index.xml", lang="en", tier=2, category="tech"),
    Feed(name="Engadget", url="https://www.engadget.com/rss.xml", lang="en", tier=2, category="tech"),
    Feed(name="OpenAI Blog", url="https://openai.com/blog/rss.xml", lang="en", tier=3, category="tech"),
    Feed(name="Anthropic", url="https://www.anthropic.com/feed/rss", lang="en", tier=3, category="tech"),
    Feed(name="Hugging Face", url="https://huggingface.co/blog/feed.xml", lang="en", tier=3, category="tech"),
    Feed(name="Hacker News", url="https://hnrss.org/frontpage", lang="en", tier=3, category="tech"),
    Feed(name="GitHub Blog", url="https://github.blog/feed/", lang="en", tier=3, category="tech"),
    Feed(name="Product Hunt", url="https://www.producthunt.com/feed", lang="en", tier=3, category="tech"),
    Feed(name="Y Combinator", url="https://www.ycombinator.com/news.rss", lang="en", tier=3, category="tech"),
    Feed(name="a16z", url="https://a16z.com/feed/", lang="en", tier=3, category="tech"),
    Feed(name="Sequoia", url="www.sequoiacap.com/insights", lang="en", tier=3, category="tech"),
    Feed(name="Stratechery", url="https://stratechery.com/feed/", lang="en", tier=3, category="tech"),
    Feed(name="Lenny's Newsletter", url="https://www.lennysnewsletter.com/feed", lang="en", tier=3, category="tech"),
    Feed(name="SemiAnalysis", url="https://www.semianalysis.com/feed", lang="en", tier=3, category="tech"),

    # ===== ECONOMY / 经济 =====
    Feed(name="CNBC", url="https://www.cnbc.com/id/100003114/device/rss/rss.html", lang="en", tier=2, category="finance"),
    Feed(name="MarketWatch", url="https://feeds.marketwatch.com/marketwatch/topstories/", lang="en", tier=2, category="finance"),
    Feed(name="Reuters Business", url="https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best", lang="en", tier=1, category="finance"),
    Feed(name="Economist", url="https://www.economist.com/rss", lang="en", tier=2, category="finance"),
    Feed(name="Financial Times Markets", url="https://www.ft.com/rss/markets", lang="en", tier=2, category="finance"),
    Feed(name="Yahoo Finance", url="https://finance.yahoo.com/rss/topstories", lang="en", tier=2, category="finance"),
    Feed(name="Seeking Alpha", url="https://seekingalpha.com/market_currents.xml", lang="en", tier=3, category="finance"),
    Feed(name="Federal Reserve", url="https://www.federalreserve.gov/feeds/press_all.xml", lang="en", tier=2, category="finance"),
    Feed(name="SEC", url="https://www.sec.gov/rss/news.rss", lang="en", tier=2, category="finance"),
    Feed(name="Layoffs.fyi", url="https://layoffs.fyi/rss/", lang="en", tier=3, category="finance"),

    # ===== SCIENCE / 科学 =====
    Feed(name="Nature", url="https://www.nature.com/nature.rss", lang="en", tier=2, category="science"),
    Feed(name="Science Daily", url="https://www.sciencedaily.com/rss/all.xml", lang="en", tier=3, category="science"),
    Feed(name="NASA", url="https://www.nasa.gov/rss/dyn/breaking_news.rss", lang="en", tier=2, category="science"),
    Feed(name="Space.com", url="https://www.space.com/feeds/all", lang="en", tier=3, category="science"),
    Feed(name="ArXiv", url="http://export.arxiv.org/api/query?search_query=cat:cs.*&max_results=20", lang="en", tier=3, category="science"),
    Feed(name="MIT News", url="https://news.mit.edu/rss/feed", lang="en", tier=2, category="science"),

    # ===== GOVERNMENT / 政府机构 =====
    Feed(name="White House", url="https://www.whitehouse.gov/feed/rss/", lang="en", tier=1, category="geopolitics"),
    Feed(name="State Dept", url="https://www.state.gov/rss/press-releases/", lang="en", tier=1, category="geopolitics"),
    Feed(name="UN News", url="https://news.un.org/feed/", lang="en", tier=1, category="geopolitics"),
    Feed(name="WHO", url="https://www.who.int/feeds/entity/news/en/rss.xml", lang="en", tier=1, category="science"),
    Feed(name="Treasury", url="https://home.treasury.gov/news/rss/press-releases", lang="en", tier=2, category="finance"),

    # ===== 中文源 =====
    # 新闻
    Feed(name="参考消息", url="https://www.cankaoxiaoxi.com/feed/", lang="zh", tier=2, category="china"),
    Feed(name="环球时报", url="https://global.huanqiu.com/rss/", lang="zh", tier=2, category="china"),
    Feed(name="观察者网", url="https://www.guancha.cn/news/rss.xml", lang="zh", tier=3, category="china"),
    Feed(name="澎湃新闻", url="https://m.thepaper.cn/rss_hotWords.xml", lang="zh", tier=3, category="china"),
    Feed(name="财新网", url="https://www.caixin.com/rss.xml", lang="zh", tier=3, category="china"),
    Feed(name="凤凰网", url="https://www.ifeng.com/rss", lang="zh", tier=3, category="china"),

    # ===== SOCIAL / 社交媒体热榜 (TrendRadar) =====
    # 这些通常需要特殊爬虫，RSS 可能已失效
    Feed(name="微博热搜", url="https://weibo.com/ajax/side/hotSearch", lang="zh", tier=2, category="social"),
    Feed(name="知乎热榜", url="https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total", lang="zh", tier=2, category="social"),
    Feed(name="百度热搜", url="https://top.baidu.com/board?tab=realtime", lang="zh", tier=2, category="social"),
    Feed(name="Bilibili热搜", url="https://api.bilibili.com/x/web-interface/popular", lang="zh", tier=2, category="social"),
    Feed(name="抖音热榜", url="https://www.douyin.com/aweme/v1/web/hot/search/", lang="zh", tier=2, category="social"),
    Feed(name="今日头条", url="https://www.toutiao.com/hot_event/", lang="zh", tier=2, category="social"),
    Feed(name="华尔街见闻", url="https://wallstreetcn.com/articles", lang="zh", tier=2, category="finance"),
    Feed(name="财联社", url="https://www.cls.cn/v1/rank", lang="zh", tier=2, category="finance"),

    # ===== 区域媒体 =====
    # 日本
    Feed(name="NHK", url="https://www3.nhk.or.jp/rss/news/cat0.xml", lang="ja", tier=2, category="geopolitics"),
    # 韩国
    Feed(name="Yonhap", url="https://www.yonhapnews.co.kr/rss/", lang="ko", tier=2, category="geopolitics"),
    # 俄罗斯
    Feed(name="Meduza", url="https://meduza.io/rss", lang="ru", tier=2, category="geopolitics"),
    # 印度
    Feed(name="The Hindu", url="https://www.thehindu.com/feeds/rss/", lang="en", tier=2, category="geopolitics"),
]


# ============================================================
# 分类映射
# ============================================================
CATEGORY_FEEDS: Dict[str, List[Feed]] = {
    # 世界政治
    "geopolitics": [
        Feed(name="Reuters", url="https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best", lang="en", tier=1),
        Feed(name="AP News", url="https://feeds.apnews.com/apnews/topnews", lang="en", tier=1),
        Feed(name="BBC World", url="http://feeds.bbci.co.uk/news/world/rss.xml", lang="en", tier=2),
        Feed(name="Al Jazeera", url="https://www.aljazeera.com/xml/rss/all.xml", lang="en", tier=2),
        Feed(name="Foreign Policy", url="https://foreignpolicy.com/feed/", lang="en", tier=3),
    ],

    # 军事
    "military": [
        Feed(name="Defense One", url="https://www.defenseone.com/feed/", lang="en", tier=3),
        Feed(name="Breaking Defense", url="https://breakingdefense.com/feed/", lang="en", tier=3),
        Feed(name="Janes", url="https://www.janes.com/defence-news/rss", lang="en", tier=3),
        Feed(name="Oryx OSINT", url="https://www.oryxspioenkop.com/feed/", lang="en", tier=3),
    ],

    # 网络安全
    "cyber": [
        Feed(name="Krebs Security", url="https://krebsonsecurity.com/feed/", lang="en", tier=3),
        Feed(name="The Hacker News", url="https://feeds.feedburner.com/TheHackersNews", lang="en", tier=3),
        Feed(name="BleepingComputer", url="https://www.bleepingcomputer.com/feed/", lang="en", tier=3),
    ],

    # 科技
    "tech": [
        Feed(name="TechCrunch", url="https://techcrunch.com/feed/", lang="en", tier=2),
        Feed(name="Wired", url="https://www.wired.com/feed/rss", lang="en", tier=2),
        Feed(name="Hacker News", url="https://hnrss.org/frontpage", lang="en", tier=3),
        Feed(name="OpenAI Blog", url="https://openai.com/blog/rss.xml", lang="en", tier=3),
    ],

    # 经济
    "finance": [
        Feed(name="CNBC", url="https://www.cnbc.com/id/100003114/device/rss/rss.html", lang="en", tier=2),
        Feed(name="MarketWatch", url="https://feeds.marketwatch.com/marketwatch/topstories/", lang="en", tier=2),
        Feed(name="Yahoo Finance", url="https://finance.yahoo.com/rss/topstories", lang="en", tier=2),
        Feed(name="Reuters Business", url="https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best", lang="en", tier=1),
    ],

    # 科学
    "science": [
        Feed(name="Nature", url="https://www.nature.com/nature.rss", lang="en", tier=2),
        Feed(name="NASA", url="https://www.nasa.gov/rss/dyn/breaking_news.rss", lang="en", tier=2),
        Feed(name="MIT News", url="https://news.mit.edu/rss/feed", lang="en", tier=2),
    ],

    # 中国
    "china": [
        Feed(name="参考消息", url="https://www.cankaoxiaoxi.com/feed/", lang="zh", tier=2),
        Feed(name="观察者网", url="https://www.guancha.cn/news/rss.xml", lang="zh", tier=3),
        Feed(name="澎湃新闻", url="https://m.thepaper.cn/rss_hotWords.xml", lang="zh", tier=3),
    ],

    # 社交媒体热榜
    "social": [
        Feed(name="微博热搜", url="https://weibo.com/ajax/side/hotSearch", lang="zh", tier=2),
        Feed(name="知乎热榜", url="https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total", lang="zh", tier=2),
        Feed(name="百度热搜", url="https://top.baidu.com/board?tab=realtime", lang="zh", tier=2),
    ],
}


# ============================================================
# 便捷函数
# ============================================================

def get_feeds_by_category(category: str, lang: Optional[str] = None) -> List[Feed]:
    """获取指定分类的 RSS 源"""
    feeds = CATEGORY_FEEDS.get(category, [])
    if lang:
        feeds = [f for f in feeds if f.lang == lang or f.lang is None]
    return feeds


def get_all_feeds(lang: Optional[str] = None, tier: Optional[int] = None) -> List[Feed]:
    """获取所有 RSS 源"""
    feeds = RSS_FEEDS.copy()
    if lang:
        feeds = [f for f in feeds if f.lang == lang or f.lang is None]
    if tier:
        feeds = [f for f in feeds if f.tier <= tier]
    return feeds


def get_feed_by_name(name: str) -> Optional[Feed]:
    """通过名称获取 RSS 源"""
    for feed in RSS_FEEDS:
        if feed.name == name:
            return feed
    return None


def get_tier_name(tier: int) -> str:
    """获取层级名称"""
    names = {
        1: "Wire Services",
        2: "Major Media",
        3: "Specialty",
        4: "Aggregator"
    }
    return names.get(tier, "Unknown")


def create_feeds_config(
    categories: Optional[List[str]] = None,
    lang: str = "en",
    max_tier: int = 2
) -> List[Feed]:
    """创建 RSS 源配置

    Args:
        categories: 分类列表 (None = 所有)
        lang: 语言
        max_tier: 最大信任层级

    Returns:
        RSS 源列表
    """
    if categories:
        feeds = []
        for cat in categories:
            feeds.extend(get_feeds_by_category(cat, lang))
    else:
        feeds = get_all_feeds(lang, max_tier)

    return feeds


def get_stats() -> dict:
    """获取 RSS 源统计"""
    stats = {
        "total": len(RSS_FEEDS),
        "by_category": {},
        "by_tier": {1: 0, 2: 0, 3: 0, 4: 0},
        "by_lang": {},
    }

    for feed in RSS_FEEDS:
        # 按分类统计
        if feed.category:
            stats["by_category"][feed.category] = stats["by_category"].get(feed.category, 0) + 1

        # 按层级统计
        stats["by_tier"][feed.tier] = stats["by_tier"].get(feed.tier, 0) + 1

        # 按语言统计
        lang = feed.lang or "unknown"
        stats["by_lang"][lang] = stats["by_lang"].get(lang, 0) + 1

    return stats

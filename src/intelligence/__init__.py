# coding=utf-8
"""
Intelligence Module - 情报获取与分析

基于 TrendRadar 的核心组件重构:
- DataFetcher: 新闻数据获取
- AIAnalyzer: AI 深度分析
- NotificationDispatcher: 多渠道推送

设计参考:
- TrendRadar: 热点新闻聚合与分析
- Microsoft Azure: 情报评分系统
- WorldMonitor: 全球情报聚合 (https://github.com/koala73/worldmonitor)
"""
from .fetcher import IntelligenceFetcher
from .analyzer import IntelligenceAnalyzer
from .scorer import IntelligenceScorer, UserProfile
from .pipeline import IntelligencePipeline, PipelineConfig
from .pusher import IntelligencePusher, PushFeedbackTracker, PushRecord
from .rss_fetcher import RSSFetcher, RSSNewsItem
from .threat_classifier import (
    ThreatClassification,
    ThreatLevel,
    EventCategory,
    classify_by_keyword,
    aggregate_threats,
)
from .feeds_config import Feed, RSS_FEEDS, CATEGORY_FEEDS, get_feeds_by_category
from .worldmonitor_adapter import (
    WorldMonitorAdapter,
    WorldMonitorConfig,
    WorldMonitorNewsItem,
    WorldMonitorCategory,
    ThreatLevel as WMThreatLevel,
    create_worldmonitor_adapter,
)
from .github_trending import GitHubTrendingFetcher, GitHubTrendingItem
from .readme_fetcher import (
    ReadmeFetcher,
    ReadmeSummarizer,
    GitHubRepoInfo,
    create_readme_fetcher,
    create_readme_summarizer,
)
from .summarize_client import (
    SummarizeClient,
    SummarizeLength,
    create_summarize_client,
)
# 分级分类信息获取
from .classifier import (
    InformationClassifier,
    InfoCategory,
    ClassificationResult,
    get_classifier,
)
from .hot_fetcher import (
    HotFetcher,
    HackerNewsFetcher,
    GitHubTrendingFetcher,
    ProductHuntFetcher,
    WeiboHotFetcher,
    HotItem,
    create_hot_fetcher,
)
from .academic_fetcher import (
    AcademicFetcher,
    ArxivFetcher,
    PubMedFetcher,
    HuggingFaceFetcher,
    AcademicPaper,
    create_academic_fetcher,
    create_huggingface_fetcher,
)
from .intake import (
    InformationIntake,
    IntelligenceItem,
    get_information_intake,
)

__all__ = [
    # Core
    "IntelligenceFetcher",
    "IntelligenceAnalyzer",
    "IntelligenceScorer",
    "UserProfile",
    "IntelligencePipeline",
    "PipelineConfig",
    "IntelligencePusher",
    "PushFeedbackTracker",
    "PushRecord",
    # RSS Fetcher (WorldMonitor-style)
    "RSSFetcher",
    "RSSNewsItem",
    # Threat Classifier
    "ThreatClassification",
    "ThreatLevel",
    "EventCategory",
    "classify_by_keyword",
    "aggregate_threats",
    # Feeds Config
    "Feed",
    "RSS_FEEDS",
    "CATEGORY_FEEDS",
    "get_feeds_by_category",
    # WorldMonitor
    "WorldMonitorAdapter",
    "WorldMonitorConfig",
    "WorldMonitorNewsItem",
    "WorldMonitorCategory",
    "create_worldmonitor_adapter",
    # GitHub Trending
    "GitHubTrendingFetcher",
    "GitHubTrendingItem",
    # README Fetcher
    "ReadmeFetcher",
    "ReadmeSummarizer",
    "GitHubRepoInfo",
    "create_readme_fetcher",
    "create_readme_summarizer",
    # Summarize CLI
    "SummarizeClient",
    "SummarizeLength",
    "create_summarize_client",
    # 分级分类信息获取
    "InformationClassifier",
    "InfoCategory",
    "ClassificationResult",
    "get_classifier",
    "HotFetcher",
    "HackerNewsFetcher",
    "GitHubTrendingFetcher",
    "ProductHuntFetcher",
    "WeiboHotFetcher",
    "HotItem",
    "create_hot_fetcher",
    "AcademicFetcher",
    "ArxivFetcher",
    "PubMedFetcher",
    "HuggingFaceFetcher",
    "AcademicPaper",
    "create_huggingface_fetcher",
    "create_academic_fetcher",
    "InformationIntake",
    "IntelligenceItem",
    "get_information_intake",
]

# WorldMonitor Integration Plan

## Overview
Integrate WorldMonitor's RSS fetching and threat classification into message-integrate-agent to enrich intelligence gathering with global news sources.

## Components Integrated

### 1. RSS Feed Fetcher (src/intelligence/rss_fetcher.py)
- **Source**: WorldMonitor's `src/services/rss.ts`
- **Features**:
  - 40+ curated RSS feeds
  - In-memory caching with TTL
  - Failure cooldown mechanism
  - Parallel batch fetching
  - Image extraction from RSS
  - Threat classification integration

### 2. Threat Classifier (src/intelligence/threat_classifier.py)
- **Source**: WorldMonitor's `src/services/threat-classifier.ts`
- **Features**:
  - Keyword-based threat classification
  - 5 threat levels: critical, high, medium, low, info
  - 14 event categories: conflict, protest, disaster, etc.
  - Compound escalation detection

### 3. Feed Configuration (src/intelligence/feeds_config.py)
- **Source**: WorldMonitor's `src/config/feeds.ts`
- **Features**:
  - 40+ RSS sources with tier system
  - Multi-language support (en, zh)
  - Category-based filtering

## Implementation Phases

### Phase 1: Core Infrastructure ✅
- [x] Create threat classifier module
- [x] Create feeds configuration
- [x] Create RSS fetcher with WorldMonitor-style features

### Phase 2: Integration ✅
- [x] Integrate into IntelligencePipeline
- [ ] Add to Heartbeat Engine (config only)
- [x] Configure categories

### Phase 3: Testing ✅
- [x] Test RSS fetching
- [x] Test threat classification
- [x] Test full pipeline

## Test Results

```
📥 获取: 100 条 (国内 50 + RSS 50)
📝 分析: 100 条
📊 评分: 67 条通过阈值
📤 推送: 1 个渠道
⚠️ Alert items: 10 (威胁告警)
```

## RSS Sources (Current)

| Category | Sources |
|----------|---------|
| geopolitics | Reuters, BBC World, Al Jazeera |
| military | Breaking Defense, Janes |
| cyber | Krebs Security, The Hacker News |
| tech | TechCrunch, Wired |
| economy | CNBC, MarketWatch |
| science | Nature, NASA |

## Configuration

The pipeline now supports:

```python
config = PipelineConfig(
    # 国内平台
    platforms=["weibo", "zhihu", "bilibili"],

    # RSS 配置 (新增)
    rss_enabled=True,
    rss_categories=["geopolitics", "military", "tech"],
    rss_lang="en",
    rss_max_tier=2,  # 1=通讯社, 2=主流媒体

    # WorldMonitor (可选,需要自托管)
    worldmonitor_enabled=False,
)
```

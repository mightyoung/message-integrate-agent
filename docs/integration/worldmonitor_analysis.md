# WorldMonitor 集成分析报告

## 1. WorldMonitor 项目概述

**项目地址**: https://github.com/koala73/worldmonitor

**核心定位**: Real-time global intelligence dashboard - AI驱动的全球情报聚合平台

### 主要特性

| 特性 | 说明 |
|------|------|
| 数据源 | 435+ RSS feeds, 15个类别 |
| 变体 | World, Tech, Finance, Commodity, Happy 5个版本 |
| AI能力 | 本地Ollama/Groq/OpenRouter 多提供商摘要 |
| 可视化 | 3D地球 + 2D地图, 45个可切换数据层 |
| 语言 | 21种语言支持 |
| 部署 | Web (Vercel) + 桌面端 (Tauri) |

---

## 2. 现有 Intelligence 模块对比

### message-integrate-agent 当前能力

```
IntelligencePipeline:
├── fetch_data()      → IntelligenceFetcher (简单RSS)
├── analyze()         → IntelligenceAnalyzer (LLM分析)
├── score()          → IntelligenceScorer (多维度评分)
└── push()           → IntelligencePusher (多渠道推送)
```

**局限性**:
- 数据源有限 (微博/知乎/B站)
- 无地理编码
- 无威胁分类
- 无多源融合

### WorldMonitor 核心能力

| 模块 | WorldMonitor 能力 |
|------|------------------|
| **RSS聚合** | 435+ 精选源, 智能分类, 失败冷却 |
| **威胁分类** | 关键词 + AI 双重分类 |
| **地理编码** | 自动推断地点, 坐标匹配 |
| **AI摘要** | 多提供商级联 (Ollama→Groq→OpenRouter) |
| **数据层** | 军事/冲突/基础设施/气象等45层 |

---

## 3. 集成必要性分析

### ✅ 需要集成的理由

1. **数据源扩展**
   - 现有: 3个中文平台
   - WorldMonitor: 435+ 全球源 (路透/BBC/彭博等)
   - 覆盖: 地缘政治, 军事, 经济, 科技

2. **质量提升**
   - 现有: 简单关键词匹配
   - WorldMonitor: 威胁等级分类 + 地理编码

3. **AI能力增强**
   - 现有: 仅摘要
   - WorldMonitor: 推理预测 + 焦点检测

4. **行业最佳实践**
   - 多源情报融合是OSINT标准做法
   - 参考: Palantir, Jane's, Stratfor

### ⚠️ 集成挑战

1. **技术栈差异**
   - WorldMonitor: TypeScript/Next.js/Tauri
   - 本项目: Python/FastAPI

2. **部署复杂度**
   - WorldMonitor 需要 Vercel + Redis + 多个API密钥
   - 本项目: 轻量级 Python 服务

3. **资源需求**
   - WorldMonitor: 大量边缘计算
   - 本项目: 资源受限环境

---

## 4. 集成方案

### 方案A: API 集成 (推荐)

```
┌─────────────────────────────────────────────────────────────┐
│                    WorldMonitor API                         │
│  (部署为外部服务或 worldmonitor.app API)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              IntelligenceFetcher (改造)                     │
│  - 新增 worldmonitor adapter                              │
│  - 调用 WorldMonitor News API                            │
│  - 转换 WorldMonitor NewsItem → 本地格式                  │
└─────────────────────────────────────────────────────────────┘
```

**优点**:
- 最小改造
- 可复用 WorldMonitor 全部数据
- 可选择部署或使用官方API

**需要**:
- WorldMonitor 部署 (或使用官方API如果有)
- API 密钥配置

### 方案B: 数据源复用

```
┌─────────────────────────────────────────────────────────────┐
│              直接集成 WorldMonitor 源码                     │
│  - 复制 rss.ts 服务逻辑                                   │
│  - 适配 Python                                           │
│  - 使用 feeds.ts 配置                                      │
└─────────────────────────────────────────────────────────────┘
```

**优点**:
- 自主可控
- 无需外部依赖

**缺点**:
- 代码移植工作量大
- 需要持续同步更新

### 方案C: A2A 协议集成

```
┌─────────────────────────────────────────────────────────────┐
│              WorldMonitor 作为 A2A Agent                   │
│  - WorldMonitor 暴露 A2A Server                           │
│  - message-integrate-agent 作为 A2A Client                │
│  - 任务: "获取最新地缘政治新闻"                           │
└─────────────────────────────────────────────────────────────┘
```

**优点**:
- 标准化接口
- 松耦合

**缺点**:
- 需要 WorldMonitor 支持 A2A (当前不支持)

---

## 5. 推荐集成计划

### Phase 1: API 适配器 (Task #69)

创建 WorldMonitor 数据适配器:

```python
# src/intelligence/worldmonitor_adapter.py

class WorldMonitorAdapter:
    """WorldMonitor 数据适配器"""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key

    async def fetch_news(
        self,
        category: str = "geopolitics",
        limit: int = 50
    ) -> List[NewsItem]:
        """获取新闻"""
        # 调用 WorldMonitor API
        # 转换格式
        pass

    async def fetch_summary(
        self,
        headlines: List[str]
    ) -> str:
        """获取AI摘要"""
        pass
```

### Phase 2: 集成到 IntelligencePipeline (Task #70)

修改 `src/intelligence/pipeline.py`:

```python
async def _fetch_intelligence(self):
    # 原有来源
    items = await self.fetcher.fetch_data()

    # WorldMonitor 来源 (新增)
    wm_items = await self.worldmonitor_adapter.fetch_news()
    items.extend(wm_items)

    return items
```

### Phase 3: 配置扩展 (Task #71)

在 `config.py` 中添加:

```python
class WorldMonitorConfig:
    api_url: str = "https://api.worldmonitor.app"
    api_key: str = ""
    categories: List[str] = ["geopolitics", "military", "economy"]
```

---

## 6. 实施优先级

| 优先级 | 任务 | 工作量 | 价值 |
|--------|------|--------|------|
| P0 | 创建 WorldMonitorAdapter | 2h | 高 |
| P1 | 集成到 IntelligencePipeline | 1h | 高 |
| P2 | 添加威胁分类映射 | 2h | 中 |
| P3 | 添加 AI 摘要能力 | 3h | 中 |

---

## 7. 结论

**建议集成**, 理由:

1. **数据价值高**: 435+ 优质全球源, 覆盖现有盲区
2. **技术可行**: API 适配器模式, 改动可控
3. **行业标准**: 多源情报融合是OSINT最佳实践
4. **互补性强**: 现有中文源 + WorldMonitor 全球源

**推荐方案**: 方案A (API集成) - 最快实现价值

是否继续执行集成计划?

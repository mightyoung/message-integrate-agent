# Firecrawl 集成设计方案

## 一、Firecrawl 核心功能分析

### 1.1 Firecrawl 是什么
Firecrawl 是一个将网站转换为 LLM 可用数据的 API 服务，主要功能包括：

| 功能 | 描述 |
|------|------|
| **网页抓取 (Scrape)** | 从单个 URL 提取结构化数据 |
| **网站爬取 (Crawl)** | 爬取整个网站，提取所有页面 |
| **搜索 (Search)** | 基于关键词搜索网页 |
| **Markdown 转换** | 将网页内容转换为干净的 Markdown |
| **结构化提取** | 支持 JSON 模式定义输出格式 |
| **动态内容** | 处理 JavaScript 渲染的页面 |
| **批处理** | 异步批量抓取数千个 URL |
| **变化追踪** | 监控网站内容变化 |

### 1.2 关键 API 方法
```python
from firecrawl import Firecrawl

# 同步客户端
client = Firecrawl(api_key="fc-xxx")

# 抓取单个页面
result = client.scrape_url(
    url="https://example.com",
    formats=["markdown", "html", "text"]
)

# 爬取整个网站
crawl_result = client.crawl_url(
    url="https://example.com",
    limit=100
)

# 搜索
search_result = client.search(
    query="AI news 2024",
    limit=10
)

# 批量抓取
batch_result = client.batch_scrape(
    urls=["url1", "url2", "url3"],
    formats=["markdown"]
)
```

### 1.3 部署方式
- **云服务**: 直接使用 firecrawl.dev API
- **自托管**: 通过 Docker Compose 部署（需要 Redis、RabbitMQ、PostgreSQL）

---

## 二、集成价值分析

### 2.1 当前系统能力
| 组件 | 功能 |
|------|------|
| IntelligenceFetcher | 获取国内平台热点（微博、知乎、B站） |
| RSSFetcher | 获取全球 RSS 源（TechCrunch、Wired 等） |
| IntelligenceAnalyzer | AI 分析（LLM 摘要、分类） |
| IntelligenceScorer | 用户匹配评分 |
| IntelligencePusher | 推送到飞书 |

### 2.2 集成后的能力提升
| 场景 | 当前能力 | 集成后能力 |
|------|----------|------------|
| 新闻详情 | 只获取标题和简介 | 获取完整文章内容 |
| 深度分析 | 基于摘要分析 | 基于全文分析 |
| 特定网站抓取 | 依赖 RSS | 直接抓取任意网站 |
| 结构化数据 | 无 | 支持 JSON Schema 提取 |

### 2.3 顶级专家的集成思维
参考彭博社、路透社等顶级新闻机构的 AI 数据架构：

1. **数据分层架构**
   - Layer 1: 快速获取（RSS、API）→  headlines
   - Layer 2: 深度抓取（Firecrawl）→  full content
   - Layer 3: 智能分析（LLM）→  insights

2. **按需抓取策略**
   - 只对高价值 URL 进行深度抓取
   - 使用缓存避免重复抓取
   - 异步批量处理

3. **质量控制**
   - 验证抓取结果完整性
   - 错误重试机制
   - 成本控制（API 配额）

---

## 三、集成设计方案

### 3.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Intelligence Pipeline                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │   Fetcher   │───▶│   Analyzer  │───▶│   Pusher    │   │
│  └─────────────┘    └─────────────┘    └─────────────┘   │
│         │                  │                                 │
│         ▼                  ▼                                 │
│  ┌─────────────────────────────────────────────┐          │
│  │           Firecrawl Adapter                   │          │
│  │  • 链接扩展  • 内容抓取  • 结构化提取       │          │
│  └─────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 核心组件设计

#### 组件 1: FirecrawlAdapter
```python
# src/intelligence/firecrawl_adapter.py

class FirecrawlAdapter:
    """Firecrawl 适配器"""

    def __init__(self, api_key: str = None, api_url: str = None):
        self.client = Firecrawl(api_key=api_key, api_url=api_url)
        self.cache = {}  # URL -> content 缓存

    async def scrape_url(
        self,
        url: str,
        formats: List[str] = ["markdown"],
        only_main_content: bool = True
    ) -> Optional[Dict]:
        """抓取单个 URL"""

    async def scrape_urls(
        self,
        urls: List[str],
        formats: List[str] = ["markdown"]
    ) -> List[Dict]:
        """批量抓取 URL"""

    async def expand_intelligence(
        self,
        news_items: List[NewsItem]
    ) -> List[NewsItem]:
        """扩展情报内容"""
        # 1. 提取需要抓取的 URLs
        # 2. 批量抓取
        # 3. 合并内容到 NewsItem
        # 4. 返回扩展后的列表
```

#### 组件 2: 集成到 Pipeline
```python
# src/intelligence/pipeline.py 新增配置

class PipelineConfig:
    # ... existing config ...

    # Firecrawl 配置
    firecrawl_enabled: bool = False
    firecrawl_api_key: Optional[str] = None
    firecrawl_api_url: str = "https://api.firecrawl.dev"
    firecrawl_max_urls_per_batch: int = 10
    firecrawl_expand_content: bool = True  # 是否扩展内容

# 在 _fetch_intelligence 中添加
async def _expand_with_firecrawl(self, news_items):
    if not self.config.firecrawl_enabled:
        return news_items

    adapter = FirecrawlAdapter(
        api_key=self.config.firecrawl_api_key,
        api_url=self.config.firecrawl_api_url,
    )

    return await adapter.expand_intelligence(news_items)
```

### 3.3 数据流设计

```
原始新闻 (title + url)
        │
        ▼
┌───────────────────┐
│  评估抓取价值      │  ← 基于评分/分类/用户兴趣
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Firecrawl 抓取   │  ← 批量异步抓取
│  (Markdown 格式)  │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  内容整合          │  ← 合并到 NewsItem
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  现有 Pipeline     │  ← 分析→评分→推送
└───────────────────┘
```

### 3.4 配置设计

```yaml
# config/settings.yaml

intelligence:
  firecrawl:
    enabled: true
    api_key: ${FIRECRAWL_API_KEY}  # 从环境变量读取
    api_url: https://api.firecrawl.dev
    max_urls_per_batch: 10
    expand_content: true
    only_main_content: true  # 只抓取主要内容
    formats:
      - markdown
      - html
    timeout: 30
    retry: 3
```

---

## 四、实施步骤

### Phase 1: 基础集成
1. 创建 `FirecrawlAdapter` 类
2. 实现 `scrape_url` 和 `scrape_urls` 方法
3. 添加单元测试

### Phase 2: Pipeline 集成
1. 在 `PipelineConfig` 中添加 Firecrawl 配置
2. 在 `_fetch_intelligence` 中调用扩展方法
3. 添加错误处理和重试机制

### Phase 3: 优化
1. 实现 URL 缓存（避免重复抓取）
2. 添加成本控制（API 配额监控）
3. 实现增量抓取（只抓取新 URL）

---

## 五、注意事项

### 5.1 成本控制
- Firecrawl API 按调用次数计费
- 建议：只对高价值情报进行深度抓取
- 建议：使用缓存减少重复抓取

### 5.2 错误处理
- 网络超时重试
- 反爬虫应对
- 内容解析失败降级

### 5.3 隐私合规
- 遵守目标网站 robots.txt
- 合理设置抓取频率
- 不抓取敏感信息

---

## 六、配置示例

```bash
# .env.prod
FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxxxxxxxxxxxxxx  # 云服务 API Key
```

---

## 七、总结

| 方面 | 说明 |
|------|------|
| **集成方式** | 在 IntelligencePipeline 中新增 Firecrawl 扩展层 |
| **核心价值** | 将新闻标题扩展为完整文章内容 |
| **实施难度** | 中等（需要理解现有 Pipeline 结构） |
| **成本影响** | 按需调用，云服务按次计费 |
| **性能影响** | 异步批量抓取，影响较小 |

**当前配置**: 使用 Firecrawl 云服务 (API Key: fc-xxxxx...)

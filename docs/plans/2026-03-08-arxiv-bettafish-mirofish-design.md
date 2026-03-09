# ArXiv 论文源增强 + BettaFish/MiroFish 集成设计方案

## 背景

1. **ArXiv 论文源增强**：添加 AI/ML 分类论文，获取后进行翻译和总结
2. **BettaFish + MiroFish 集成**：作为独立容器集成舆情爬虫和预测引擎

---

## Part 1: ArXiv 论文源增强

### 1.1 技术方案

**ArXiv API**：
- 基础 URL: `http://export.arxiv.org/api/query`
- 查询参数: `search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.CV`
- 返回格式: Atom XML

**论文处理流程**：
```
ArXiv API → 获取论文列表 → 提取标题/摘要 → LLM翻译 → LLM总结 → 推送
```

### 1.2 分类配置

```python
ARXIV_CATEGORIES = {
    "cs.AI": "Artificial Intelligence",
    "cs.LG": "Machine Learning",
    "cs.CL": "Computation and Language",
    "cs.CV": "Computer Vision",
    "cs.NE": "Neural and Evolutionary Computing",
}
```

### 1.3 实现

**新增 ArXivFetcher**：
```python
class ArxivFetcher:
    def __init__(self, categories: List[str], max_results: int = 20):
        self.categories = categories
        self.max_results = max_results

    def fetch(self) -> List[ArxivPaper]:
        # 调用 ArXiv API
        # 解析 Atom XML
        pass
```

**新增 ArxivProcessor**：
```python
class ArxivProcessor:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def process(self, paper: ArxivPaper) -> ProcessedPaper:
        # 1. 翻译标题
        translated_title = await self.llm.translate(paper.title, "zh")

        # 2. 总结摘要
        summary = await self.llm.summarize(paper.abstract)

        return ProcessedPaper(
            original_title=paper.title,
            translated_title=translated_title,
            summary=summary,
            url=paper.url,
            authors=paper.authors,
            published=paper.published,
        )
```

---

## Part 2: BettaFish + MiroFish 集成

### 2.1 可行性分析

| 项目 | Stars | 功能 | 架构 | 集成难度 |
|------|-------|------|------|----------|
| BettaFish | - | 舆情爬虫 + 多智能体分析 | Python + Flask | ⭐⭐⭐ |
| MiroFish | 6.6k | 预测引擎 + 群体仿真 | Python + Vue | ⭐⭐ |

### 2.2 BettaFish 架构

```
BettaFish/
├── QueryEngine/      # 搜索Agent
├── MediaEngine/     # 内容分析Agent
├── InsightEngine/   # 数据挖掘Agent
├── ReportEngine/   # 报告生成Agent
├── ForumEngine/    # Agent协作
├── MindSpider/     # 爬虫系统
└── SentimentAnalysisModel/
```

**集成方式**：
- 作为独立 Docker 容器运行
- 提供 REST API 供 message-hub 调用
- 通过 Docker Network 连接

### 2.3 MiroFish 架构

```
MiroFish/
├── OASIS/           # 仿真引擎 (CAMEL-AI)
├── GraphRAG/        # 知识图谱
├── ReportAgent/     # 预测报告
└── Frontend/       # Vue 前端
```

**集成方式**：
- 作为独立 Docker 容器运行
- 提供预测 API
- 支持舆情推演、预测报告生成

### 2.4 集成架构

```yaml
# docker-compose.yml 扩展
services:
  # 现有服务
  gateway:
    # ...

  # 新增服务
  bettafish:
    image: bettafish:latest
    build: ./bettafish
    ports:
      - "5000:5000"
    networks:
      - message-hub-net
    environment:
      - LLM_API_KEY=${OPENAI_API_KEY}
      - LLM_BASE_URL=${OPENAI_BASE_URL}

  mirofish:
    image: mirofish:latest
    build: ./mirofish
    ports:
      - "5001:5001"
      - "3000:3000"  # 前端
    networks:
      - message-hub-net
    environment:
      - LLM_API_KEY=${OPENAI_API_KEY}
      - LLM_BASE_URL=${OPENAI_BASE_URL}
```

### 2.5 API 对接

**BettaFish API**：
- `POST /api/analyze` - 舆情分析
- `GET /api/search` - 搜索
- `POST /api/report` - 生成报告

**MiroFish API**：
- `POST /api/simulate` - 启动仿真
- `GET /api/prediction/{id}` - 获取预测结果
- `POST /api/report` - 生成预测报告

---

## 实现计划

### Phase 1: ArXiv 论文增强
- [ ] 更新 ArXiv RSS 源 URL
- [ ] 创建 ArxivFetcher 类
- [ ] 创建 ArxivProcessor 类（翻译+总结）
- [ ] 集成到 Intelligence Pipeline

### Phase 2: BettaFish 集成
- [ ] 创建 BettaFish Dockerfile
- [ ] 配置 docker-compose
- [ ] 实现 API 调用封装
- [ ] 集成到消息推送

### Phase 3: MiroFish 集成
- [ ] 创建 MiroFish Dockerfile
- [ ] 配置 docker-compose
- [ ] 实现 API 调用封装
- [ ] 集成预测功能

---

## 依赖

### 新增 Python 依赖
```txt
feedparser>=6.0.0  # RSS/Atom 解析
```

### 外部服务
- BettaFish (独立容器)
- MiroFish (独立容器)
- LLM (DeepSeek/OpenAI)

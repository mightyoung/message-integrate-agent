# 完整用户交互流程设计方案

**日期**: 2026-03-10
**版本**: v1.0
**状态**: 已批准

---

## 1. 背景与目标

### 1.1 项目现状

- **菜单系统**: 已实现 FeishuMenuHandler，支持14个菜单项
- **意图识别**: KeywordRouter + AIRouter 双轨制
- **消息处理**: MessagePipeline 快速路径/深度处理
- **情报采集**: IntelligencePipeline 完整的数据采集→存储→分析

### 1.2 设计目标

实现从用户触发到收到结果的完整闭环：
1. 支持菜单点击触发
2. 支持消息文本触发
3. 完整的情报采集→处理→推送流程
4. 控制台模拟输出

---

## 2. 用户旅程设计

### 2.1 完整流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            用户交互完整流程                                   │
└─────────────────────────────────────────────────────────────────────────────┘

用户操作                          系统处理                              用户感知
────────────────────────────────────────────────────────────────────────────

  ┌─────────────────┐
  │ 用户点击菜单     │           1. 事件接收
  │ 或发送消息      │──────────> 2. 事件解析
  └─────────────────┘           3. 意图识别
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │      意图识别层               │
                    │  ┌─────┐ ┌────────┐ ┌────┐ │
                    │  │Menu │ │Keyword │ │AI  │ │
                    │  │100% │ │  High  │ │Low │ │
                    │  └──┬──┘ └────┬───┘ └──┬─┘ │
                    └──────┼─────────┼────────┼────┘
                           │         │        │
                           ▼         ▼        ▼
                    ┌─────────────────────────────────┐
                    │       任务执行层                 │
                    │  ┌───────────────────────────┐  │
                    │  │   IntelligencePipeline   │  │
                    │  │  ① 数据采集 (RSS/HN/GitHub)│  │
                    │  │  ② 去重处理 (Redis)        │  │
                    │  │  ③ AI分析 (LLM fallback)   │  │
                    │  │  ④ 存储 (PG + S3)         │  │
                    │  └───────────────────────────┘  │
                    └─────────────┬───────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────────┐
                    │       响应格式化层               │
                    │  ┌───────────────────────────┐  │
                    │  │  Markdown / 卡片 / 文本   │  │
                    │  └───────────────────────────┘  │
                    └─────────────┬───────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────────┐
                    │       平台适配层                 │
                    │  ┌───────────────────────────┐  │
                    │  │ FeishuAdapter (模拟输出)  │  │
                    │  └───────────────────────────┘  │
                    └─────────────────────────────────┘

                                  │
                                  ▼
                          ┌───────────────┐
                          │ 用户收到消息   │ <── 控制台模拟输出
                          └───────────────┘
```

---

## 3. 核心组件设计

### 3.1 UnifiedMessageHandler - 统一消息处理器

```python
class UnifiedMessageHandler:
    """统一消息处理器

    整合菜单事件和消息事件到一个入口
    """

    def __init__(self):
        self.menu_handler = FeishuMenuHandler()
        self.keyword_router = KeywordRouter()
        self.ai_router = AIRouter()
        self.pipeline = MessagePipeline()
        self.intelligence_pipeline = IntelligencePipeline()

    async def handle(self, event: Dict) -> str:
        """统一处理入口

        Args:
            event: 事件字典 (menu/message/webhook)

        Returns:
            处理结果
        """
        # 1. 事件类型判断
        event_type = self._get_event_type(event)

        if event_type == "menu":
            return await self._handle_menu(event)
        elif event_type == "message":
            return await self._handle_message(event)
        else:
            return await self._handle_webhook(event)

    async def _handle_menu(self, event: Dict) -> str:
        """处理菜单事件"""
        # 1. 解析菜单事件
        intent_result = await self.menu_handler.handle_menu_event(event)

        # 2. 执行任务
        return await self._execute_intent(intent_result)

    async def _handle_message(self, event: Dict) -> str:
        """处理消息事件"""
        # 1. 解析消息
        message = self._parse_message(event)

        # 2. 意图识别
        intent_result = await self._recognize_intent(message)

        # 3. 执行任务
        return await self._execute_intent(intent_result)
```

### 3.2 意图识别策略

| 优先级 | 来源 | 置信度 | 适用场景 |
|-------|------|--------|---------|
| 1 | Menu | 100% | 用户点击菜单 |
| 2 | Keyword | 90% | 明确关键词匹配 |
| 3 | AI | 70% | 复杂语义理解 |

### 3.3 任务执行器

```python
class TaskExecutor:
    """任务执行器

    根据意图执行相应任务
    """

    async def execute(self, intent_result: IntentResult) -> str:
        """执行任务

        Args:
            intent_result: 意图识别结果

        Returns:
            执行结果 (Markdown格式)
        """
        # 1. 根据agent选择执行器
        if intent_result.agent == "intelligence":
            return await self._execute_intelligence(intent_result)
        elif intent_result.agent == "search":
            return await self._execute_search(intent_result)
        elif intent_result.agent == "system":
            return await self._execute_system(intent_result)
        else:
            return await self._execute_default(intent_result)

    async def _execute_intelligence(self, intent_result: IntentResult) -> str:
        """执行情报任务"""

        # 1. 采集情报
        config = PipelineConfig(
            rss_categories=[intent_result.params.get("category", "tech")],
            rss_lang="zh" if "hot" in intent_result.params else "en",
        )
        pipeline = IntelligencePipeline(config)
        result = await pipeline.process(user_id=intent_result.user_id)

        # 2. 格式化输出
        return self._format_intelligence_result(result)
```

---

## 4. 菜单与意图映射

### 4.1 菜单 → 意图 → 任务

| 菜单ID | 菜单名称 | 意图 | Agent | 参数 |
|-------|---------|------|-------|------|
| menu_intelligence_hot | 查看热点新闻 | view_hot_news | intelligence | category=hot |
| menu_intelligence_tech | 查看科技动态 | view_category_news | intelligence | category=tech |
| menu_intelligence_ai | 查看AI进展 | view_category_news | intelligence | category=ai |
| menu_intelligence_investment | 查看投资并购 | view_category_news | intelligence | category=investment |
| menu_intelligence_report | 查看行业报告 | view_category_news | intelligence | category=report |
| menu_search_news | 搜索新闻 | search_intelligence | search | type=news |
| menu_search_info | 搜索资讯 | search_intelligence | search | type=info |
| menu_search_trend | 搜索趋势 | search_intelligence | search | type=trend |
| menu_search_advanced | 高级搜索 | search_advanced | search | - |
| menu_settings_get | 获取当前配置 | get_settings | system | - |
| menu_settings_frequency | 切换推送频率 | change_settings | system | key=frequency |
| menu_settings_language | 语言设置 | change_settings | system | key=language |
| menu_settings_clear | 清除会话历史 | clear_history | system | - |

### 4.2 消息 → 意图 (示例)

| 消息内容 | 识别方式 | 意图 | Agent |
|---------|---------|------|-------|
| 科技动态 | Keyword | view_category_news | intelligence |
| 有什么热点新闻 | Keyword | view_hot_news | intelligence |
| 帮我查下AI进展 | AI | view_category_news | intelligence |
| 搜索GPT最新消息 | AI | search_intelligence | search |

---

## 5. 输出格式设计

### 5.1 控制台模拟输出

```
══════════════════════════════════════════════════════════════════
                    📬 用户交互流程模拟
══════════════════════════════════════════════════════════════════

【用户操作】
  类型: 菜单点击
  内容: 查看热点新闻
  用户ID: test_user_001

【系统处理】
  ├── 1. 事件解析
  │      ✓ 解析菜单事件: menu_intelligence_hot
  │
  ├── 2. 意图识别
  │      ✓ 来源: menu (置信度: 100%)
  │      ✓ 意图: view_hot_news
  │      ✓ Agent: intelligence
  │
  ├── 3. 任务执行
  │      ├── 3.1 数据采集
  │      │      ├── RSS采集: 20条
  │      │      ├── 微博采集: 30条
  │      │      └── HackerNews: 10条
  │      │
  │      ├── 3.2 去重处理
  │      │      └── 去除重复: 15条 → 45条
  │      │
  │      ├── 3.3 AI分析
  │      │      └── 分类: 科技(12), 商业(8), ...
  │      │
  │      └── 3.4 存储
  │             ├── PostgreSQL: 45条
  │             └── S3: 45个MD文件
  │
  └── 4. 响应生成
         ✓ Markdown格式
         ✓ 包含摘要和链接

【用户收到】
═══════════════════════════════════════════════════════════════
📰 今日热点新闻 (2026-03-10)

【科技】
1. OpenAI 发布 GPT-5
   https://...
2. Google 发布 Gemini 2.0
   https://...

【商业】
1. XXX 公司获得亿美元融资
   https://...

【查看更多】→ 点击链接
═══════════════════════════════════════════════════════════════

【执行统计】
  总耗时: 3.2s
  采集: 60条 → 去重: 45条 → 存储: 45条
═══════════════════════════════════════════════════════════════
```

---

## 6. 实施计划

### Phase 1: 统一入口 (1小时)
- [ ] 创建 UnifiedMessageHandler
- [ ] 整合菜单和消息处理

### Phase 2: 任务执行 (2小时)
- [ ] 实现 TaskExecutor
- [ ] 集成 IntelligencePipeline

### Phase 3: 输出格式化 (1小时)
- [ ] 实现 Markdown 格式化
- [ ] 实现控制台模拟输出

### Phase 4: 测试验证 (1小时)
- [ ] 菜单触发测试
- [ ] 消息触发测试
- [ ] 完整流程测试

---

## 7. 预期结果

| 指标 | 目标 |
|-----|------|
| 菜单响应时间 | <5s |
| 消息响应时间 | <10s |
| 支持菜单项 | 14个 |
| 支持触发方式 | 2种 |

---

**批准**: 2026-03-10
**下一步**: 实施执行

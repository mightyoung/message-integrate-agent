# OpenClaw 风格心跳与技能系统设计方案

**日期**: 2026-03-08
**版本**: v1.0
**状态**: 已批准

---

## 一、概述

### 1.1 目标

实现 OpenClaw 风格的自进化能力：
- **A) 心跳机制主动性**：让 Agent 能主动推送消息给用户
- **C) 技能系统增强**：门控、优先级、版本管理

### 1.2 设计原则

1. **响应契约**：心跳结果必须有明确的状态契约
2. **分层隔离**：Lane-based 命令队列实现并发控制
3. **门控验证**：技能加载前必须通过环境检查
4. **版本锁定**：支持语义版本和依赖解析

---

## 二、心跳机制主动性 (Heartbeat Autonomy)

### 2.1 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    HeartbeatEngine                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Scheduler   │→ │ AgentRuntime│→ │ ResponseHandler │  │
│  │ (Cron/Lane)│  │ (7 Steps)   │  │ (Contract)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│         ↓               ↓                  ↓              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              CommandQueue (Lane-based)             │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐   │  │
│  │  │ global │ │ session│ │ sub-   │ │  cron    │   │  │
│  │  │ (max:4)│ │ (serial)│ │ agent  │ │(parallel)│   │  │
│  │  └────────┘ └────────┘ │(max:8) │ └──────────┘   │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓
              ┌───────────────────────┐
              │    PushService        │
              │ (Active Delivery)     │
              └───────────────────────┘
```

### 2.2 响应契约

```python
class HeartbeatResponse:
    """心跳响应契约"""
    status: str          # "ok" | "alert" | "error"
    content: str         # 推送内容（alert 时）
    channel: str        # 目标通道 "telegram:user_id" | "feishu:open_id"
    suppress: bool      # 是否静默（True = 不推送）

    @classmethod
    def ok(cls) -> "HeartbeatResponse":
        return cls(status="ok", suppress=True)

    @classmethod
    def alert(cls, content: str, channel: str = "default") -> "HeartbeatResponse":
        return cls(status="alert", content=content, channel=channel, suppress=False)
```

### 2.3 检查清单 (HEARTBEAT.md)

- 位置：`.learnings/HEARTBEAT.md`
- 评估规则：
  - 错误率 > 10% → alert
  - 长时间无交互 → alert
  - 新用户反馈 → alert
  - 技能更新需求 → alert

### 2.4 命令队列

```python
class CommandQueue:
    LANES = {
        "global": {"max_concurrent": 4, "fifo": True},
        "session": {"max_concurrent": 1, "fifo": True},
        "sub_agent": {"max_concurrent": 8, "fifo": True},
        "cron": {"max_concurrent": 10, "fifo": False},
    }
```

### 2.5 调度器

- Cron 表达式支持
- 一次性调度 (at)
- 间隔调度 (every)

---

## 三、技能系统增强

### 3.1 三层优先级

```
1. Workspace (highest): <project>/skills/
2. Managed: ~/.message-agent/skills/
3. Bundled (lowest): <install>/skills/
```

### 3.2 YAML Frontmatter

```yaml
---
name: web_search
version: "1.2.0"
description: Search the web
requires:
  binary: ["curl", "jq"]
  env: ["TAVILY_API_KEY"]
  config: ["search.timeout"]
platforms: ["darwin", "linux"]
entry: skill.py
---
```

### 3.3 工具策略

```python
# 优先级: global_deny → agent_deny → global_allow → agent_allow → default(deny)

CORE_TOOLS = {
    "read", "write", "edit",
    "exec", "process",
    "search_memory",
    "sub_agent",
}
```

### 3.4 版本管理

- 语义版本 (semver)
- 版本锁定 (lock file)
- 兼容检查

---

## 四、数据流

### 心跳流程

```
Scheduler → CommandQueue → AgentRuntime(7步) → Checklist评估 → ResponseHandler → PushService
```

### 技能加载流程

```
扫描三层 → Frontmatter解析 → Gate检查 → Policy应用 → 加载注册
```

---

## 五、组件清单

| 组件 | 文件 | 描述 |
|------|------|------|
| HeartbeatResponse | heartbeat/response.py | 响应契约 |
| HeartbeatChecklist | heartbeat/checklist.py | 检查清单 |
| CommandQueue | heartbeat/queue.py | Lane队列 |
| Scheduler | heartbeat/scheduler.py | Cron调度 |
| SkillGate | skills/gate.py | 门控检查 |
| ToolPolicy | skills/policy.py | 工具策略 |
| SkillRegistry | skills/registry.py | 版本管理 |
| IdempotentCommand | heartbeat/idempotent.py | 幂等执行 |
| MemoryCompaction | heartbeat/memory.py | 内存压缩 |

---

## 六、参考

- OpenClaw Architecture (https://gist.github.com/royosherove/971c7b4a350a30ac8a8dad41604a95a0)
- APScheduler (Python 定时任务标准)
- Celery Beat (分布式调度)

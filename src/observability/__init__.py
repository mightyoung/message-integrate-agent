"""
Observability Module - 可观测性系统

实现生产环境监控与指标收集：
- Metrics: 关键性能指标
- Tracing: 链路追踪
- Health Checks: 健康检查增强

设计参考：
- Microsoft AI Agents: Observability & Evaluation
- LangChain Production Monitoring
- Prometheus metrics collection
"""
import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import defaultdict

from loguru import logger


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"      # 计数器 - 只增不减
    GAUGE = "gauge"        # 仪表 - 可增可减
    HISTOGRAM = "histogram" # 直方图 - 分布统计


@dataclass
class Metric:
    """指标"""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """增加计数器"""
        key = self._make_key(name, labels)
        self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表值"""
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录直方图值"""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)

    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """生成指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_all(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: {
                    "count": len(v),
                    "sum": sum(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                }
                for k, v in self._histograms.items()
            },
        }

    def get_prometheus_format(self) -> str:
        """转换为Prometheus格式"""
        lines = []

        # Counters
        for key, value in self._counters.items():
            lines.append(f"# TYPE {key} counter")
            lines.append(f"{key} {value}")

        # Gauges
        for key, value in self._gauges.items():
            lines.append(f"# TYPE {key} gauge")
            lines.append(f"{key} {value}")

        # Histograms
        for key, values in self._histograms.items():
            if values:
                lines.append(f"# TYPE {key} histogram")
                lines.append(f"{key}_count {len(values)}")
                lines.append(f"{key}_sum {sum(values)}")

        return "\n".join(lines)


class MetricsService:
    """
    指标服务

    统一收集和暴露系统指标
    """

    # 预定义指标名称
    REQUEST_LATENCY = "request_latency_seconds"
    REQUEST_COUNT = "requests_total"
    ERROR_COUNT = "errors_total"
    TOOL_CALL_COUNT = "tool_calls_total"
    TOOL_CALL_SUCCESS = "tool_calls_success_total"
    TOKEN_USAGE = "token_usage_total"
    ROUTING_DECISIONS = "routing_decisions_total"
    ROUTING_SUCCESS = "routing_success_total"
    FEEDBACK_COUNT = "feedback_total"
    MESSAGE_PROCESSED = "messages_processed_total"
    ACTIVE_CONNECTIONS = "active_connections"

    def __init__(self):
        self.collector = MetricsCollector()
        self._start_time = time.time()

    def record_request(self, duration: float, success: bool = True):
        """记录请求"""
        self.collector.observe(self.REQUEST_LATENCY, duration)
        self.collector.increment(self.REQUEST_COUNT)
        if not success:
            self.collector.increment(self.ERROR_COUNT)

    def record_tool_call(self, tool_name: str, success: bool = True):
        """记录工具调用"""
        self.collector.increment(self.TOOL_CALL_COUNT, labels={"tool": tool_name})
        if success:
            self.collector.increment(self.TOOL_CALL_SUCCESS, labels={"tool": tool_name})

    def record_routing(self, router_name: str, success: bool = True):
        """记录路由决策"""
        self.collector.increment(self.ROUTING_DECISIONS, labels={"router": router_name})
        if success:
            self.collector.increment(self.ROUTING_SUCCESS, labels={"router": router_name})

    def record_feedback(self, feedback_type: str):
        """记录反馈"""
        self.collector.increment(self.FEEDBACK_COUNT, labels={"type": feedback_type})

    def record_message_processed(self):
        """记录消息处理"""
        self.collector.increment(self.MESSAGE_PROCESSED)

    def set_active_connections(self, count: int):
        """设置活跃连接数"""
        self.collector.set_gauge(self.ACTIVE_CONNECTIONS, count)

    def record_token_usage(self, input_tokens: int = 0, output_tokens: int = 0):
        """记录Token使用"""
        total = input_tokens + output_tokens
        self.collector.increment(self.TOKEN_USAGE, total)

    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        metrics = self.collector.get_all()
        metrics["uptime_seconds"] = time.time() - self._start_time
        return metrics

    def get_prometheus_metrics(self) -> str:
        """获取Prometheus格式指标"""
        return self.collector.get_prometheus_format()


class TracingContext:
    """链路追踪上下文"""

    def __init__(self, trace_id: str, span_name: str):
        self.trace_id = trace_id
        self.span_name = span_name
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.attributes: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any):
        """设置属性"""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """添加事件"""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })

    def end(self):
        """结束追踪"""
        self.end_time = time.time()

    def duration_ms(self) -> float:
        """获取持续时间(毫秒)"""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "span_name": self.span_name,
            "duration_ms": self.duration_ms(),
            "attributes": self.attributes,
            "events": self.events,
        }


class TracingService:
    """链路追踪服务"""

    def __init__(self, max_spans: int = 1000):
        self.max_spans = max_spans
        self._spans: List[TracingContext] = []
        self._current_span: Optional[TracingContext] = None

    def start_span(self, trace_id: str, span_name: str) -> TracingContext:
        """开始span"""
        span = TracingContext(trace_id, span_name)
        self._spans.append(span)
        self._current_span = span

        # 限制span数量
        if len(self._spans) > self.max_spans:
            self._spans = self._spans[-self.max_spans:]

        return span

    def end_span(self):
        """结束当前span"""
        if self._current_span:
            self._current_span.end()
            self._current_span = None

    def get_current_span(self) -> Optional[TracingContext]:
        """获取当前span"""
        return self._current_span

    def get_recent_spans(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的spans"""
        spans = self._spans[-limit:]
        return [s.to_dict() for s in spans]


class ObservabilityService:
    """
    可观测性服务

    整合指标和追踪
    """

    def __init__(self):
        self.metrics = MetricsService()
        self.tracing = TracingService()

    async def track_request(self, trace_id: str, span_name: str):
        """追踪请求"""
        span = self.tracing.start_span(trace_id, span_name)
        start_time = time.time()

        try:
            yield span
        finally:
            duration = time.time() - start_time
            self.metrics.record_request(duration)
            span.end()

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        metrics = self.metrics.get_metrics()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": metrics.get("uptime_seconds", 0),
            "metrics": {
                "requests_total": metrics.get("counters", {}).get("requests_total", 0),
                "errors_total": metrics.get("counters", {}).get("errors_total", 0),
                "messages_processed": metrics.get("counters", {}).get("messages_processed_total", 0),
            },
        }

    def get_metrics_endpoint(self) -> Dict[str, Any]:
        """获取指标端点数据"""
        return {
            "metrics": self.metrics.get_metrics(),
            "recent_traces": self.tracing.get_recent_spans(10),
        }


# 全局可观测性服务
_observability_service: Optional[ObservabilityService] = None


def get_observability_service() -> ObservabilityService:
    """获取全局可观测性服务"""
    global _observability_service
    if _observability_service is None:
        _observability_service = ObservabilityService()
    return _observability_service

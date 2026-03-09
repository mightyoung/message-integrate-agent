# 飞书长连接 + Mihomo 代理集成设计方案

## 背景

用户需要在 NAS Docker 环境中运行 message-integrate-agent，需要：
1. 将飞书通信从 webhook 改为 WebSocket 长连接模式
2. 添加 mihomo 代理支持，用于访问非中国大陆网站
3. 使用混合模式判断请求是否需要代理

## 目标

- 飞书 WebSocket 长连接正常工作
- 搜索/API 请求智能路由到 mihomo 代理
- 支持域名规则 + GeoIP 混合判断
- 支持 HTTP(9090) 和 SOCKS5(7890) 双代理协议

## 架构设计

### 网络拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Container                        │
│  ┌─────────────────┐    ┌─────────────────────────────┐   │
│  │  FeishuAdapter  │    │      ProxyManager          │   │
│  │  (WebSocket)    │    │  ┌─────────────────────┐   │   │
│  │                 │───▶│  │ DomainRouter        │   │   │
│  │  直连: api.feishu.cn   │  │ + GeoIPRouter      │   │   │
│  └─────────────────┘    │  └──────────┬──────────┘   │   │
│                         │             │               │   │
│  ┌─────────────────┐    │  ┌──────────▼──────────┐   │   │
│  │  Search/Web      │    │  │ MihomoConnector     │   │   │
│  │  (Tavily/etc)   │───▶│  │ HTTP:9090 SOCKS5:7890   │   │
│  └─────────────────┘    │  └─────────────────────┘   │   │
│                         └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
            │                               │
            │ Docker Network                │ Docker Network
            ▼                               ▼
┌───────────────────┐            ┌───────────────────┐
│  飞书服务器        │            │  mihomo (Docker) │
│  api.feishu.cn    │            │  HTTP:9090        │
│                   │            │  SOCKS5:7890      │
└───────────────────┘            └───────────────────┘
```

### 组件设计

#### 1. ProxyManager 增强

```python
class ProxyManager:
    # 现有功能保持不变

    # 新增功能：
    - MihomoConnector: 连接 mihomo 代理
    - GeoIPRouter: 基于 IP 地址判断地理位置
    - HybridRouter: 混合路由（域名优先 + GeoIP fallback）
```

#### 2. MihomoConnector

```python
class MihomoConnector:
    """Mihomo 代理连接器"""

    def __init__(self, http_port: int = 9090, socks_port: int = 7890):
        self.http_proxy = f"http://mihomo:{http_port}"
        self.socks_proxy = f"socks5://mihomo:{socks_port}"

    def get_client(self, url: str) -> httpx.Client:
        """根据 URL 返回合适的代理客户端"""
```

#### 3. GeoIPRouter

```python
class GeoIPRouter:
    """基于 GeoIP 的路由判断"""

    def __init__(self, china_cidrs: list):
        self.china_cidrs = china_cidrs  # 中国IP段

    def is_china_ip(self, ip: str) -> bool:
        """判断IP是否在中国"""
        # 使用 ipaddress 模块进行CIDR匹配
```

#### 4. HybridRouter

```python
class HybridRouter:
    """混合路由：域名规则优先，GeoIP fallback"""

    def __init__(self, domain_router, geoip_router):
        self.domain_router = domain_router
        self.geoip_router = geoip_router

    def should_proxy(self, url: str, ip: str = None) -> bool:
        """判断是否需要代理"""
        # 1. 先检查域名规则
        if self.domain_router.has_rule(url):
            return self.domain_router.should_proxy(url)

        # 2. 如果没有域名规则，检查 GeoIP
        if ip:
            return not self.geoip_router.is_china_ip(ip)

        # 3. 默认使用代理
        return True
```

## 实现计划

### Phase 1: 基础代理支持

1. 修改 `config/proxy.yaml`，添加 mihomo 配置
2. 增强 `ProxyManager`，支持 mihomo 连接
3. 添加环境变量配置：MIHOMO_HTTP_PORT, MIHOMO_SOCKS_PORT

### Phase 2: GeoIP 支持

1. 添加 GeoIP 路由模块
2. 集成 IP 库（中国IP段）
3. 实现混合路由逻辑

### Phase 3: 飞书长连接集成

1. 修复 FeishuWebSocketClient 的同步/异步问题
2. 在 FeishuAdapter 中集成代理（非必需，直连）
3. 测试长连接稳定性

### Phase 4: 搜索代理集成

1. 在 search_web 函数中集成代理判断
2. 为 Tavily 等外部 API 配置代理规则

## 配置示例

```yaml
# config/proxy.yaml
mihomo:
  enabled: true
  http_port: 9090
  socks_port: 7890
  container_name: "mihomo"

routing:
  mode: "hybrid"  # domain | geoip | hybrid

  # 域名规则（优先）
  proxy_domains:
    - "*.google.com"
    - "*.tavily.com"
    - "api.github.com"

  direct_domains:
    - "*.baidu.com"
    - "api.feishu.cn"  # 飞书直连

  # GeoIP fallback
  geoip:
    fallback_to_proxy: true
    china_cidrs:
      - "10.0.0.0/8"
      - "172.16.0.0/12"
      # ... 更多中国IP段
```

## 依赖库

- `geoip2` 或 `ip2region` - GeoIP 查询
- `httpx` - HTTP 客户端（已集成）
- `aiohttp[speedups]` - 异步 HTTP（可选）

## 注意事项

1. 飞书长连接不需要代理，直连国内网络即可
2. mihomo 需要与 message-integrate-agent 在同一 Docker 网络
3. 优先使用 SOCKS5 代理（性能更好）
4. 需要处理代理失败时的 fallback

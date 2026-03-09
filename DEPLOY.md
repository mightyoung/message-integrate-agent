# ============================================================
# Message Integrate Agent - 一键部署说明
# ============================================================

## 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAS Docker Network                        │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐                         │
│  │   gateway    │    │   mihomo     │                         │
│  │(Feishu WS)  │───▶│  (代理服务)  │                         │
│  │   :8080      │    │  :7890       │                         │
│  └──────────────┘    └──────────────┘                         │
│         │                    │                                  │
│         │            ┌──────▼──────┐                          │
│         │            │  bettafish  │  舆情分析               │
│         │            │   :5000     │                          │
│         │            └─────────────┘                          │
│         │                    │                                  │
│         │            ┌──────▼──────┐                          │
│         │            │  mirofish  │  预测分析               │
│         │            │   :5001     │                          │
│         │            └─────────────┘                          │
│         │                                                     │
│         │  飞书长连接 (WebSocket)                             │
│         └─────────────────────────────────────────────────────▶ │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
   飞书服务器
   (wss://msg-frontier.feishu.cn)
```

## 上传到 NAS 的文件

将以下文件上传到 NAS 的 `/volume1/docker/message-hub/` 目录：

```
message-hub/
├── docker-compose.prod.yml    # 部署配置
├── Dockerfile.prod            # 镜像构建
├── .env.prod                 # 环境变量
├── bettafish/               # 舆情分析服务
│   └── Dockerfile
├── mirofish/                # 预测分析服务
│   └── Dockerfile
├── config/                  # 配置目录
│   ├── clash/             # mihomo 配置
│   ├── proxy.yaml
│   └── settings.yaml
└── DEPLOY.md               # 说明
```

## NAS 上执行

### 1. 构建并启动所有服务

```bash
cd /volume1/docker/message-hub/

# 构建所有镜像并启动
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 2. 验证

```bash
# 查看状态
docker-compose -f docker-compose.prod.yml ps

# 健康检查
curl http://localhost:8080/health

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

## 端口说明

| 端口 | 服务 |
|------|------|
| 8080 | Gateway HTTP |
| 8081 | WebSocket |
| 7890 | mihomo HTTP 代理 |
| 5000 | BettaFish API (舆情分析) |
| 5001 | MiroFish API (预测分析) |
| 3000 | MiroFish Web UI |

## 飞书配置

已配置为 **WebSocket 长连接**模式 (`FEISHU_CONNECTION_MODE=websocket`)

- WebSocket 连接到 `wss://msg-frontier.feishu.cn`
- 不需要公网 IP，客户端主动连接
- 通过 mihomo 代理访问非中国大陆 IP

## 代理规则 (mihomo)

已配置智能路由：
- **国内域名/IP**: 直连 (DIRECT)
- **海外域名/IP**: 代理 (PROXY)
- **飞书域名**: 直连

配置文件: `config/clash/config.yaml`

## API 调用

### BettaFish 舆情分析

```bash
# 舆情分析
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI发展", "depth": "deep"}'
```

### MiroFish 预测分析

```bash
# 预测分析
curl -X POST http://localhost:5001/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"scenario": "科技发展", "steps": 10}'
```

## 常用命令

```bash
# 启动
docker-compose -f docker-compose.prod.yml start

# 停止
docker-compose -f docker-compose.prod.yml stop

# 重启
docker-compose -f docker-compose.prod.yml restart

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f gateway
docker-compose -f docker-compose.prod.yml logs -f bettafish
docker-compose -f docker-compose.prod.yml logs -f mirofish
docker-compose -f docker-compose.prod.yml logs -f mihomo

# 进入容器
docker exec -it message-hub-gateway /bin/bash
docker exec -it message-hub-bettafish /bin/bash
docker exec -it message-hub-mirofish /bin/bash
```

## 常见问题

### Q: 无法连接飞书
A: 检查 mihomo 是否正常运行: `docker-compose ps mihomo`

### Q: BettaFish/MiroFish 启动失败
A: 检查 DeepSeek API 配置是否正确: `docker-compose logs bettafish`

### Q: 代理无法访问
A: 检查 config/clash/config.yaml 中的代理节点是否有效

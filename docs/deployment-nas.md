# Message Integrate Agent - NAS 部署手册

## 一、部署架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAS (192.168.1.2)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ PostgreSQL  │  │    Redis   │  │    S3/RustFs Storage   │ │
│  │  :45041     │  │   :40967   │  │      :37163            │ │
│  │ + pgvector  │  │             │  │   (mightyoung bucket)  │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│         │                │                      │                 │
│         └────────────────┼──────────────────────┘                 │
│                          │                                        │
│                    ┌─────▼─────┐                                  │
│                    │  mihomo   │  (代理服务 :7890)                │
│                    │  :7890    │                                  │
│                    └───────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Docker 容器
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Container                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              message-hub-gateway                         │   │
│  │  - FastAPI Gateway (:8080/8081)                         │   │
│  │  - Agent Pool                                           │   │
│  │  - Intelligence Pipeline                                 │   │
│  │  - Feishu/Telegram Adapter                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              ngrok (可选)                                │   │
│  │  - 公网隧道                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 二、NAS 服务前置要求

### 2.1 必需服务（已在 NAS 运行）

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL + pgvector | 45041 | 向量数据库，存储信息 embeddings |
| Redis | 40967 | 缓存、会话、限流 |
| S3/RustFs | 37163 | MD 文件存储 |
| mihomo | 7890 | HTTP/HTTPS 代理 |

### 2.2 验证 NAS 服务

```bash
# 测试 PostgreSQL
nc -zv 192.168.1.2 45041

# 测试 Redis
nc -zv 192.168.1.2 40967

# 测试 S3
curl -I http://192.168.1.2:37163

# 测试代理
curl -x http://192.168.1.2:7890 https://www.google.com -I
```

## 三、部署步骤

### 步骤 1：准备项目目录

```bash
# 在 NAS 上创建项目目录
mkdir -p /volume1/docker/message-integrate-agent
cd /volume1/docker/message-integrate-agent

# 克隆项目（或从本地上传）
git clone <your-repo-url> .
```

### 步骤 2：配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

必需配置项：

```bash
# ==================== 飞书配置 ====================
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_VERIFICATION_TOKEN=your_verification_token
FEISHU_ENCRYPT_KEY=your_encrypt_key

# ==================== Telegram 配置 ====================
TELEGRAM_BOT_TOKEN=your_telegram_token

# ==================== 代理配置 ====================
HTTP_PROXY=http://192.168.1.2:7890
HTTPS_PROXY=http://192.168.1.2:7890
NO_PROXY=localhost,127.0.0.1,api.feishu.cn,open.feishu.cn,192.168.0.0/16

# ==================== PostgreSQL + pgvector (NAS) ====================
DATABASE_URL=postgresql://postgres:postgres@192.168.1.2:45041/bs_generator_db
PG_HOST=192.168.1.2
PG_PORT=45041
PG_USER=postgres
PG_PASSWORD=postgres
PG_DATABASE=bs_generator_db

# ==================== Redis (NAS) ====================
REDIS_HOST=192.168.1.2
REDIS_PORT=40967
REDIS_DB=0

# ==================== S3/RustFs Storage (NAS) ====================
S3_ENDPOINT_URL=http://192.168.1.2:37163
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET_NAME=mightyoung
S3_REGION_NAME=us-east-1

# ==================== LLM 配置 ====================
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# ==================== GitHub (可选) ====================
GITHUB_TOKEN=your_github_token
```

### 步骤 3：构建 Docker 镜像

```bash
# 构建镜像
docker build -t message-integrate-agent:latest .

# 或使用 docker-compose
docker-compose build
```

### 步骤 4：启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f gateway

# 查看服务状态
docker-compose ps
```

### 步骤 5：验证部署

```bash
# 健康检查
curl http://localhost:8080/health

# 检查详细状态
curl http://localhost:8080/health/detail
```

预期响应：
```json
{
  "status": "healthy",
  "service": "message-hub-gateway",
  "version": "1.0.0"
}
```

## 四、服务管理

### 4.1 常用命令

```bash
# 启动
docker-compose start

# 停止
docker-compose stop

# 重启
docker-compose restart

# 查看日志
docker-compose logs -f

# 进入容器
docker exec -it message-hub-gateway /bin/bash

# 查看资源使用
docker stats message-hub-gateway
```

### 4.2 自动重启配置

```yaml
# docker-compose.yml 中已配置
restart: unless-stopped
```

### 4.3 日志轮转

```bash
# 查看日志大小
du -sh /var/lib/docker/containers/*/message-hub-gateway-*.log

# 清理旧日志
docker-compose rm -f
docker system prune -f
```

## 五、飞书 Webhook 配置

### 5.1 创建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 `APP_ID` 和 `APP_SECRET`

### 5.2 配置权限

必需权限：
- `im:message:send_as_bot`
- `im:chat:message`
- `im:chat:members`
- `im:menu` (菜单事件)

### 5.3 配置事件订阅

1. 创建应用后添加回调事件
2. **WebSocket 模式（推荐，无需内网穿透）**：
   - 事件 URL：可选，WebSocket 长连接会自动接收事件
   - 事件类型：
     - `im.message.message_created` (消息事件)
     - `im.menu.menu_clicked` (菜单点击事件)
3. **Webhook 模式（需要内网穿透）**：
   - 事件 URL：`http://<your-domain>/webhook/feishu/event`
   - 事件类型同上

### 5.4 获取配置信息

在 .env 中填入：
```bash
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=your_app_secret
FEISHU_VERIFICATION_TOKEN=your_verification_token
FEISHU_ENCRYPT_KEY=your_encrypt_key
FEISHU_CONNECTION_MODE=websocket  # 推荐使用 WebSocket 长连接
```

## 六、故障排查

### 6.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 无法连接 PostgreSQL | NAS 防火墙 | 检查 45041 端口 |
| 无法连接 Redis | Redis 未启动 | 检查 40967 端口 |
| S3 上传失败 | 凭证错误 | 验证 S3_ACCESS_KEY |
| 代理无法访问 | mihomo 未运行 | 检查 7890 端口 |
| 飞书消息失败 | Webhook URL 不对 | 确认公网可访问 |

### 6.2 调试命令

```bash
# 测试数据库连接
docker exec -it message-hub-gateway python -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://postgres:postgres@192.168.1.2:45041/bs_generator_db')
    print(await conn.fetch('SELECT version()'))
    await conn.close()
asyncio.run(test())
"

# 测试 Redis
docker exec -it message-hub-gateway python -c "
import redis
r = redis.Redis(host='192.168.1.2', port=40967, db=0)
print(r.ping())
"

# 测试 S3
docker exec -it message-hub-gateway python -c "
import boto3
s3 = boto3.client('s3', endpoint_url='http://192.168.1.2:37163')
print(s3.list_buckets())
"
```

## 七、升级部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建
docker-compose build

# 滚动更新
docker-compose up -d --force-recreate
```

## 八、备份与恢复

### 8.1 备份

```bash
# 备份配置文件
tar -czf backup-config-$(date +%Y%m%d).tar.gz .env config/

# 备份数据库（可选）
pg_dump -h 192.168.1.2 -p 45041 -U postgres bs_generator_db > backup-db-$(date +%Y%m%d).sql
```

### 8.2 恢复

```bash
# 恢复配置
tar -xzf backup-config-20260101.tar.gz

# 恢复数据库
psql -h 192.168.1.2 -p 45041 -U postgres bs_generator_db < backup-db-20260101.sql
```

## 九、监控

### 9.1 健康检查端点

| 端点 | 说明 |
|------|------|
| `/health` | 基础健康检查 |
| `/health/detail` | 详细状态（包含所有组件） |

### 9.2 外部监控

```bash
# 定时检查健康
*/5 * * * * curl -f http://localhost:8080/health || docker-compose restart
```

## 十、快速命令参考

```bash
# 首次部署
cd /volume1/docker/message-integrate-agent
cp .env.example .env
nano .env
docker-compose up -d

# 查看状态
docker-compose ps
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down
```

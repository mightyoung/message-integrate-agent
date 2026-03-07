# Message Integrate Agent

AI-powered message hub that connects to multiple messaging platforms (Telegram, Feishu, WeChat) with intelligent task routing and Docker deployment support.

## Features

- **Multi-Platform Support**: Telegram, Feishu (Lark), WeChat
- **Intelligent Routing**: Keyword-based and AI-powered intent recognition
- **Agent Pool**: LLM, Search, and API agents
- **MCP Integration**: Model Context Protocol for tool exposure
- **Proxy Support**: HTTP/SOCKS proxy with automatic failover
- **Docker Ready**: One-click deployment with Docker Compose

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd message-integrate-agent

# Create virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy environment example
cp .env.example .env

# Edit .env with your API keys
# Required: OPENAI_API_KEY (for LLM and AI routing)
# Optional: TAVILY_API_KEY, TELEGRAM_BOT_TOKEN, etc.
```

### 3. Run

```bash
# Local development
python -m src.main

# Or use the startup script
./start.sh
```

### 4. Docker Deployment

```bash
# Build and run with Docker
./start-docker.sh

# Or manually
docker build -t message-integrate-agent .
docker-compose up -d
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token |
| `FEISHU_APP_ID` | No | Feishu app ID |
| `FEISHU_APP_SECRET` | No | Feishu app secret |
| `TAVILY_API_KEY` | No | Tavily search API key |
| `HTTP_PROXY` | No | HTTP proxy URL |
| `HTTPS_PROXY` | No | HTTPS proxy URL |

### YAML Configuration

Edit `config/settings.yaml` to customize:
- Gateway host/port
- Platform settings
- Routing rules
- LLM defaults

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Gateway (8080)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ WebSocket│  │ Webhook   │  │ Health Check  │  │
│  │   /ws    │  │ /webhook/*│  │   /health    │  │
│  └────┬─────┘  └────┬─────┘  └───────────────┘  │
└───────┼─────────────┼────────────────────────────┘
        │             │
        ▼             ▼
┌─────────────────────────────────────────────────────┐
│              Task Router                             │
│  ┌──────────────┐    ┌────────────────────────┐   │
│  │   Keyword    │    │   AI Intent Router    │   │
│  │   Router     │    │   (GPT-4)            │   │
│  └──────┬───────┘    └───────────┬────────────┘   │
└─────────┼─────────────────────────┼───────────────┘
          │                         │
          ▼                         ▼
┌─────────────────────────────────────────────────────┐
│                  Agent Pool                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────────────┐   │
│  │LLM Agent│  │Search   │  │   API Agent     │   │
│  │ (GPT-4) │  │ Agent   │  │ (HTTP Calls)   │   │
│  └─────────┘  └─────────┘  └─────────────────────┘│
└─────────────────────────────────────────────────────┘
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Simple health check |
| `/health/detailed` | GET | Detailed status |
| `/ws/{client_id}` | WS | WebSocket connection |
| `/webhook/telegram` | POST | Telegram webhook |
| `/webhook/feishu` | POST | Feishu webhook |
| `/webhook/wechat` | POST | WeChat webhook |
| `/docs` | GET | OpenAPI docs |

## MCP Tools

When MCP Server is enabled (port 8081):

| Tool | Description |
|------|-------------|
| `search_web` | Web search (Tavily/Google/DuckDuckGo) |
| `chat_with_llm` | LLM conversation |
| `call_api` | HTTP API calls |
| `send_message` | Send messages to platforms |

## Routing Rules

### Keyword Routing

Edit `config/settings.yaml`:

```yaml
routing:
  keyword_match:
    rules:
      - keywords: ["天气", "weather"]
        agent: "search"
        action: "weather"
      - keywords: ["翻译", "translate"]
        agent: "llm"
        action: "translate"
```

### AI Routing

When keyword doesn't match, AI routing uses GPT-4 to determine which agent should handle the message.

## Development

```bash
# Run tests
pytest tests/ -v

# Add new tests
# Edit tests/ directory

# Code style
ruff check src/
```

## Troubleshooting

### Gateway won't start

```bash
# Check port availability
lsof -i :8080

# Check logs
tail -f logs/app.log
```

### Telegram webhook not working

1. Make sure you've set the webhook URL in Telegram
2. Verify `TELEGRAM_BOT_TOKEN` is correct
3. Check `/health/detailed` for platform status

### AI routing not working

1. Verify `OPENAI_API_KEY` is set
2. Check logs for API errors
3. Try keyword routing first

## License

MIT

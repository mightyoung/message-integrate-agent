# Architecture

## Overview

Message Integrate Agent is an AI-powered message hub that connects to multiple messaging platforms (Telegram, Feishu, WeChat) with intelligent task routing.

## Components

- **Gateway**: WebSocket server for real-time messaging
- **Adapters**: Platform-specific message handlers
- **MCP Server**: Exposes tools for AI agents
- **Router**: Keyword and AI-based message routing
- **Agent Pool**: LLM, Search, and API agents

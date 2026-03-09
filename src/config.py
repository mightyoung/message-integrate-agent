"""
Configuration module for Message Integrate Agent
"""
import os
import re
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_env_vars(value):
    """Resolve ${VAR} environment variable placeholders in a string."""
    if not isinstance(value, str):
        return value
    # Match ${VAR} pattern
    pattern = r'\$\{([^}]+)\}'
    matches = re.findall(pattern, value)
    if not matches:
        return value
    # Replace each ${VAR} with environment variable
    def replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, value)  # Keep original if not found
    return re.sub(pattern, replace, value)


def resolve_config_env_vars(config):
    """Recursively resolve environment variables in config object."""
    for field_name in config.model_fields:
        value = getattr(config, field_name)
        if isinstance(value, str):
            resolved = resolve_env_vars(value)
            setattr(config, field_name, resolved)
        elif hasattr(value, 'model_fields'):  # Nested pydantic model
            resolve_config_env_vars(value)
    return config


class GatewayConfig(BaseModel):
    """Gateway server configuration."""
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False


class PlatformConfig(BaseModel):
    """Message platform configuration."""
    enabled: bool = False
    # Telegram
    bot_token: Optional[str] = None
    # Feishu
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    verification_token: Optional[str] = None
    # WeChat
    webhook_url: Optional[str] = None


class MCPConfig(BaseModel):
    """MCP server configuration."""
    server_name: str = "message-hub"
    version: str = "1.0.0"


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    default_model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = "https://api.openai.com/v1"


class SearchConfig(BaseModel):
    """Search engine configuration."""
    default_engine: str = "tavily"
    tavily_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None


class ProxyConfig(BaseModel):
    """Proxy configuration."""
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    no_proxy: Optional[str] = None


class AppConfig(BaseSettings):
    """Main application configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Gateway
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)

    # Platforms
    telegram: PlatformConfig = Field(default_factory=PlatformConfig)
    feishu: PlatformConfig = Field(default_factory=PlatformConfig)
    wechat: PlatformConfig = Field(default_factory=PlatformConfig)

    # MCP
    mcp: MCPConfig = Field(default_factory=MCPConfig)

    # LLM
    llm: LLMConfig = Field(default_factory=LLMConfig)

    # Search
    search: SearchConfig = Field(default_factory=SearchConfig)

    # Proxy
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)

    # Debug
    debug: bool = False


def load_config() -> AppConfig:
    """Load configuration from file and environment."""
    config = AppConfig()

    # Try to load from yaml file
    config_path = Path("config/settings.yaml")
    if config_path.exists():
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                # Override with yaml values
                if "gateway" in yaml_config:
                    config.gateway = GatewayConfig(**yaml_config["gateway"])
                if "platforms" in yaml_config:
                    if "telegram" in yaml_config["platforms"]:
                        config.telegram = PlatformConfig(**yaml_config["platforms"]["telegram"])
                    if "feishu" in yaml_config["platforms"]:
                        config.feishu = PlatformConfig(**yaml_config["platforms"]["feishu"])
                    if "wechat" in yaml_config["platforms"]:
                        config.wechat = PlatformConfig(**yaml_config["platforms"]["wechat"])
                if "llm" in yaml_config:
                    config.llm = LLMConfig(**yaml_config["llm"])
                if "search" in yaml_config:
                    config.search = SearchConfig(**yaml_config["search"])

    return resolve_config_env_vars(config)

"""
Configuration validation utilities
"""
from typing import List, Tuple


def validate_config(config: dict) -> List[Tuple[str, str]]:
    """
    Validate configuration and return list of issues.

    Returns:
        List of (severity, message) tuples
    """
    issues = []

    # Check required environment variables
    required_env_vars = []

    # Check platform configurations
    if config.get("telegram", {}).get("enabled"):
        if not config["telegram"].get("bot_token"):
            issues.append(("error", "TELEGRAM_BOT_TOKEN is required when Telegram is enabled"))

    if config.get("feishu", {}).get("enabled"):
        if not config["feishu"].get("app_id"):
            issues.append(("error", "FEISHU_APP_ID is required when Feishu is enabled"))
        if not config["feishu"].get("app_secret"):
            issues.append(("error", "FEISHU_APP_SECRET is required when Feishu is enabled"))

    if config.get("wechat", {}).get("enabled"):
        if not config["wechat"].get("webhook_url"):
            issues.append(("warning", "WECHAT_WEBHOOK_URL not set - WeChat webhook mode will be limited"))

    # Check LLM configuration
    if not config.get("llm", {}).get("api_key"):
        issues.append(("warning", "OPENAI_API_KEY not set - LLM functionality will not work"))

    # Check search configuration
    search_config = config.get("search", {})
    if not search_config.get("tavily_api_key") and not search_config.get("google_api_key"):
        issues.append(("warning", "No search API keys configured - search functionality will not work"))

    return issues


def print_config_issues(issues: List[Tuple[str, str]]):
    """Print configuration issues in a readable format."""
    if not issues:
        print("✓ Configuration looks good!")
        return

    print("\nConfiguration Issues:")
    print("=" * 50)

    errors = [i for i in issues if i[0] == "error"]
    warnings = [i for i in issues if i[0] == "warning"]

    if errors:
        print("\nErrors (must fix):")
        for _, msg in errors:
            print(f"  ✗ {msg}")

    if warnings:
        print("\nWarnings (recommended to fix):")
        for _, msg in warnings:
            print(f"  ⚠ {msg}")

    print()

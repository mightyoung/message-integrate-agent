"""
LLM chat tool for MCP
"""
import os
from typing import Optional

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


def _get_proxies() -> dict:
    """Get proxy configuration from environment."""
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    proxies = {}
    if http_proxy:
        proxies["http://"] = http_proxy
    if https_proxy:
        proxies["https://"] = https_proxy

    return proxies if proxies else None


async def chat_with_llm(
    prompt: str,
    model: str = "gpt-4",
    system_message: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> str:
    """
    Chat with LLM (OpenAI-compatible API).

    Args:
        prompt: User prompt
        model: Model name (gpt-4, gpt-3.5-turbo, etc.)
        system_message: Optional system message
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response

    Returns:
        LLM response text
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    if not api_key:
        return "Error: OPENAI_API_KEY not configured"

    # Build messages
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    # Get proxy settings
    proxies = _get_proxies()

    # Build httpx client kwargs
    client_kwargs = {"timeout": 60.0}
    if proxies:
        # httpx 0.27+ uses 'proxy' singular
        try:
            import httpx
            if hasattr(httpx, '__version__') and tuple(map(int, httpx.__version__.split('.')[:2])) >= (0, 27):
                client_kwargs["proxy"] = list(proxies.values())[0] if proxies else None
            else:
                client_kwargs["proxies"] = proxies
        except (AttributeError, ValueError, TypeError):
            # Fallback to proxies dict for older versions
            client_kwargs["proxies"] = proxies

    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return "No response generated"
            else:
                error_msg = f"API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('error', {}).get('message', '')}"
                except Exception:
                    pass
                return f"Error: {error_msg}"

    except httpx.TimeoutException:
        return "Error: Request timed out"
    except Exception as e:
        logger.error(f"LLM chat error: {e}")
        return f"Error: {str(e)}"


async def chat_with_anthropic(
    prompt: str,
    model: str = "claude-3-opus-20240229",
    system_message: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> str:
    """
    Chat with Anthropic Claude API.

    Args:
        prompt: User prompt
        model: Model name
        system_message: Optional system message
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response

    Returns:
        LLM response text
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        return "Error: ANTHROPIC_API_KEY not configured"

    # Build messages
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    # Get proxy settings
    proxies = _get_proxies()

    # Build httpx client kwargs
    client_kwargs = {"timeout": 60.0}
    if proxies:
        # httpx 0.27+ uses 'proxy' singular
        try:
            import httpx
            if hasattr(httpx, '__version__') and tuple(map(int, httpx.__version__.split('.')[:2])) >= (0, 27):
                client_kwargs["proxy"] = list(proxies.values())[0] if proxies else None
            else:
                client_kwargs["proxies"] = proxies
        except (AttributeError, ValueError, TypeError):
            # Fallback to proxies dict for older versions
            client_kwargs["proxies"] = proxies

    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("content", [{}])[0].get("text", "")
            else:
                return f"Error: API error {response.status_code}"

    except Exception as e:
        logger.error(f"Anthropic chat error: {e}")
        return f"Error: {str(e)}"

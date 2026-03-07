"""
Web search tool for MCP
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


def _create_client(proxies: dict = None) -> httpx.AsyncClient:
    """Create httpx AsyncClient with proper proxy handling."""
    client_kwargs = {"timeout": 30.0}
    if proxies:
        try:
            if hasattr(httpx, '__version__') and tuple(map(int, httpx.__version__.split('.')[:2])) >= (0, 27):
                client_kwargs["proxy"] = list(proxies.values())[0] if proxies else None
            else:
                client_kwargs["proxies"] = proxies
        except (AttributeError, ValueError, TypeError) as e:
            # Fallback to proxies dict for older versions
            client_kwargs["proxies"] = proxies
    return httpx.AsyncClient(**client_kwargs)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True
)
async def _search_with_retry(client: httpx.AsyncClient, method: str, *args, **kwargs) -> httpx.Response:
    """Execute search with retry logic."""
    if method.upper() == "GET":
        return await client.get(*args, **kwargs)
    elif method.upper() == "POST":
        return await client.post(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")


async def search_web(
    query: str,
    engine: str = "tavily",
    max_results: int = 5
) -> str:
    """
    Search the web using various search engines.

    Args:
        query: Search query
        engine: Search engine (tavily, google, duckduckgo)
        max_results: Maximum number of results

    Returns:
        Formatted search results
    """
    results = []

    if engine == "tavily":
        results = await _search_tavily(query, max_results)
    elif engine == "google":
        results = await _search_google(query, max_results)
    elif engine == "duckduckgo":
        results = await _search_duckduckgo(query, max_results)
    else:
        return f"Unknown search engine: {engine}"

    if not results:
        return "No results found."

    # Format results
    output = ["## Search Results\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        content = r.get("content", "")[:200]

        output.append(f"### {i}. {title}")
        output.append(f"   {url}")
        if content:
            output.append(f"   {content}...")
        output.append("")

    return "\n".join(output)


async def _search_tavily(query: str, max_results: int) -> list[dict]:
    """Search using Tavily API with retry."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return [{"title": "Error", "url": "", "content": "TAVILY_API_KEY not configured"}]

    try:
        proxies = _get_proxies()

        async with _create_client(proxies) as client:
            response = await _search_with_retry(
                client,
                "POST",
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": True,
                    "include_raw_content": False,
                }
            )
            if response.status_code == 200:
                data = response.json()
                results = []

                # Add AI answer if available
                if data.get("answer"):
                    results.append({
                        "title": "AI Answer",
                        "url": "",
                        "content": data["answer"]
                    })

                # Add search results
                for r in data.get("results", []):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", ""),
                    })

                return results[:max_results]
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return [{"title": "Error", "url": "", "content": str(e)}]

    return []


async def _search_google(query: str, max_results: int) -> list[dict]:
    """Search using Google Custom Search API with retry."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        return [{"title": "Error", "url": "", "content": "Google API credentials not configured"}]

    try:
        proxies = _get_proxies()

        async with _create_client(proxies) as client:
            response = await _search_with_retry(
                client,
                "GET",
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": api_key,
                    "cx": cse_id,
                    "q": query,
                    "num": max_results,
                }
            )
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("items", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "content": item.get("snippet", ""),
                    })
                return results
    except Exception as e:
        logger.error(f"Google search error: {e}")

    return []


async def _search_duckduckgo(query: str, max_results: int) -> list[dict]:
    """Search using DuckDuckGo with retry."""
    try:
        proxies = _get_proxies()

        async with _create_client(proxies) as client:
            response = await _search_with_retry(
                client,
                "GET",
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1,
                }
            )
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("RelatedTopics", []):
                    if isinstance(item, dict):
                        results.append({
                            "title": item.get("Text", ""),
                            "url": item.get("URL", ""),
                            "content": "",
                        })
                        if len(results) >= max_results:
                            break
                return results
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")

    return []

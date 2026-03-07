"""
Proxy manager for handling HTTP/SOCKS proxies
"""
import os
from pathlib import Path
from typing import Optional

import httpx
import yaml
from loguru import logger


class ProxyManager:
    """
    Manages proxy configuration and provides HTTP client with proxy support.
    """

    def __init__(self, config_path: str = "config/proxy.yaml"):
        self.config_path = Path(config_path)
        self.config: dict = {}
        self._load_config()

        # Get proxy from environment
        self.http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        self.https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        self.no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy", "localhost,127.0.0.1")

        logger.info(f"Proxy configured - HTTP: {self.http_proxy}, HTTPS: {self.https_proxy}")

    def _load_config(self):
        """Load proxy configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f) or {}
                logger.info(f"Proxy config loaded from {self.config_path}")
        else:
            logger.warning(f"Proxy config not found at {self.config_path}")

    def get_client(self) -> httpx.Client:
        """
        Get an HTTP client with proxy configuration.

        Returns:
            Configured httpx.Client
        """
        proxies = {}

        if self.http_proxy:
            proxies["http://"] = self.http_proxy
        if self.https_proxy:
            proxies["https://"] = self.https_proxy

        if proxies:
            return httpx.Client(proxies=proxies, timeout=30.0)
        else:
            return httpx.Client(timeout=30.0)

    def get_async_client(self) -> httpx.AsyncClient:
        """
        Get an async HTTP client with proxy configuration.

        Returns:
            Configured httpx.AsyncClient
        """
        proxies = {}

        if self.http_proxy:
            proxies["http://"] = self.http_proxy
        if self.https_proxy:
            proxies["https://"] = self.https_proxy

        if proxies:
            return httpx.AsyncClient(proxies=proxies, timeout=30.0)
        else:
            return httpx.AsyncClient(timeout=30.0)

    def should_use_proxy(self, url: str) -> bool:
        """
        Determine if a URL should use proxy based on routing rules.

        Args:
            url: The URL to check

        Returns:
            True if should use proxy, False otherwise
        """
        if not self.config.get("routing"):
            # No routing rules, use proxy if configured
            return bool(self.https_proxy or self.http_proxy)

        routing = self.config["routing"]
        proxy_domains = routing.get("proxy_domains", [])
        direct_domains = routing.get("direct_domains", [])

        # Check direct list first
        for domain in direct_domains:
            if self._match_domain(url, domain):
                return False

        # Check proxy list
        for domain in proxy_domains:
            if self._match_domain(url, domain):
                return True

        # Use fallback
        fallback = routing.get("fallback", "direct")
        return fallback == "proxy"

    def _match_domain(self, url: str, pattern: str) -> bool:
        """Check if URL matches domain pattern."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.netloc.lower()

        # Simple wildcard matching
        if pattern.startswith("*."):
            domain = pattern[2:]
            return host.endswith(domain) or host == domain[1:]
        else:
            return host == pattern or host.endswith(f".{pattern}")

    def get_proxied_client(self, url: str) -> httpx.Client:
        """
        Get HTTP client configured based on URL.

        Args:
            url: The target URL

        Returns:
            Client with appropriate proxy settings
        """
        if self.should_use_proxy(url):
            return self.get_client()
        else:
            return httpx.Client(timeout=30.0)

    def get_proxied_async_client(self, url: str) -> httpx.AsyncClient:
        """
        Get async HTTP client configured based on URL.

        Args:
            url: The target URL

        Returns:
            AsyncClient with appropriate proxy settings
        """
        if self.should_use_proxy(url):
            return self.get_async_client()
        else:
            return httpx.AsyncClient(timeout=30.0)

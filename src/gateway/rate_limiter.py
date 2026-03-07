"""
Rate limiting for the Gateway.

Implements a sliding window rate limiter inspired by OpenClaw:
- Sliding window algorithm
- Per-client tracking
- Automatic cleanup
- Loopback exemption

参考 OpenClaw: https://github.com/openclaw/openclaw/blob/main/src/gateway/auth-rate-limit.ts
"""
import time
from dataclasses import dataclass, field
from typing import Dict, Optional
from loguru import logger


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    max_attempts: int = 10  # Maximum attempts in window
    window_ms: int = 60_000  # 1 minute window
    lockout_ms: int = 300_000  # 5 minute lockout
    exempt_loopback: bool = True  # Exempt localhost
    prune_interval_ms: int = 60_000  # Auto-prune interval


@dataclass
class RateLimitEntry:
    """Rate limit tracking entry."""
    attempts: list[float] = field(default_factory=list)
    locked_until: Optional[float] = None


class RateLimiter:
    """
    Sliding window rate limiter.

    Design decisions:
    - Pure in-memory - no external dependencies
    - Loopback addresses exempt by default
    - Automatic pruning to avoid memory growth

    Usage:
        limiter = RateLimiter(max_attempts=10, window_ms=60000)

        # Check if allowed
        result = limiter.check(client_id)
        if not result.allowed:
            print(f"Rate limited, retry after {result.retry_after_ms}ms")

        # Record failure
        limiter.record_failure(client_id)

        # Reset after success
        limiter.reset(client_id)
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._entries: Dict[str, RateLimitEntry] = {}
        self._last_prune = time.time()

    def _is_loopback(self, client_id: str) -> bool:
        """Check if client ID is a loopback address."""
        loopback_prefixes = ("127.", "::1", "localhost", "0.0.0.0", "::")
        return client_id.startswith(loopback_prefixes) or client_id == "localhost"

    def check(self, client_id: str) -> Dict:
        """
        Check if a client is allowed to proceed.

        Args:
            client_id: Unique client identifier (IP, user ID, etc.)

        Returns:
            Dict with keys:
            - allowed: bool
            - remaining: int
            - retry_after_ms: int
        """
        # Exempt loopback addresses
        if self.config.exempt_loopback and self._is_loopback(client_id):
            return {
                "allowed": True,
                "remaining": self.config.max_attempts,
                "retry_after_ms": 0,
            }

        now = time.time()

        # Get or create entry
        if client_id not in self._entries:
            self._entries[client_id] = RateLimitEntry()

        entry = self._entries[client_id]

        # Check if currently locked out
        if entry.locked_until and now < entry.locked_until:
            retry_after_ms = int((entry.locked_until - now) * 1000)
            return {
                "allowed": False,
                "remaining": 0,
                "retry_after_ms": retry_after_ms,
            }

        # Clean expired attempts from window
        window_start = now - (self.config.window_ms / 1000)
        entry.attempts = [t for t in entry.attempts if t > window_start]

        current_attempts = len(entry.attempts)

        # Check if over limit
        if current_attempts >= self.config.max_attempts:
            # Lock out the client
            entry.locked_until = now + (self.config.lockout_ms / 1000)
            return {
                "allowed": False,
                "remaining": 0,
                "retry_after_ms": self.config.lockout_ms,
            }

        # Record this attempt
        entry.attempts.append(now)

        # Allowed - return remaining attempts
        remaining = self.config.max_attempts - current_attempts - 1
        return {
            "allowed": True,
            "remaining": max(0, remaining),
            "retry_after_ms": 0,
        }

    def record_failure(self, client_id: str) -> None:
        """
        Record a failed attempt for a client.

        Args:
            client_id: Unique client identifier
        """
        # Exempt loopback
        if self.config.exempt_loopback and self._is_loopback(client_id):
            return

        now = time.time()

        # Get or create entry
        if client_id not in self._entries:
            self._entries[client_id] = RateLimitEntry()

        entry = self._entries[client_id]

        # If locked, don't record more failures
        if entry.locked_until and now < entry.locked_until:
            return

        # Add attempt timestamp
        entry.attempts.append(now)

        # Reset lockout
        entry.locked_until = None

        # Auto-prune if needed
        self._maybe_prune()

    def reset(self, client_id: str) -> None:
        """
        Reset rate limit for a client (e.g., after successful auth).

        Args:
            client_id: Unique client identifier
        """
        if client_id in self._entries:
            del self._entries[client_id]

    def size(self) -> int:
        """Return number of tracked clients."""
        return len(self._entries)

    def _maybe_prune(self) -> None:
        """Prune expired entries if interval has passed."""
        now = time.time()
        if now - self._last_prune < (self.config.prune_interval_ms / 1000):
            return

        self.prune()
        self._last_prune = now

    def prune(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        now = time.time()
        window_start = now - (self.config.window_ms / 1000)
        lockout_window = now - (self.config.lockout_ms / 1000)

        removed = 0
        to_remove = []

        for client_id, entry in self._entries.items():
            # Remove if no recent attempts and not locked
            if not entry.attempts or all(t < window_start for t in entry.attempts):
                if not entry.locked_until or entry.locked_until < lockout_window:
                    to_remove.append(client_id)

        for client_id in to_remove:
            del self._entries[client_id]
            removed += 1

        if removed > 0:
            logger.debug(f"Rate limiter pruned {removed} expired entries")

        return removed

    def dispose(self) -> None:
        """Clean up resources."""
        self._entries.clear()


class MultiScopeRateLimiter:
    """
    Rate limiter with multiple scopes.

    Allows separate rate limiting for different credential classes
    while sharing one limiter instance.

    Usage:
        limiter = MultiScopeRateLimiter()

        # Check with different scopes
        limiter.check("client_ip", scope="login")
        limiter.check("client_ip", scope="api")
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._limiters: Dict[str, RateLimiter] = {}

    def _get_limiter(self, scope: str) -> RateLimiter:
        """Get or create limiter for scope."""
        if scope not in self._limiters:
            self._limiters[scope] = RateLimiter(self.config)
        return self._limiters[scope]

    def check(self, client_id: str, scope: str = "default") -> Dict:
        """Check rate limit for a scope."""
        return self._get_limiter(scope).check(client_id)

    def record_failure(self, client_id: str, scope: str = "default") -> None:
        """Record failure for a scope."""
        self._get_limiter(scope).record_failure(client_id)

    def reset(self, client_id: str, scope: str = "default") -> None:
        """Reset rate limit for a scope."""
        self._get_limiter(scope).reset(client_id)

    def prune(self) -> int:
        """Prune all scopes."""
        total = 0
        for limiter in self._limiters.values():
            total += limiter.prune()
        return total

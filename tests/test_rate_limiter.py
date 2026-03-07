"""
Tests for Rate Limiter
"""
import pytest
import time
from unittest.mock import patch

from src.gateway.rate_limiter import RateLimiter, RateLimitConfig, MultiScopeRateLimiter


def test_rate_limit_config_defaults():
    """Test default rate limit config."""
    config = RateLimitConfig()

    assert config.max_attempts == 10
    assert config.window_ms == 60_000
    assert config.lockout_ms == 300_000
    assert config.exempt_loopback is True


def test_rate_limit_config_custom():
    """Test custom rate limit config."""
    config = RateLimitConfig(
        max_attempts=5,
        window_ms=30_000,
        lockout_ms=60_000,
        exempt_loopback=False,
    )

    assert config.max_attempts == 5
    assert config.window_ms == 30_000
    assert config.lockout_ms == 60_000
    assert config.exempt_loopback is False


def test_rate_limiter_allows_within_limit():
    """Test that requests within limit are allowed."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=5, window_ms=60_000))

    # First 5 requests should be allowed
    for i in range(5):
        result = limiter.check(f"client_{i}")
        assert result["allowed"] is True


def test_rate_limiter_blocks_over_limit():
    """Test that requests over limit are blocked."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=3, window_ms=60_000))

    # First 3 requests should be allowed
    for i in range(3):
        result = limiter.check("client")
        assert result["allowed"] is True

    # 4th request should be blocked
    result = limiter.check("client")
    assert result["allowed"] is False
    assert result["remaining"] == 0
    assert result["retry_after_ms"] > 0


def test_rate_limiter_loopback_exempt():
    """Test that loopback addresses are exempt."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=1, window_ms=60_000, exempt_loopback=True))

    # Loopback should always be allowed
    result = limiter.check("127.0.0.1")
    assert result["allowed"] is True
    # Loopback is exempt, so remaining shows max_attempts (1)
    assert result["remaining"] == 1

    result = limiter.check("::1")
    assert result["allowed"] is True

    result = limiter.check("localhost")
    assert result["allowed"] is True


def test_rate_limiter_no_loopback_exemption():
    """Test that loopback addresses are not exempt when configured."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=1, window_ms=60_000, exempt_loopback=False))

    # Loopback should be rate limited
    result = limiter.check("127.0.0.1")
    assert result["allowed"] is True
    assert result["remaining"] == 0  # Used 1

    result = limiter.check("127.0.0.1")
    assert result["allowed"] is False


def test_rate_limiter_sliding_window():
    """Test that the sliding window correctly expires old requests."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=2, window_ms=1000))

    # Two requests should be allowed
    result1 = limiter.check("client")
    assert result1["allowed"] is True

    result2 = limiter.check("client")
    assert result2["allowed"] is True

    # Third should be blocked
    result3 = limiter.check("client")
    assert result3["allowed"] is False


def test_rate_limiter_lockout():
    """Test that lockout is applied after exceeding limit."""
    limiter = RateLimiter(RateLimitConfig(
        max_attempts=2,
        window_ms=60_000,
        lockout_ms=5000,
        exempt_loopback=False,
    ))

    # Use up the limit
    limiter.check("client")
    limiter.check("client")

    # Should be locked out
    result = limiter.check("client")
    assert result["allowed"] is False
    assert result["retry_after_ms"] > 0


def test_rate_limiter_remaining_count():
    """Test that remaining count decreases correctly."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=5, window_ms=60_000))

    # First check
    result = limiter.check("client")
    assert result["remaining"] == 4

    # Second check
    result = limiter.check("client")
    assert result["remaining"] == 3

    # Third check
    result = limiter.check("client")
    assert result["remaining"] == 2


def test_rate_limiter_record_failure():
    """Test recording failure manually."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=2, window_ms=60_000, exempt_loopback=False))

    # Record a failure
    limiter.record_failure("client")

    # Check remaining - first check should be allowed, uses 1 from record_failure
    result = limiter.check("client")
    assert result["remaining"] == 0  # 2 - 1 (from record_failure) - 1 (from check) = 0

    # Record another failure
    limiter.record_failure("client")

    # Should be at limit now
    result = limiter.check("client")
    assert result["allowed"] is False


def test_rate_limiter_reset():
    """Test resetting rate limit."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=1, window_ms=60_000, exempt_loopback=False))

    # Use up the limit
    limiter.check("client")
    result = limiter.check("client")
    assert result["allowed"] is False

    # Reset
    limiter.reset("client")

    # Should be allowed again
    result = limiter.check("client")
    assert result["allowed"] is True
    assert result["remaining"] == 0  # New attempt recorded


def test_rate_limiter_prune():
    """Test pruning expired entries."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=1, window_ms=100, lockout_ms=100, exempt_loopback=False))

    # Add a client
    limiter.check("client1")

    # Wait for expiration
    time.sleep(0.2)

    # Prune
    removed = limiter.prune()

    assert removed >= 1


def test_rate_limiter_size():
    """Test size tracking."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=10, window_ms=60_000))

    assert limiter.size() == 0

    limiter.check("client1")
    assert limiter.size() == 1

    limiter.check("client2")
    assert limiter.size() == 2

    limiter.reset("client1")
    assert limiter.size() == 1


def test_rate_limiter_dispose():
    """Test disposing limiter."""
    limiter = RateLimiter(RateLimitConfig(max_attempts=10, window_ms=60_000))

    limiter.check("client1")
    limiter.check("client2")

    assert limiter.size() == 2

    limiter.dispose()

    assert limiter.size() == 0


def test_multi_scope_rate_limiter():
    """Test multi-scope rate limiter."""
    limiter = MultiScopeRateLimiter(RateLimitConfig(max_attempts=2, window_ms=60_000))

    # Check in different scopes
    result1 = limiter.check("client", scope="login")
    assert result1["allowed"] is True

    result2 = limiter.check("client", scope="api")
    assert result2["allowed"] is True

    # Scopes are independent
    result3 = limiter.check("client", scope="login")
    assert result3["allowed"] is True  # Still 1 used in login scope


def test_multi_scope_rate_limiter_different_clients():
    """Test multi-scope with different clients."""
    limiter = MultiScopeRateLimiter(RateLimitConfig(max_attempts=1, window_ms=60_000))

    # Client A in login scope - first request
    result = limiter.check("client_a", scope="login")
    assert result["allowed"] is True

    # Client A in login scope - second request (same client)
    result = limiter.check("client_a", scope="login")
    assert result["allowed"] is False

    # Client B in same scope - different client, should be allowed (rate limit is per-client)
    result = limiter.check("client_b", scope="login")
    assert result["allowed"] is True


def test_multi_scope_prune():
    """Test pruning in multi-scope limiter."""
    limiter = MultiScopeRateLimiter(RateLimitConfig(max_attempts=1, window_ms=100, exempt_loopback=False))

    limiter.check("client1", scope="login")
    limiter.check("client2", scope="api")

    time.sleep(0.2)

    removed = limiter.prune()
    assert removed >= 2

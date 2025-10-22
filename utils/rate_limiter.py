#!/usr/bin/env python3
"""
Rate Limiter for LLM API Calls

Prevents hitting API rate limits by adding delays between calls.
Useful for free tier API access.
"""

import time
import os
from datetime import datetime, timedelta
from typing import Optional, Callable, Any


class RateLimiter:
    """
    Rate limiter for API calls

    Supports two modes:
    1. Simple delay: Wait X seconds between each call
    2. Token bucket: Allow bursts with rate limiting
    """

    def __init__(
        self,
        calls_per_minute: int = None,
        delay_between_calls: float = None,
        mode: str = "auto"
    ):
        """
        Initialize rate limiter

        Args:
            calls_per_minute: Maximum calls per minute (for token bucket mode)
            delay_between_calls: Fixed delay in seconds between calls (for simple mode)
            mode: "simple" (fixed delay), "bucket" (token bucket), or "auto" (read from env)
        """
        # Read from environment if auto mode
        if mode == "auto":
            enable_rate_limiting = os.getenv('ENABLE_RATE_LIMITING', 'false').lower() == 'true'

            if not enable_rate_limiting:
                # Disabled - no delays
                self.mode = "disabled"
                self.delay_between_calls = 0
                self.calls_per_minute = None
            else:
                # Check which mode to use
                delay_env = os.getenv('API_DELAY_SECONDS')
                rate_env = os.getenv('API_CALLS_PER_MINUTE')

                if delay_env:
                    self.mode = "simple"
                    self.delay_between_calls = float(delay_env)
                    self.calls_per_minute = None
                elif rate_env:
                    self.mode = "bucket"
                    self.calls_per_minute = int(rate_env)
                    self.delay_between_calls = None
                else:
                    # Default: 15 calls per minute (free tier safe)
                    self.mode = "bucket"
                    self.calls_per_minute = 15
                    self.delay_between_calls = None
        else:
            self.mode = mode
            self.calls_per_minute = calls_per_minute
            self.delay_between_calls = delay_between_calls

        # Track last call time
        self.last_call_time = None

        # Token bucket state
        if self.mode == "bucket":
            self.tokens = self.calls_per_minute
            self.last_refill = datetime.now()

        # Statistics
        self.total_calls = 0
        self.total_wait_time = 0

        # Print configuration
        if self.mode != "disabled":
            print(f"⏱️  Rate limiter enabled ({self.mode} mode)")
            if self.mode == "simple":
                print(f"   Delay between calls: {self.delay_between_calls}s")
            elif self.mode == "bucket":
                print(f"   Max calls per minute: {self.calls_per_minute}")

    def wait_if_needed(self):
        """Wait if necessary before making next API call"""
        if self.mode == "disabled":
            return

        if self.mode == "simple":
            self._simple_delay()
        elif self.mode == "bucket":
            self._token_bucket_wait()

        self.total_calls += 1

    def _simple_delay(self):
        """Simple fixed delay between calls"""
        if self.last_call_time is not None:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.delay_between_calls:
                wait_time = self.delay_between_calls - elapsed
                print(f"   ⏳ Rate limit: waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.total_wait_time += wait_time

        self.last_call_time = time.time()

    def _token_bucket_wait(self):
        """Token bucket rate limiting (allows bursts)"""
        # Refill tokens
        now = datetime.now()
        elapsed = (now - self.last_refill).total_seconds()

        # Refill rate: calls_per_minute tokens per 60 seconds
        tokens_to_add = (elapsed / 60.0) * self.calls_per_minute
        self.tokens = min(self.calls_per_minute, self.tokens + tokens_to_add)
        self.last_refill = now

        # Check if we have tokens
        if self.tokens < 1:
            # Need to wait for a token
            wait_time = (1 - self.tokens) * (60.0 / self.calls_per_minute)
            print(f"   ⏳ Rate limit: waiting {wait_time:.1f}s for next API call...")
            time.sleep(wait_time)
            self.total_wait_time += wait_time
            self.tokens = 1

        # Consume token
        self.tokens -= 1
        self.last_call_time = time.time()

    def call_with_limit(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with rate limiting

        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result
        """
        self.wait_if_needed()
        return func(*args, **kwargs)

    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        return {
            "mode": self.mode,
            "total_calls": self.total_calls,
            "total_wait_time": self.total_wait_time,
            "avg_wait_time": self.total_wait_time / self.total_calls if self.total_calls > 0 else 0
        }

    def print_stats(self):
        """Print rate limiter statistics"""
        if self.mode == "disabled" or self.total_calls == 0:
            return

        stats = self.get_stats()
        print(f"\n⏱️  Rate Limiter Statistics:")
        print(f"   Total API calls: {stats['total_calls']}")
        print(f"   Total wait time: {stats['total_wait_time']:.1f}s")
        print(f"   Avg wait per call: {stats['avg_wait_time']:.2f}s")


# Global rate limiters (one for LLM, one for embeddings)
_llm_limiter: Optional[RateLimiter] = None
_embedding_limiter: Optional[RateLimiter] = None


def get_llm_rate_limiter() -> RateLimiter:
    """Get or create LLM rate limiter"""
    global _llm_limiter
    if _llm_limiter is None:
        # Read from env or use defaults
        _llm_limiter = RateLimiter(mode="auto")
    return _llm_limiter


def get_embedding_rate_limiter() -> RateLimiter:
    """Get or create embedding rate limiter"""
    global _embedding_limiter
    if _embedding_limiter is None:
        # Embeddings are usually much cheaper, use separate limiter
        delay = float(os.getenv('EMBEDDING_DELAY_SECONDS', '0.1'))  # Small delay by default
        _embedding_limiter = RateLimiter(delay_between_calls=delay, mode="simple")
    return _embedding_limiter


def reset_limiters():
    """Reset all rate limiters (useful for testing)"""
    global _llm_limiter, _embedding_limiter
    _llm_limiter = None
    _embedding_limiter = None


# Convenience decorators
def rate_limited_llm(func):
    """Decorator to rate limit LLM calls"""
    def wrapper(*args, **kwargs):
        limiter = get_llm_rate_limiter()
        return limiter.call_with_limit(func, *args, **kwargs)
    return wrapper


def rate_limited_embedding(func):
    """Decorator to rate limit embedding calls"""
    def wrapper(*args, **kwargs):
        limiter = get_embedding_rate_limiter()
        return limiter.call_with_limit(func, *args, **kwargs)
    return wrapper

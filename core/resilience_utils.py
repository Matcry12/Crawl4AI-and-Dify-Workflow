"""
Error Resilience & Recovery Utilities

This module provides retry logic, checkpointing, and failure recovery
mechanisms for the crawl workflow.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from functools import wraps
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


# ============================================================================
# RETRY LOGIC WITH EXPONENTIAL BACKOFF
# ============================================================================

class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def should_retry(exception: Exception) -> bool:
    """Determine if an exception is retryable"""
    # Network errors - retry
    if isinstance(exception, (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.HTTPError
    )):
        return True

    # HTTP status codes that should be retried
    if hasattr(exception, 'response') and exception.response is not None:
        status = exception.response.status_code
        # Retry on server errors (5xx) and rate limiting (429)
        if status >= 500 or status == 429:
            return True
        # Don't retry on client errors (4xx) except 429
        if 400 <= status < 500:
            return False

    return False


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay with exponential backoff"""
    delay = min(
        config.initial_delay * (config.exponential_base ** attempt),
        config.max_delay
    )

    # Add jitter to prevent thundering herd
    if config.jitter:
        import random
        delay = delay * (0.5 + random.random())

    return delay


def with_retry(config: Optional[RetryConfig] = None):
    """Decorator to add retry logic to functions"""
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not should_retry(e):
                        logger.warning(f"Non-retryable error in {func.__name__}: {e}")
                        raise

                    if attempt < config.max_attempts - 1:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not should_retry(e):
                        logger.warning(f"Non-retryable error in {func.__name__}: {e}")
                        raise

                    if attempt < config.max_attempts - 1:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# CIRCUIT BREAKER PATTERN
# ============================================================================

class CircuitBreakerState:
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker to prevent cascade failures"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception(f"Circuit breaker OPEN: Service unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info("Circuit breaker recovered, entering CLOSED state")
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitBreakerState.OPEN:
                logger.error(
                    f"Circuit breaker OPEN after {self.failure_count} failures"
                )
            self.state = CircuitBreakerState.OPEN


# ============================================================================
# CHECKPOINT & RESUME SYSTEM
# ============================================================================

class CrawlCheckpoint:
    """Manages crawl state for crash recovery"""

    def __init__(self, checkpoint_file: str = "crawl_checkpoint.json"):
        self.checkpoint_file = Path(checkpoint_file)
        self.state: Dict[str, Any] = {
            'version': '1.0',
            'start_time': None,
            'last_update': None,
            'processed_urls': [],
            'pending_urls': [],
            'failed_urls': [],
            'knowledge_bases': {},
            'statistics': {
                'total_urls': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0
            }
        }

    def save(self):
        """Save checkpoint to disk"""
        try:
            self.state['last_update'] = datetime.now().isoformat()
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"Checkpoint saved: {len(self.state['processed_urls'])} processed")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load(self) -> bool:
        """Load checkpoint from disk"""
        try:
            if not self.checkpoint_file.exists():
                logger.info("No checkpoint found, starting fresh")
                return False

            with open(self.checkpoint_file, 'r') as f:
                self.state = json.load(f)

            logger.info(
                f"Checkpoint loaded: {len(self.state['processed_urls'])} URLs processed, "
                f"{len(self.state['pending_urls'])} pending"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return False

    def initialize(self, start_url: str, total_urls: int = 0):
        """Initialize new crawl session"""
        self.state['start_time'] = datetime.now().isoformat()
        self.state['start_url'] = start_url
        self.state['statistics']['total_urls'] = total_urls
        self.save()

    def mark_processed(self, url: str, success: bool = True):
        """Mark URL as processed"""
        if url not in self.state['processed_urls']:
            self.state['processed_urls'].append(url)

        if success:
            self.state['statistics']['successful'] += 1
        else:
            self.state['statistics']['failed'] += 1

        # Remove from pending if present
        if url in self.state['pending_urls']:
            self.state['pending_urls'].remove(url)

    def mark_failed(self, url: str, error: str):
        """Mark URL as failed"""
        if url not in self.state['failed_urls']:
            self.state['failed_urls'].append(url)
        self.mark_processed(url, success=False)

    def mark_skipped(self, url: str):
        """Mark URL as skipped (duplicate)"""
        self.state['statistics']['skipped'] += 1
        self.mark_processed(url, success=True)

    def add_pending(self, urls: List[str]):
        """Add URLs to pending queue"""
        for url in urls:
            if url not in self.state['processed_urls'] and url not in self.state['pending_urls']:
                self.state['pending_urls'].append(url)

    def get_pending_urls(self) -> List[str]:
        """Get list of pending URLs"""
        return self.state['pending_urls'].copy()

    def is_processed(self, url: str) -> bool:
        """Check if URL was already processed"""
        return url in self.state['processed_urls']

    def update_kb_info(self, kb_name: str, kb_id: str):
        """Update knowledge base information"""
        self.state['knowledge_bases'][kb_name] = kb_id

    def get_statistics(self) -> Dict[str, Any]:
        """Get crawl statistics"""
        return self.state['statistics'].copy()

    def clear(self):
        """Clear checkpoint (start fresh)"""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        self.__init__(str(self.checkpoint_file))
        logger.info("Checkpoint cleared")


# ============================================================================
# FAILURE QUEUE
# ============================================================================

class FailureQueue:
    """Queue for failed URLs to retry later"""

    def __init__(self, queue_file: str = "failure_queue.json"):
        self.queue_file = Path(queue_file)
        self.failures: List[Dict[str, Any]] = []

    def add(self, url: str, error: str, metadata: Optional[Dict] = None):
        """Add failed URL to queue"""
        failure_record = {
            'url': url,
            'error': str(error),
            'timestamp': datetime.now().isoformat(),
            'retry_count': 0,
            'metadata': metadata or {}
        }
        self.failures.append(failure_record)
        self._save()
        logger.debug(f"Added to failure queue: {url}")

    def _save(self):
        """Save failure queue to disk"""
        try:
            with open(self.queue_file, 'w') as f:
                json.dump(self.failures, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save failure queue: {e}")

    def load(self) -> bool:
        """Load failure queue from disk"""
        try:
            if not self.queue_file.exists():
                return False

            with open(self.queue_file, 'r') as f:
                self.failures = json.load(f)

            logger.info(f"Loaded {len(self.failures)} failed URLs from queue")
            return True
        except Exception as e:
            logger.error(f"Failed to load failure queue: {e}")
            return False

    def get_retryable(self, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Get URLs that should be retried"""
        return [
            f for f in self.failures
            if f['retry_count'] < max_retries
        ]

    def mark_retried(self, url: str):
        """Mark URL as retried"""
        for failure in self.failures:
            if failure['url'] == url:
                failure['retry_count'] += 1
                failure['last_retry'] = datetime.now().isoformat()
        self._save()

    def remove(self, url: str):
        """Remove URL from failure queue (successful retry)"""
        self.failures = [f for f in self.failures if f['url'] != url]
        self._save()

    def clear(self):
        """Clear failure queue"""
        if self.queue_file.exists():
            self.queue_file.unlink()
        self.failures = []
        logger.info("Failure queue cleared")

    def export_report(self, filename: str = "failed_urls_report.json"):
        """Export failure report"""
        report = {
            'total_failures': len(self.failures),
            'timestamp': datetime.now().isoformat(),
            'failures': self.failures
        }
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Failure report exported to {filename}")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: Using retry decorator
    @with_retry(RetryConfig(max_attempts=3, initial_delay=1.0))
    def api_call_with_retry():
        # Simulated API call
        import random
        if random.random() < 0.5:
            raise requests.exceptions.ConnectionError("Network error")
        return "Success"

    # Example: Using circuit breaker
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)

    # Example: Using checkpoint
    checkpoint = CrawlCheckpoint()
    checkpoint.initialize("https://example.com")
    checkpoint.add_pending(["https://example.com/page1", "https://example.com/page2"])
    checkpoint.mark_processed("https://example.com/page1", success=True)
    checkpoint.save()

    # Example: Using failure queue
    failure_queue = FailureQueue()
    failure_queue.add("https://example.com/failed", "Connection timeout")
    failure_queue.export_report()

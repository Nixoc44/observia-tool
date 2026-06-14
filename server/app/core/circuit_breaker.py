import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""


class CircuitBreaker:
    """Simple circuit breaker for external service calls."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: float | None = None
        self.state = CircuitState.CLOSED

    def _maybe_transition_to_half_open(self) -> None:
        if self.state != CircuitState.OPEN or self.last_failure_time is None:
            return
        if (time.monotonic() - self.last_failure_time) >= self.recovery_timeout:
            self.state = CircuitState.HALF_OPEN

    def before_call(self) -> None:
        """Check whether a call is allowed; raise if circuit is open."""
        self._maybe_transition_to_half_open()
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError("Circuit is open")

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.monotonic()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def record_success(self) -> None:
        self.failures = 0
        self.state = CircuitState.CLOSED

    async def execute(self, coro):
        """Execute an async call through the circuit breaker."""
        self.before_call()
        try:
            result = await coro
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def call(self, fn):
        """Execute a sync call through the circuit breaker."""
        self.before_call()
        try:
            result = fn()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

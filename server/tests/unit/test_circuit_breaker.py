"""Unit tests for circuit breaker."""
import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


def test_opens_after_threshold_failures():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
    for _ in range(3):
        cb.record_failure()
    with pytest.raises(CircuitOpenError):
        cb.before_call()


def test_closes_after_success():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_sync_call_success():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
    assert cb.call(lambda: "ok") == "ok"
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_async_execute_success():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

    async def coro():
        return "ok"

    assert await cb.execute(coro()) == "ok"
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_async_execute_records_failure():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30)

    async def failing():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await cb.execute(failing())
    assert cb.state == CircuitState.OPEN

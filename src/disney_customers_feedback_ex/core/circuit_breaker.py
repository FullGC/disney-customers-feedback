"""Circuit breaker pattern for external service calls."""
from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.
    
    Tracks failure rate and opens circuit when threshold is exceeded.
    Automatically attempts to close after timeout period.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: float = 0.5,
        timeout: float = 60.0,
        window_size: int = 10
    ) -> None:
        """Initialize circuit breaker.
        
        Args:
            name: Name of the service being protected.
            failure_threshold: Failure rate to trigger circuit open (0.0-1.0).
            timeout: Seconds to wait before attempting half-open state.
            window_size: Number of recent calls to track.
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.window_size = window_size
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time: float | None = None
        self.last_state_change: float = time.time()
    
    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute.
            *args: Positional arguments for function.
            **kwargs: Keyword arguments for function.
            
        Returns:
            Result of function call.
            
        Raises:
            Exception: If circuit is open or function fails.
        """
        # Check if we should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker {self.name}: Attempting reset (HALF_OPEN)")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = time.time()
            else:
                logger.warning(
                    f"Circuit breaker {self.name}: Circuit OPEN, rejecting call"
                )
                raise Exception(f"Circuit breaker {self.name} is OPEN")
        
        try:
            # Execute the function
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self.successes += 1
        
        # Reset window if needed
        if self.successes + self.failures > self.window_size:
            self._reset_window()
        
        # Transition from HALF_OPEN to CLOSED on success
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker {self.name}: Service recovered (CLOSED)")
            self.state = CircuitState.CLOSED
            self.failures = 0
            self.last_state_change = time.time()
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        # Reset window if needed
        if self.successes + self.failures > self.window_size:
            self._reset_window()
        
        # Check if we should open the circuit
        total_calls = self.successes + self.failures
        if total_calls > 0:
            failure_rate = self.failures / total_calls
            
            if failure_rate >= self.failure_threshold:
                if self.state != CircuitState.OPEN:
                    logger.error(
                        f"Circuit breaker {self.name}: Opening circuit "
                        f"(failure rate: {failure_rate:.2%})"
                    )
                    self.state = CircuitState.OPEN
                    self.last_state_change = time.time()
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset.
        
        Returns:
            True if we should attempt to close the circuit.
        """
        if self.last_failure_time is None:
            return False
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.timeout
    
    def _reset_window(self) -> None:
        """Reset the sliding window of calls."""
        # Keep proportions but reset counts
        total = self.successes + self.failures
        if total > 0:
            success_ratio = self.successes / total
            self.successes = int(self.window_size * success_ratio)
            self.failures = self.window_size - self.successes
    
    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        logger.info(f"Circuit breaker {self.name}: Manual reset")
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = None
        self.last_state_change = time.time()
    
    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state.
        
        Returns:
            Dictionary with state information.
        """
        total_calls = self.successes + self.failures
        failure_rate = self.failures / total_calls if total_calls > 0 else 0.0
        
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "successes": self.successes,
            "failure_rate": failure_rate,
            "last_state_change": self.last_state_change
        }

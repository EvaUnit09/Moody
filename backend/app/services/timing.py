"""Per-stage latency timing for the /recommend pipeline."""

import time
from collections.abc import Iterator
from contextlib import contextmanager


class StageTimer:
    """Records wall-clock milliseconds for each named pipeline stage."""

    def __init__(self) -> None:
        self._start = time.perf_counter()
        self._durations: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        """Time the wrapped block. Records the duration even if the block raises."""
        started = time.perf_counter()
        try:
            yield
        finally:
            self._durations = {**self._durations, name: (time.perf_counter() - started) * 1000}

    @property
    def durations(self) -> dict[str, float]:
        return dict(self._durations)

    def total_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000

    def server_timing_header(self) -> str:
        """Format as a Server-Timing header value, e.g. 'expand;dur=812.4, total;dur=4100.2'."""
        entries = [f"{name};dur={ms:.1f}" for name, ms in self._durations.items()]
        entries.append(f"total;dur={self.total_ms():.1f}")
        return ", ".join(entries)

    def log_line(self) -> str:
        parts = [f"{name}={ms:.0f}ms" for name, ms in self._durations.items()]
        parts.append(f"total={self.total_ms():.0f}ms")
        return " ".join(parts)

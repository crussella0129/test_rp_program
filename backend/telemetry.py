"""Telemetry statistics for Red Planet mission readings."""

import math


class TelemetryStats:
    """Descriptive statistics over a list of telemetry readings."""

    def __init__(self, readings: list[float]) -> None:
        if not readings:
            raise ValueError("readings must not be empty")
        self.readings = sorted(readings)

    def count(self) -> int:
        return len(self.readings)

    def mean(self) -> float:
        return sum(self.readings) / self.count()

    def median(self) -> float:
        n = self.count()
        mid = n // 2
        if n % 2 == 0:
            return (self.readings[mid - 1] + self.readings[mid]) / 2
        return self.readings[mid]

    def std_dev(self) -> float:
        if self.count() < 2:
            return 0.0
        mean = self.mean()
        variance = sum((x - mean) ** 2 for x in self.readings) / (self.count() - 1)
        return math.sqrt(variance)

    def minimum(self) -> float:
        return self.readings[0]

    def maximum(self) -> float:
        return self.readings[-1]

    def summary(self) -> dict:
        return {
            "count": self.count(),
            "mean": round(self.mean(), 4),
            "median": round(self.median(), 4),
            "std_dev": round(self.std_dev(), 4),
            "min": self.minimum(),
            "max": self.maximum(),
        }

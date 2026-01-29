from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Iterable, List


@dataclass(frozen=True)
class MetricSummary:
    """Summary of a numeric time series."""

    avg: float
    trend: float
    variability: float


def compute_trend(values: Iterable[float]) -> float:
    """
    Compute a simple trend for a series.

    Trend = last_value - first_value.
    Returns 0.0 if fewer than 2 values are provided.
    """
    vals = list(values)   # Convert input to list so we can access first/last values
    if len(vals) < 2:
        return 0.0
    return float(vals[-1] - vals[0])     # Trend = last - first (simple change over time)


def compute_variability(values: Iterable[float]) -> float:
    """
    Compute variability using population standard deviation.

    Returns 0.0 if fewer than 2 values are provided.
    """
    vals = list(values)
    if len(vals) < 2:
        return 0.0
    return float(pstdev(vals))


def summarize_series(values: Iterable[float]) -> MetricSummary:
    """
    Build a MetricSummary for a numeric series: avg, trend, variability.
    """
    vals: List[float] = list(values)
    if not vals:
        return MetricSummary(avg=0.0, trend=0.0, variability=0.0)

    return MetricSummary(
        avg=float(mean(vals)),
        trend=compute_trend(vals),
        variability=compute_variability(vals),
    )

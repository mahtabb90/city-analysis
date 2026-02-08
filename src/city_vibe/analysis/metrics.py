
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


def compute_trend(values: Iterable[float | None]) -> float:
    """
    Compute a simple trend for a series.

    """
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return 0.0
    return float(vals[-1] - vals[0])


def compute_variability(values: Iterable[float | None]) -> float:
    """
    Compute variability using population standard deviation.
    """
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return 0.0
    return float(pstdev(vals))


def summarize_series(values: Iterable[float | None]) -> MetricSummary:
    """
    Build a MetricSummary for a numeric series: avg, trend, variability.
    """
    vals = [v for v in values if v is not None]
    if not vals:
        return MetricSummary(avg=0.0, trend=0.0, variability=0.0)

    return MetricSummary(
        avg=float(mean(vals)),
        trend=compute_trend(vals),
        variability=compute_variability(vals),
    )

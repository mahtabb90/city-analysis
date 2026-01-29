"""
Rule-based classification for city status.

This module converts computed metrics into a simple, testable status.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from city_vibe.analysis.metrics import MetricSummary


class CityStatus(str, Enum):
    """High-level classification of the city conditions."""

    STABLE = "stable"
    IMPROVING = "improving"
    DECLINING = "declining"
    UNSTABLE = "unstable"


@dataclass(frozen=True)
class WeatherRuleThresholds:
    """
    Threshold values used to classify weather-related status.

    Notes:
    - variability is compared first (instability wins)
    - trend decides improving vs declining
    """

    variability_unstable: float = 2.0
    trend_improving: float = 1.0
    trend_declining: float = -1.0


def classify_weather_status(
    metrics: MetricSummary,
    thresholds: WeatherRuleThresholds | None = None,
) -> CityStatus:
    """
    Classify city weather status based on metrics.

    Rules (in order):
    1) If variability is high -> UNSTABLE
    2) If trend is strongly positive -> IMPROVING
    3) If trend is strongly negative -> DECLINING
    4) Otherwise -> STABLE
    """
    # Use defaults if caller doesn't provide thresholds
    t = thresholds or WeatherRuleThresholds()

    # Instability should dominate (high fluctuations)
    if metrics.variability > t.variability_unstable:
        return CityStatus.UNSTABLE

    # Trend indicates direction over time
    if metrics.trend >= t.trend_improving:
        return CityStatus.IMPROVING

    if metrics.trend <= t.trend_declining:
        return CityStatus.DECLINING

    return CityStatus.STABLE

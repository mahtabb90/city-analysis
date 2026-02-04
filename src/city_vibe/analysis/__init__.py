"""
Analysis package for City Vibe Analyzer.

This package contains the core analysis logic:
- metrics: numerical analysis of time-series data
- rules: rule-based classification built on top of metrics

The analysis layer is independent of data sources and presentation.
"""

from city_vibe.analysis.metrics import (
    MetricSummary,
    compute_trend,
    compute_variability,
    summarize_series,
)

from city_vibe.analysis.rules import (
    CityStatus,
    WeatherRuleThresholds,
    classify_weather_status,
)

__all__ = [
    "MetricSummary",
    "compute_trend",
    "compute_variability",
    "summarize_series",
    "CityStatus",
    "WeatherRuleThresholds",
    "classify_weather_status",
]

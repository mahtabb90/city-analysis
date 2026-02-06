from city_vibe.analysis.metrics import MetricSummary
from city_vibe.analysis.vibe_algorithm import (
    CityStatus,
    RuleThresholds,
    classify_status,
)


def test_unstable_when_variability_high():
    metrics = MetricSummary(avg=0.0, trend=0.5, variability=5.0)
    assert classify_status(metrics) == CityStatus.UNSTABLE


def test_improving_when_trend_high_and_variability_ok():
    metrics = MetricSummary(avg=0.0, trend=2.0, variability=0.3)
    assert classify_status(metrics) == CityStatus.IMPROVING


def test_declining_when_trend_low_and_variability_ok():
    metrics = MetricSummary(avg=0.0, trend=-2.0, variability=0.3)
    assert classify_status(metrics) == CityStatus.DECLINING


def test_custom_thresholds_change_behavior():
    metrics = MetricSummary(avg=0.0, trend=0.8, variability=1.5)
    thresholds = RuleThresholds(
        variability_unstable=1.0, trend_improving=0.5, trend_declining=-0.5
    )
    assert classify_status(metrics, thresholds) == CityStatus.UNSTABLE

from city_vibe.analysis.metrics import (
    compute_trend,
    compute_variability,
    summarize_series,
)


def test_compute_trend_basic():
    assert compute_trend([1.0, 2.0, 4.0]) == 3.0


def test_compute_variability_zero_for_single_value():
    assert compute_variability([10.0]) == 0.0


def test_summarize_series():
    summary = summarize_series([1.0, 2.0, 3.0])
    assert summary.avg == 2.0
    assert summary.trend == 2.0
    assert summary.variability >= 0.0

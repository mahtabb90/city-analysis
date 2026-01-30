from pathlib import Path

from city_vibe.analysis.metrics import MetricSummary
from city_vibe.analysis.rules import CityStatus
from city_vibe.presentation.plots import (
    plot_metric_summary_bar,
    plot_city_status_overview,
)


def test_plot_metric_summary_bar_creates_file(tmp_path: Path):
    metrics = MetricSummary(avg=5.0, trend=1.2, variability=0.8)
    out = tmp_path / "summary.png"

    result = plot_metric_summary_bar(metrics, out)

    assert result.exists()
    assert result.stat().st_size > 0


def test_plot_city_status_overview_creates_file(tmp_path: Path):
    out = tmp_path / "status.png"

    result = plot_city_status_overview(CityStatus.IMPROVING, out)

    assert result.exists()
    assert result.stat().st_size > 0

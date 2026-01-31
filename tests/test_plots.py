from pathlib import Path

from city_vibe.analysis.metrics import MetricSummary
from city_vibe.analysis.rules import CityStatus
from city_vibe.presentation.plots import (
    plot_city_status_overview,
    plot_line_series,
    plot_metric_summary_bar,
)


def test_plot_line_series_creates_file(tmp_path: Path):
    out_file = tmp_path / "line_series.png"

    result = plot_line_series(
        values=[1.0, 2.0, 1.5, 3.0],
        out_path=out_file,
        title="Temperature trend",
        x_label="Day",
        y_label="Temp (C)",
    )

    assert result.exists()
    assert result.stat().st_size > 0


def test_plot_metric_summary_bar_creates_file(tmp_path: Path):
    metrics = MetricSummary(avg=5.0, trend=1.2, variability=0.8)
    out_file = tmp_path / "summary.png"

    result = plot_metric_summary_bar(metrics, out_file)

    assert result.exists()
    assert result.stat().st_size > 0


def test_plot_city_status_overview_creates_file(tmp_path: Path):
    out_file = tmp_path / "status.png"

    result = plot_city_status_overview(CityStatus.IMPROVING, out_file)

    assert result.exists()
    assert result.stat().st_size > 0

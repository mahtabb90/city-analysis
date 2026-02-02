from pathlib import Path

import pytest

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


def test_plot_line_series_raises_on_empty_values(tmp_path: Path):
    out_file = tmp_path / "empty.png"

    with pytest.raises(ValueError, match="values must not be empty"):
        plot_line_series(values=[], out_path=out_file)


def test_plot_line_series_raises_on_label_length_mismatch(tmp_path: Path):
    out_file = tmp_path / "mismatch.png"

    with pytest.raises(ValueError, match="x_labels must have the same length as values"):
        plot_line_series(
            values=[1.0, 2.0],
            out_path=out_file,
            x_labels=["day-1"],  # only 1 label for 2 values
        )


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

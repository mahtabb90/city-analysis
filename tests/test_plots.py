from pathlib import Path

from city_vibe.presentation.plots import plot_line_series


def test_plot_line_series_creates_file(tmp_path: Path):
    out_file = tmp_path / "temp_plot.png"

    result = plot_line_series(
        values=[1.0, 2.0, 1.5, 3.0],
        out_path=out_file,
        title="Temperature trend",
        x_label="Day",
        y_label="Temp (C)",
    )

    assert result.exists()
    assert result.stat().st_size > 0  # File should not be empty

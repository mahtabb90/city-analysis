from pathlib import Path

import pytest

from city_vibe.presentation.cli import CliArgs, run_demo, validate_args


def test_demo_run_creates_three_plots(tmp_path: Path):
    args = CliArgs(city="Stockholm", days=7, out_dir=tmp_path, demo=True)
    outputs = run_demo(args)

    assert Path(outputs["line_plot"]).exists()
    assert Path(outputs["metrics_plot"]).exists()
    assert Path(outputs["status_plot"]).exists()

    # Files should not be empty
    assert Path(outputs["line_plot"]).stat().st_size > 0
    assert Path(outputs["metrics_plot"]).stat().st_size > 0
    assert Path(outputs["status_plot"]).stat().st_size > 0


def test_validate_args_rejects_invalid_days():
    class NS:
        city = "Stockholm"
        days = 0
        out_dir = "reports/plots"
        demo = True

    with pytest.raises(ValueError):
        validate_args(NS())

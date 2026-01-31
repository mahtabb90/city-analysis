"""
Command-line interface for City Vibe Analyzer.

Demo mode runs the full pipeline without calling external APIs:
- generate demo time-series data
- compute metrics
- classify city status
- save plots to disk
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from city_vibe.analysis.metrics import summarize_series
from city_vibe.analysis.rules import classify_weather_status
from city_vibe.presentation.plots import (
    plot_city_status_overview,
    plot_line_series,
    plot_metric_summary_bar,
)


@dataclass(frozen=True)
class CliArgs:
    """Validated CLI arguments."""

    city: str
    days: int
    out_dir: Path
    demo: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="city-vibe",
        description="City Vibe Analyzer (Demo mode available)",
    )

    parser.add_argument(
        "--city",
        default="Stockholm",
        help="City name (used for labels in demo mode).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days for the demo time-series (1-30).",
    )
    parser.add_argument(
        "--out-dir",
        default="reports/plots",
        help="Directory to save plot images.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo pipeline (no API calls).",
    )

    return parser


def validate_args(ns: argparse.Namespace) -> CliArgs:
    # Basic input validation (course requirement)
    city = str(ns.city).strip()
    if not city:
        raise ValueError("city must be a non-empty string")

    days = int(ns.days)
    if days < 1 or days > 30:
        raise ValueError("days must be between 1 and 30")

    out_dir = Path(ns.out_dir)
    demo = bool(ns.demo)

    return CliArgs(city=city, days=days, out_dir=out_dir, demo=demo)


def generate_demo_temperatures(days: int) -> list[float]:
    """
    Create simple demo data.

    English note: This is intentionally deterministic (no randomness)
    to make tests stable and predictable.
    """
    base = 3.0
    temps: list[float] = []
    for i in range(days):
        # Simple pattern: gentle upward trend + small oscillation
        wave = 0.8 if i % 2 == 0 else -0.4
        temps.append(base + (i * 0.5) + wave)
    return temps


def run_demo(args: CliArgs) -> dict[str, str]:
    """
    Run the demo pipeline end-to-end and save plots.

    Returns:
        A small dict of generated file paths (as strings) for printing/testing.
    """
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    temps = generate_demo_temperatures(args.days)

    # Analysis layer (metrics + rules)
    summary = summarize_series(temps)
    status = classify_weather_status(summary)

    # Presentation layer (plots)
    line_path = plot_line_series(
        values=temps,
        out_path=out_dir / f"{args.city.lower()}_temp_trend.png",
        title=f"Temperature trend - {args.city}",
        x_label="Day",
        y_label="Temp (C)",
    )

    metrics_path = plot_metric_summary_bar(
        metrics=summary,
        out_path=out_dir / f"{args.city.lower()}_metrics.png",
        title=f"Metric summary - {args.city}",
    )

    status_path = plot_city_status_overview(
        status=status,
        out_path=out_dir / f"{args.city.lower()}_status.png",
        title=f"City status - {args.city}",
    )

    return {
        "line_plot": str(line_path),
        "metrics_plot": str(metrics_path),
        "status_plot": str(status_path),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)

    try:
        args = validate_args(ns)
    except ValueError as exc:
        # Print a user-friendly message and return non-zero exit code
        parser.error(str(exc))
        return 2

    if args.demo:
        outputs = run_demo(args)
        print("\nDemo run completed ✅")
        print(f"City: {args.city} | Days: {args.days}")
        print("Generated files:")
        for k, v in outputs.items():
            print(f" - {k}: {v}")
        return 0

    print("No mode selected. Use --demo to run without APIs.")
    return 1

"""
Plotting utilities for City Vibe Analyzer.

This module focuses on saving plots to files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

from city_vibe.analysis.metrics import MetricSummary
from city_vibe.analysis.rules import CityStatus

# Use a non-interactive backend so plots can be created in CI (no GUI required).
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402


def _ensure_output_dir(out_path: Path) -> None:
    """Ensure that the parent directory for the output path exists."""
    out_path.parent.mkdir(parents=True, exist_ok=True)


def plot_line_series(
    values: Iterable[float],
    out_path: str | Path,
    *,
    title: str = "Series",
    x_labels: Sequence[str] | None = None,
    x_label: str = "Time",
    y_label: str = "Value",
) -> Path:
    """
    Save a line plot for a numeric series.

    Args:
        values: Numeric values to plot (ordered in time).
        out_path: Where to save the image file (e.g. reports/plots/temp.png).
        title: Plot title.
        x_labels: Optional labels for x-axis (same length as values).
        x_label: Label for x-axis.
        y_label: Label for y-axis.

    Returns:
        Path to the saved plot file.
    """
    vals = list(values)
    out = Path(out_path)

    _ensure_output_dir(out)

    if x_labels is not None and len(x_labels) != len(vals):
        raise ValueError(
            "x_labels must have the same length as values "
            f"(got {len(x_labels)} labels and {len(vals)} values)."
        )

    fig, ax = plt.subplots(figsize=(8, 4))

    if x_labels is not None:
        ax.plot(x_labels, vals, marker="o")
        ax.tick_params(axis="x", rotation=45)
    else:
        ax.plot(range(len(vals)), vals, marker="o")

    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

    return out


def plot_metric_summary_bar(
    metrics: MetricSummary,
    out_path: str | Path,
    *,
    title: str = "Metric Summary",
) -> Path:
    """
    Save a bar chart summarizing key metrics.
    """
    out = Path(out_path)
    _ensure_output_dir(out)

    labels = ["Average", "Trend", "Variability"]
    values = [metrics.avg, metrics.trend, metrics.variability]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel("Value")
    ax.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

    return out


def plot_city_status_overview(
    status: CityStatus,
    out_path: str | Path,
    *,
    title: str = "City Status",
) -> Path:
    """
    Save a simple visual overview of city status.
    """
    out = Path(out_path)
    _ensure_output_dir(out)

    color_map = {
        CityStatus.STABLE: "#4CAF50",
        CityStatus.IMPROVING: "#2196F3",
        CityStatus.DECLINING: "#F44336",
        CityStatus.UNSTABLE: "#FF9800",
    }

    fig, ax = plt.subplots(figsize=(4, 3))
    ax.text(
        0.5,
        0.5,
        status.value.upper(),
        ha="center",
        va="center",
        fontsize=20,
        weight="bold",
        color="white",
        bbox=dict(boxstyle="round,pad=0.6", facecolor=color_map[status]),
    )
    ax.set_title(title)
    ax.axis("off")

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

    return out

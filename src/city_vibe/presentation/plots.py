"""
Plotting utilities for City Vibe Analyzer.

This module focuses on saving plots to files .
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

# Use a non-interactive backend so plots can be created in CI (no GUI required).
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402


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
    vals = list(values)  # Convert to list so we can measure length and index
    out = Path(out_path)

    # Ensure output directory exists
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4))

    # If x_labels are provided, use them. Otherwise use index positions.
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
    plt.close(fig)  # Important: free memory in test/CI runs

    return out

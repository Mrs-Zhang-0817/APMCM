"""Render the manuscript's two paired forecast comparisons from archived results."""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
GASES = ("CO2", "CO")


def read_rows(path):
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def archived_comparisons():
    summary = read_rows("q3/results/summary.csv")
    gains = read_rows("question3/results/spectral_gain_10s.csv")
    static, historical, process, fused = [], [], [], []
    for gas in GASES:
        selected = {(row["model"]): row for row in summary
                    if row["target"] == gas and float(row["horizon_s"]) == 10}
        for dest, model in ((static, "spectrum"), (historical, "spectrum_history")):
            row = selected[model]
            assert int(row["heats"]) == 9
            dest.append(float(row["macro_mae"]))
        paired = [row for row in gains if row["gas"] == gas]
        assert len({row["heat"] for row in paired}) == 9 and len(paired) == 9
        process.append(np.mean([float(row["process_MAE"]) for row in paired]))
        fused.append(np.mean([float(row["with_spectra_MAE"]) for row in paired]))
    return (static, historical), (process, fused)


def comparison_panel(ax, title, window, values, labels, precision, limit):
    first, second = values
    x = np.arange(len(GASES))
    neutral, accent = "#536477", "#007a78"
    left, right = x - 0.18, x + 0.18
    for a, b, u, v in zip(left, right, first, second):
        ax.plot([a, b], [u, v], color="#a8b7c2", lw=1.3, zorder=2)
    ax.scatter(left, first, label=labels[0], facecolor="white", edgecolor=neutral, s=43, zorder=3)
    ax.scatter(right, second, label=labels[1], color=accent, marker="D", s=33, zorder=3)
    for positions, vals, color in ((left, first, neutral), (right, second, accent)):
        for pos, value in zip(positions, vals):
            ax.annotate(f"{value:.{precision}f}", (pos, value), xytext=(0, 6), textcoords="offset points",
                        ha="center", color=color, fontsize=9)
    ax.set(xlim=(-0.55, 1.55), ylim=(0, limit), xticks=x, xticklabels=("CO₂", "CO"),
           xlabel="Gas", ylabel="Heat-averaged MAE (m³/s)")
    ax.set_title(f"{title}\nScored at target times from {window} s", loc="left", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#e1e8ee")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.15), frameon=False, fontsize=9)


def main():
    spectra_only, beyond_process = archived_comparisons()
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.3), layout="constrained")
    comparison_panel(axes[0], "(a) Spectrum only", 10, spectra_only,
                     ("Current spectrum", "Spectral history"), 2, 16)
    comparison_panel(axes[1], "(b) Added value beyond process history", 30, beyond_process,
                     ("Process history", "Process history + spectra"), 3, 6.5)
    fig.suptitle("Paired comparisons of 10 s ahead forecasts", fontsize=12)
    destination = ROOT / "paper" / "figures" / "forecast_comparisons.png"
    destination.parent.mkdir(exist_ok=True)
    fig.savefig(destination, dpi=220, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()

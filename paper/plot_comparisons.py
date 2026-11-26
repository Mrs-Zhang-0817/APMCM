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


def comparison_values():
    summary = read_rows("q3/results/summary.csv")
    gains = read_rows("question3/results/spectral_gain_10s.csv")
    static, historical, process, fused = [], [], [], []
    for gas in GASES:
        selected = {(row["model"]): row for row in summary
                    if row["target"] == gas and float(row["horizon_s"]) == 10}
        for dest, model in ((static, "spectrum"), (historical, "spectrum_history")):
            row = selected[model]
            assert int(row["heats"]) == 10
            dest.append(float(row["macro_mae"]))
        paired = [row for row in gains if row["gas"] == gas]
        assert len({row["heat"] for row in paired}) == 10 and len(paired) == 10
        process.append(np.mean([float(row["process_MAE"]) for row in paired]))
        fused.append(np.mean([float(row["with_spectra_MAE"]) for row in paired]))
    return (static, historical), (process, fused)


def write_comparison_tables():
    metrics = {(r["heat"], r["target"], r["model"]): r for r in read_rows("q3/results/validation.csv")
               if float(r["horizon_s"]) == 10 and r["model"] in {"spectrum", "spectrum_history"}}
    cases = []
    for row in read_rows("question3/results/spectral_gain_10s.csv"):
        heat, gas = row["heat"], row["gas"]
        baseline, variant = (metrics[heat, gas, model] for model in ("spectrum", "spectrum_history"))
        assert baseline["n_eval"] == variant["n_eval"] and int(baseline["n_eval"]) - int(row["n"]) == 40
        for comparison, first_s, n, before, after in (
            ("spectral_history", 10, baseline["n_eval"], baseline["mae"], variant["mae"]),
            ("spectra_beyond_process", 30, row["n"], row["process_MAE"], row["with_spectra_MAE"]),
        ):
            before, after = float(before), float(after)
            cases.append(dict(comparison=comparison, gas=gas, heat=heat, target_from_s=first_s,
                              n=int(n), baseline_mae=before, augmented_mae=after, delta_mae=after - before))
    summary = []
    for comparison in ("spectral_history", "spectra_beyond_process"):
        for gas in GASES:
            group = [r for r in cases if (r["comparison"], r["gas"]) == (comparison, gas)]
            assert len({r["heat"] for r in group}) == len(group) == 10
            delta = np.array([r["delta_mae"] for r in group])
            samples = np.random.default_rng(2026).integers(len(group), size=(10000, len(group)))
            lower, upper = np.quantile(delta[samples].mean(axis=1), [.025, .975])
            summary.append(dict(comparison=comparison, gas=gas, target_from_s=group[0]["target_from_s"],
                                heats=len(group), n_total=sum(r["n"] for r in group),
                                baseline_mae=np.mean([r["baseline_mae"] for r in group]),
                                augmented_mae=np.mean([r["augmented_mae"] for r in group]),
                                delta_mae=delta.mean(), improved_heats=int((delta < 0).sum()),
                                bootstrap_lower_95=lower, bootstrap_upper_95=upper))
    for filename, rows in (("paired_by_heat_10s.csv", cases), ("paired_summary_10s.csv", summary)):
        with (ROOT / "question3" / "results" / filename).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)


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
    write_comparison_tables()
    spectra_only, beyond_process = comparison_values()
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

"""Audit existing 10-second history predictions without refitting the models."""
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

RESULTS = Path(__file__).resolve().parent / "results"
MAIN_PREDICTIONS = RESULTS.parents[1] / "q3/results/predictions.csv"


def read_rows(filename):
    with (RESULTS / filename).open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def matched_main(groups):
    comparisons = defaultdict(list)
    keys = ("spectrum_history", "process", "adaptive_ensemble")
    with MAIN_PREDICTIONS.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if float(row["horizon_s"]) != 10 or float(row["target_s"]) < 30 or row["eligible"] != "True":
                continue
            for gas in ("CO", "CO2"):
                comparisons[gas, row["heat"]].append(
                    (float(row["target_s"]), float(row[f"recorded_{gas}"]),
                     *(float(row[f"{model}_{gas}"]) for model in keys)))
    assert groups.keys() == comparisons.keys()
    for (gas, heat), samples in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
        local = np.array(samples)
        peer = np.array(comparisons[gas, heat])
        np.testing.assert_array_equal(local[:, :2], peer[:, :2])
        errors = np.mean(np.abs(peer[:, 2:] - local[:, 1, None]), axis=0)
        yield dict(heat=heat, gas=gas, n=len(local), local_history_MAE=np.mean(abs(local[:, 2] - local[:, 1])),
                   **{f"peer_{name}_MAE": value for name, value in zip(("spectrum_history", "process", "adaptive"), errors)})


def plot_diagnostics(groups, summary):
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.hashsalt"] = "apmcm-question3"
    from matplotlib import pyplot as plt

    fig, axes = plt.subplots(3, 2, figsize=(10, 8), layout="constrained", sharex=True)
    for col, gas in enumerate(("CO", "CO2")):
        worst = [row for row in summary if row["gas"] == gas][:3]
        for row, ax in zip(worst, axes[:, col]):
            time, observed, predicted = np.array(groups[gas, row["heat"]]).T
            ax.plot(time, observed, label="Analyzer reading", lw=0.9)
            ax.plot(time, predicted, label="Spectral-history forecast", lw=0.9)
            ax.set_title(f'{row["heat"]} · {gas} · MAE {row["MAE"]:.2f}')
            ax.set_ylabel("Flow (m³/s)")
            ax.grid(alpha=.25)
        axes[-1, col].set_xlabel("Target time (s)")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Largest spectral-history errors at 10 s ahead")
    path = RESULTS / "history_10s_diagnostics.svg"
    fig.savefig(path, metadata={"Date": None})
    svg = path.read_text(encoding="utf-8")
    path.write_text("\n".join(line.rstrip() for line in svg.splitlines()) + "\n", encoding="utf-8")
    plt.close(fig)


def main():
    groups = defaultdict(list)
    for row in read_rows("predictions.csv"):
        if row["model"] != "history" or float(row["horizon_s"]) != 10:
            continue
        if row["label_valid"] == "False":
            assert row["observed"] == ""
            continue
        assert row["label_valid"] == "True"
        time = float(row["target_time_s"])
        assert time - float(row["input_time_s"]) == 10
        groups[row["target"], row["heat"]].append(
            (time, float(row["observed"]), float(row["predicted"]))
        )
    reference = {(row["target"], row["heat"]): row for row in read_rows("metrics.csv")
                 if row["model"] == "history" and float(row["horizon_s"]) == 10
                 and row["label_valid"] == "True"}
    assert groups.keys() == reference.keys()
    summary = []
    for key, values in groups.items():
        time, observed, predicted = np.array(values).T
        assert time[0] >= 30 and np.all(np.diff(time) > 0)
        error = predicted - observed
        high = observed >= np.quantile(observed, 0.9)
        mae = np.mean(np.abs(error))
        rmse = np.sqrt(np.mean(error ** 2))
        assert int(reference[key]["n"]) == len(time)
        np.testing.assert_allclose([mae, rmse], [float(reference[key][k]) for k in ("MAE", "RMSE")])
        summary.append(dict(gas=key[0], heat=key[1], n=len(time), MAE=mae, RMSE=rmse,
                            bias=error.mean(), high_threshold=np.quantile(observed, 0.9),
                            high_n=high.sum(), high_bias=error[high].mean(),
                            other_bias=error[~high].mean(), high_MAE=np.abs(error[high]).mean()))
    summary.sort(key=lambda row: (row["gas"], -row["MAE"]))
    ranks = defaultdict(int)
    for row in summary:
        ranks[row["gas"]] += 1
        row["rank_worst_first"] = ranks[row["gas"]]
    with (RESULTS / "history_10s_by_heat.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)
    matched = list(matched_main(groups))
    with (RESULTS / "matched_peer_10s.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=matched[0].keys())
        writer.writeheader()
        writer.writerows(matched)
    plot_diagnostics(groups, summary)
    for row in summary:
        print(row["gas"], row["heat"], *(round(row[k], 2) for k in ("MAE", "bias", "high_bias", "other_bias")))


if __name__ == "__main__":
    main()

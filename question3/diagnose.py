"""Audit existing 10-second history predictions without refitting the models."""
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

RESULTS = Path(__file__).resolve().parent / "results"


def read_rows(filename):
    with (RESULTS / filename).open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def main():
    groups = defaultdict(list)
    for row in read_rows("predictions.csv"):
        if row["model"] != "history" or float(row["horizon_s"]) != 10:
            continue
        if row["heat"] == "6B03205":
            assert row["observed"] == "" and row["label_valid"] == "False"
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
    assert groups.keys() == reference.keys() and len(groups) == 18
    summary = []
    for key, values in groups.items():
        time, observed, predicted = np.array(values).T
        assert time[0] == 30 and np.all(np.diff(time) == 0.5)
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
    for offset, row in enumerate(summary):
        row["rank_worst_first"] = offset % 9 + 1
    with (RESULTS / "history_10s_by_heat.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)
    for row in summary:
        print(row["gas"], row["heat"], *(round(row[k], 2) for k in ("MAE", "bias", "high_bias", "other_bias")))


if __name__ == "__main__":
    main()

"""Run and verify the revised ten-heat Question 3 pipeline."""

import argparse
import csv
import io
from pathlib import Path
import subprocess
import sys

import numpy as np

from q3.data import CURRENT_LAGS, ROOT, heat_exports
from q3.predict import TARGETS, load_heats, write_csv
from question3.run import read_heats


def verify_inputs(directory):
    main = load_heats(directory)
    supplement = read_heats(directory)
    if len(main) != 10 or {heat.name for heat in main} != set(supplement):
        raise ValueError("The main and supplementary experiments require the same ten distinct heats")
    for heat in main:
        values, _, eligible = supplement[heat.name]
        np.testing.assert_array_equal(heat.gas, values[:, -2:])
        np.testing.assert_array_equal(heat.eligible, eligible)
        if not heat.eligible.all():
            raise ValueError(f"Expected the revised, fully eligible dataset: {heat.name}")
    revised = next(heat for heat in main if heat.name == "6B03205")
    assert len(revised.time) == 1479
    np.testing.assert_array_equal(revised.gas[[499, 500, 1299]],
                                  [[18.71, 31.96], [18.71, 31.96], [12.64, 42.14]])
    print("Both readers agree on ten scored heats. 6B03205: 1479 labels; row 500:", revised.gas[499], flush=True)


def frozen_score(directory):
    """Score forecasts committed before the organizer released revised labels."""
    revision = "a1006a1"
    archived = subprocess.check_output(["git", "show", f"{revision}:q3/results/predictions.csv"], cwd=ROOT)
    archived_rows = [row for row in csv.DictReader(io.StringIO(archived.decode("utf-8-sig")))
                     if row["heat"] == "6B03205" and float(row["horizon_s"]) == 10]
    assert all(row["eligible"] == "False" for row in archived_rows)
    revised, _, valid = read_heats(directory)["6B03205"]
    indices = np.array([int(float(row["target_s"]) * 2) for row in archived_rows])
    assert len(indices) == 1459 and valid[indices].all()
    rows = []
    for col, gas in enumerate(TARGETS):
        prediction = np.array([float(row[f"joint_ensemble_{gas}"]) for row in archived_rows])
        error = prediction - revised[indices, -2:][:, col]
        rows.append(dict(heat="6B03205", gas=gas, archived_commit=revision, horizon_s=10,
                         start_target_s=indices[0] / 2, n=len(indices), mae=np.mean(abs(error)),
                         rmse=np.sqrt(np.mean(error ** 2))))
    write_csv(ROOT / "question3/results/frozen_attachment1_10s.csv", rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path, help="Directory with ten revised NPZ inputs")
    args = parser.parse_args()
    with heat_exports(args.exports) as directory:
        directory = directory.resolve()
        verify_inputs(directory)
        for command in (
            ["-m", "q3.predict", "--exports", str(directory), "--lags", str(CURRENT_LAGS)],
            ["-m", "question3.run", "--input", str(directory), "--output", "question3/results"],
            ["-m", "question3.window_selection", "--input", str(directory)],
            ["-m", "question3.spectral_gain", "--input", str(directory), "--lags", str(CURRENT_LAGS)],
            ["-m", "question3.diagnose"],
            ["-m", "q3.plot_results"],
            ["paper/plot_comparisons.py"],
        ):
            subprocess.run([sys.executable, *command], cwd=ROOT, check=True)
        frozen_score(directory)


if __name__ == "__main__":
    main()

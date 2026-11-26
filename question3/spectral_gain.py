"""Matched 10-second ablations using the same revised inputs as the main run."""
import argparse
import csv
from pathlib import Path
import sys

import numpy as np

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from q3 import predict
from q3.data import CURRENT_LAGS, ROOT, heat_exports


def interpolate_clipped(wave, spectrum, flags):
    clipped = (flags & 2) != 0
    cleaned = spectrum.copy()
    for i in np.flatnonzero(clipped.any(axis=1)):
        good = flags[i] == 0
        if good.sum() >= 2:
            interior = clipped[i] & (wave > wave[good][0]) & (wave < wave[good][-1])
            cleaned[i, interior] = np.interp(wave[interior], wave[good], spectrum[i, good])
    return cleaned


def process_reference(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {
            (row["heat"], float(row["target_s"])): [float(row[f"process_history_{gas}"]) for gas in predict.TARGETS]
            for row in csv.DictReader(stream) if row["eligible"] == "True" and float(row["horizon_s"]) == 10
        }


def evaluate(directory, reference, candidates):
    heats = []
    for path in sorted(directory.glob("*.npz")):
        heat = predict.load_heat(path)
        if heat.eligible[60:].any():
            clean = predict.load_heat(path, interpolate_clipped)
            heat.features["clean_fusion"] = clean.features["fusion_history"]
            heats.append(heat)
    heats.sort(key=lambda heat: heat.name)
    gains, clipping, delays = [], [], []
    for test in heats:
        training = [h for h in heats if h.name != test.name]
        available = [predict.target_indices(h) for h in training]
        fit_rows = [idx[h.eligible[idx]] for h, idx in zip(training, available)]
        target = [h.gas[idx] for h, idx in zip(training, fit_rows)]
        rows = np.flatnonzero(test.eligible[60:]) + 60
        truth = test.gas[rows]
        fitted = {}
        for model in ("process_history", "fusion_history", "clean_fusion"):
            x = [predict.design(h, idx, 20, model) for h, idx in zip(training, fit_rows)]
            values = predict.fit_ridge(x, target, predict.design(test, rows, 20, model), 100)
            fitted[model] = np.maximum(0, values)

        expected = [reference[test.name, t] for t in test.time[rows]]
        np.testing.assert_allclose(fitted["process_history"], expected, atol=0.00000051, rtol=0)
        members, lags = predict.predict_members(training, test, 20, candidates)
        selected = np.searchsorted(predict.target_indices(test), rows)
        base = members[selected, predict.MODELS.index("fusion_history")]
        adjusted = members[selected, predict.MODELS.index("lag_fusion")]
        np.testing.assert_allclose(base, fitted["fusion_history"], atol=1e-10, rtol=0)
        error = {model: np.mean(np.abs(result - truth), axis=0) for model, result in fitted.items()}
        lag_error = np.mean(np.abs(adjusted - truth), axis=0)
        for j, gas in enumerate(predict.TARGETS):
            common = dict(heat=test.name, gas=gas, n=len(rows))
            proc, fusing, clean = (error[model][j] for model in ("process_history", "fusion_history", "clean_fusion"))
            gains.append(dict(**common, process_MAE=proc, with_spectra_MAE=fusing, delta_MAE=fusing - proc))
            clipping.append(dict(**common, raw_MAE=fusing, clean_MAE=clean, delta_MAE=clean - fusing))
            lag, count = lags[j]
            support = [h.name for h in training if (h.name, gas) in candidates]
            assert count == len(support) and test.name not in support
            if lag <= 10:
                np.testing.assert_array_equal(base[:, j], adjusted[:, j])
            delays.append(dict(**common, eligible_heats=count, contributing_heats="|".join(support),
                               rule_lag_s=lag, active=lag > 10, extra_lookback_s=max(0, lag-10),
                               baseline_MAE=fusing, lag_MAE=lag_error[j], delta_MAE=lag_error[j] - fusing))
    return gains, clipping, delays


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Directory of heat NPZ files")
    parser.add_argument("--predictions", type=Path, default=ROOT / "q3/results/predictions.csv")
    parser.add_argument("--lags", type=Path, default=CURRENT_LAGS)
    parser.add_argument("--output", type=Path, default=ROOT / "question3/results")
    parser.add_argument("--clip-test", action="store_true", help="Write only the clipping comparison")
    parser.add_argument("--lag-test", action="store_true", help="Write only the lag comparison")
    args = parser.parse_args()
    if args.lag_test and args.clip_test:
        parser.error("Select at most one comparison")
    reference = process_reference(args.predictions)
    candidates = predict.read_lag_candidates(args.lags)
    with heat_exports(args.input) as directory:
        gains, clipping, delays = evaluate(directory, reference, candidates)
    args.output.mkdir(parents=True, exist_ok=True)
    if not (args.lag_test or args.clip_test):
        predict.write_csv(args.output / "spectral_gain_10s.csv", gains)
    if not args.lag_test:
        predict.write_csv(args.output / "clip_test_10s.csv", clipping)
    if not args.clip_test:
        predict.write_csv(args.output / "lag_test_10s.csv", delays)


if __name__ == "__main__":
    main()

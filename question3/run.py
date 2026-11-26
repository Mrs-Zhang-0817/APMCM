"""Causal leave-one-heat-out baselines for B problem question 3."""
import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from q3.data import heat_exports, label_mask

DT = 0.5


def read_heats(directory):
    heats = {}
    npz_files = sorted(directory.glob("*.npz"))
    npy_files = sorted(directory.glob("6*.npy"))
    if npz_files and npy_files:
        raise ValueError("Use separate directories for NPZ and NPY inputs")
    for file in npz_files:
        with np.load(file, allow_pickle=False) as saved:
            heat = saved["heat_id"].item()
            time = saved["time_s"]
            wave = saved["wavelength_nm"]
            gas = np.column_stack((saved["co2"], saved["co"]))
            values = np.column_stack((time / DT + 1, saved["spectrum"], saved["oxygen_cumulative"], gas))
            eligible = saved["gas_label_eligible"]
        if not np.array_equal(time, np.arange(len(time)) * DT) or not np.all(np.diff(wave) > 0):
            raise ValueError(f"Unexpected time or wavelength grid: {file}")
        if heat in heats or not np.array_equal(eligible, label_mask(gas)):
            raise ValueError(f"Duplicate heat or inconsistent label flags: {file}")
        heats[heat] = values, wave, eligible
    for file in npy_files:
        metadata = file.with_suffix(".json")
        if not metadata.exists():
            raise ValueError(f"Missing wavelength metadata: {metadata}")
        data = np.load(file)
        header = json.loads(metadata.read_text(encoding="utf-8"))["header"]
        wave = np.asarray(header[1:-3], dtype=float)
        if data.ndim != 2 or data.shape[1] != len(wave) + 4:
            raise ValueError(f"Unexpected dimensions: {file}")
        if not np.isfinite(data).all() or np.any(np.diff(wave) <= 0):
            raise ValueError(f"Nonfinite data or unordered wavelengths: {file}")
        if not np.all(np.diff(data[:, 0]) == 1):
            raise ValueError(f"Nonconsecutive sequence: {file}")
        heats[file.stem] = data, wave, label_mask(data[:, -2:])
    if len(heats) != 10 or "6B03205" not in heats:
        raise ValueError("Expected all ten heats, including 6B03205")
    return dict(sorted(heats.items()))


def features(data, wave):
    # Interpolate to a fixed physical wavelength grid before averaging bands.
    grid = np.linspace(341.0, 1023.0, 1024)
    spectrum = data[:, 1:-3]
    right = np.searchsorted(wave, grid).clip(1, len(wave) - 1)
    left = right - 1
    weight = (grid - wave[left]) / (wave[right] - wave[left])
    aligned = spectrum[:, left] * (1 - weight) + spectrum[:, right] * weight
    bands = aligned.reshape(len(data), 16, 64).mean(axis=2)
    cumulative = np.vstack((np.zeros((1, 16)), np.cumsum(bands, axis=0)))
    history = []
    for steps in (10, 20, 40):
        start = np.maximum(np.arange(len(data)) + 1 - steps, 0)
        mean = (cumulative[np.arange(len(data)) + 1] - cumulative[start]) / (np.arange(len(data)) + 1 - start)[:, None]
        history.extend((mean, bands - mean))
    oxygen = data[:, -3]
    idx = np.arange(len(data))
    start = np.maximum(idx - 11, 0)
    flow = (oxygen - oxygen[start]) / np.maximum((idx - start) * DT, DT)
    process = np.column_stack((idx * DT, oxygen, flow))
    return bands, np.column_stack((bands, *history)), process


def fit_predict(train_x, train_y, test_x, alpha):
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale < 1e-12] = 1.0
    x = (train_x - mean) / scale
    test = (test_x - mean) / scale
    target_mean = train_y.mean(axis=0)
    coef = np.linalg.solve(x.T @ x + alpha * np.eye(x.shape[1]), x.T @ (train_y - target_mean))
    return target_mean + test @ coef


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Directory of heat NPZ files or legacy NPY cache")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--alpha", type=float, default=10.0)
    args = parser.parse_args()
    if args.alpha <= 0:
        parser.error("alpha must be positive")
    with heat_exports(args.input) as directory:
        heats = read_heats(directory)
    prepared = {}
    for heat, (data, wave, eligible) in heats.items():
        if wave[0] > 341 or wave[-1] < 1023:
            raise ValueError(f"Insufficient wavelength coverage: {heat}")
        prepared[heat] = (*features(data, wave), data[:, -2:], eligible)
    metrics, predictions = [], []
    for heat in prepared:
        for horizon in (0, 20):  # samples; 20 corresponds to 10 seconds
            for mode in ("mean", "spectrum", "history", "process", "fusion"):
                def select(item):
                    bands, history, process, y, valid = item
                    x = {"mean": np.ones((len(y), 1)), "spectrum": bands,
                         "history": history, "process": process,
                         "fusion": np.column_stack((history, process))}[mode]
                    # Same target times across horizons and models, with a full 20 s history.
                    times = np.arange(60, len(y))
                    return x[times - horizon], y[times], times, valid[times]
                training = [select(item) for name, item in prepared.items() if name != heat]
                x = np.vstack([inputs[valid] for inputs, _, _, valid in training])
                y = np.vstack([targets[valid] for _, targets, _, valid in training])
                xt, yt, times, valid = select(prepared[heat])
                pred = fit_predict(x, y, xt, args.alpha)
                for col, name in enumerate(("CO2", "CO")):
                    err = pred[valid, col] - yt[valid, col]
                    variance = np.var(yt[valid, col]) if valid.any() else 0
                    metrics.append(dict(heat=heat, horizon_s=horizon * DT, model=mode,
                        target=name, n=len(err), label_valid=bool(valid.any()),
                        MAE=np.mean(np.abs(err)) if valid.any() else "",
                        RMSE=np.sqrt(np.mean(err ** 2)) if valid.any() else "",
                        R2=1 - np.mean(err ** 2) / variance if variance > 0 else ""))
                    for i, t in enumerate(times):
                        predictions.append(dict(heat=heat, horizon_s=horizon * DT, model=mode,
                            target=name, target_time_s=t * DT, input_time_s=(t - horizon) * DT,
                            observed=yt[i, col] if valid[i] else "", predicted=pred[i, col], label_valid=bool(valid[i])))
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "metrics.csv", metrics)
    write_csv(args.output / "predictions.csv", predictions)
    print(f"Saved {len(metrics)} metric rows and {len(predictions)} predictions to {args.output}")


if __name__ == "__main__":
    main()

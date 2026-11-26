"""Evaluate causal flue-gas predictors by nested leave-one-heat-out validation."""

import argparse
import csv
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np

from q3.data import CURRENT_LAGS, heat_exports


ROOT = Path(__file__).resolve().parents[1]
STEP_S = 0.5
HORIZONS = (0, 20)
TARGETS = ("CO2", "CO")
MODELS = (
    "mean", "process", "spectrum", "fusion", "process_history",
    "spectrum_history", "fusion_history", "lag_fusion",
)
JOINT = ("fusion", "fusion_history", "lag_fusion")
ENSEMBLES = ("joint_ensemble", "adaptive_ensemble")


@dataclass
class Heat:
    name: str
    time: np.ndarray
    gas: np.ndarray
    eligible: np.ndarray
    features: dict


def trailing_mean(values, steps):
    padded = np.repeat(values[:1], steps - 1, axis=0)
    cumulative = np.cumsum(np.vstack((np.zeros_like(values[:1]), padded, values)), axis=0)
    return (cumulative[steps:] - cumulative[:-steps]) / steps


def backshift(values, steps):
    return values[np.maximum(0, np.arange(len(values)) - steps)]


def common_bands(wave, spectrum, flags):
    edges = np.linspace(341, 1023, 17)
    # Insert band edges into the native wavelength grid to integrate linear segments.
    grid = np.unique(np.r_[edges, wave[(wave > edges[0]) & (wave < edges[-1])]])
    indices = np.searchsorted(edges, grid)
    ends = np.flatnonzero(grid == edges[np.minimum(indices, len(edges) - 1)])
    reconstructed = np.empty((len(spectrum), len(grid)))
    for i, row in enumerate(spectrum):
        good = (flags[i] & 5) == 0
        if good.sum() < 2 or wave[good][0] > edges[0] or wave[good][-1] < edges[-1]:
            raise ValueError("Insufficient valid wavelengths to reconstruct the common interval")
        reconstructed[i] = np.interp(grid, wave[good], row[good])
    areas = (reconstructed[:, 1:] + reconstructed[:, :-1]) * (np.diff(grid) / 2)
    cumulative = np.column_stack((np.zeros(len(spectrum)), np.cumsum(areas, axis=1)))
    return np.diff(cumulative[:, ends], axis=1) / np.diff(edges)


def load_heat(path, spectrum_transform=None):
    with np.load(path, allow_pickle=False) as data:
        heat = str(data["heat_id"].item())
        time = data["time_s"]
        oxygen = data["oxygen_cumulative"]
        gas = np.column_stack((data["co2"], data["co"]))
        eligible = data["gas_label_eligible"]
        flags = data["quality_flags"]
        wave, spectrum = data["wavelength_nm"], data["spectrum"]
        if spectrum_transform is not None:
            spectrum = spectrum_transform(wave, spectrum, flags)
        bands = common_bands(wave, spectrum, flags)
    if len(time) <= max(HORIZONS) or not np.array_equal(time, np.arange(len(time)) * STEP_S):
        raise ValueError(f"Unexpected time grid for {heat}")
    if not np.isfinite(oxygen).all() or np.any(np.diff(oxygen) < 0):
        raise ValueError(f"Unexpected cumulative oxygen values for {heat}")

    # Linearly interpolate cumulative oxygen between observed points and use
    # trailing interval slopes. The slope at each grid point uses known endpoints.
    flow = (oxygen - backshift(oxygen, 11)) / (11 * STEP_S)
    long_flow = (oxygen - backshift(oxygen, 41)) / (41 * STEP_S)
    process = np.column_stack((time, oxygen, flow))
    process_history = np.column_stack((
        process, long_flow, flow - backshift(flow, 20),
        np.maximum(0, time[:, None] - np.arange(120, 601, 120)),
        np.maximum(0, oxygen[:, None] - np.arange(500, 3001, 500)),
    ))
    logged = np.log1p(bands)
    spectral_history = np.column_stack((
        logged, trailing_mean(logged, 11), logged - backshift(logged, 20),
        np.mean((flags & 2) != 0, axis=1),
    ))
    features = {
        "process": process,
        "spectrum": bands,
        "fusion": np.column_stack((process, bands)),
        "process_history": process_history,
        "spectrum_history": spectral_history,
        "fusion_history": np.column_stack((process_history, spectral_history)),
        "logged_bands": logged,
    }
    return Heat(heat, time, gas, eligible, features)


def read_lag_candidates(path):
    by_heat = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if float(row["window"]) != 5.5:
                continue
            key = (row["heat"], row["target"])
            by_heat.setdefault(key, {})[row["method"]] = (float(row["lag"]), float(row["r"]))
    accepted = {}
    for key, peaks in by_heat.items():
        if set(peaks) != {"box", "triangle"}:
            continue
        (box_lag, box_r), (tri_lag, tri_r) = peaks["box"], peaks["triangle"]
        if (0 < min(box_lag, tri_lag) <= max(box_lag, tri_lag) < 40
                and abs(box_lag - tri_lag) <= 5 and min(abs(box_r), abs(tri_r)) >= 0.1
                and box_r * tri_r > 0):
            accepted[key] = (box_lag + tri_lag) / 2
    return accepted


def target_indices(heat):
    # Every horizon predicts the same measured targets, beginning at 10 s.
    return np.arange(max(HORIZONS), len(heat.time))


def design(heat, rows, horizon, model, lag_steps=0):
    origin = rows - horizon
    if model == "lag_fusion":
        base = heat.features["fusion_history"][origin]
        offset = max(lag_steps - horizon, 0)
        if offset:
            spectral = heat.features["logged_bands"]
            older = spectral[np.maximum(0, origin - offset)]
            departure = older - spectral[origin]
            return np.column_stack((base, departure))
        return base
    return heat.features[model][origin]


def fit_ridge(train_x, train_y, test_x, penalty):
    x = np.concatenate(train_x)
    y = np.concatenate(train_y)
    # Each training heat has the same total weight.
    weights = np.concatenate([np.full(len(part), 1 / len(part)) for part in train_y])
    weights *= len(weights) / weights.sum()
    mean_x = np.average(x, axis=0, weights=weights)
    mean_y = np.average(y, axis=0, weights=weights)
    centered = x - mean_x
    scale = np.sqrt(np.average(centered ** 2, axis=0, weights=weights))
    scale[scale < 1e-8] = 1
    z = centered / scale
    weighted = z.T * weights
    beta = np.linalg.solve(weighted @ z + penalty * np.eye(z.shape[1]), weighted @ (y - mean_y))
    return (test_x - mean_x) / scale @ beta + mean_y


def predict_members(training, test, horizon, lag_candidates):
    rows = target_indices(test)
    train_rows = []
    for heat in training:
        indices = target_indices(heat)
        train_rows.append(indices[heat.eligible[indices]])
    train_gas = [heat.gas[ix] for heat, ix in zip(training, train_rows)]
    predictions = {"mean": np.broadcast_to(np.mean([y.mean(0) for y in train_gas], axis=0), (len(rows), 2))}
    for model in MODELS[1:-1]:
        x = [design(heat, ix, horizon, model) for heat, ix in zip(training, train_rows)]
        penalty = 100 if model.endswith("_history") else 10
        predictions[model] = fit_ridge(x, train_gas, design(test, rows, horizon, model), penalty)

    lags = []
    lagged = []
    for j, target in enumerate(TARGETS):
        accepted = [lag_candidates[heat.name, target] for heat in training
                    if (heat.name, target) in lag_candidates]
        lag_steps = int(round(np.median(accepted) / STEP_S)) if len(accepted) >= 2 else 0
        lags.append((lag_steps * STEP_S, len(accepted)))
        if lag_steps <= horizon:
            lagged.append(predictions["fusion_history"][:, j])
        else:
            x = [design(heat, ix, horizon, "lag_fusion", lag_steps)
                 for heat, ix in zip(training, train_rows)]
            lagged.append(fit_ridge(x, [y[:, j] for y in train_gas],
                                   design(test, rows, horizon, "lag_fusion", lag_steps), 100))
    predictions["lag_fusion"] = np.column_stack(lagged)
    return np.maximum(0, np.stack([predictions[name] for name in MODELS], axis=1)), lags


def pair_weights(model_names):
    indices = [MODELS.index(name) for name in model_names]
    basis = np.eye(len(MODELS))
    candidates = [basis[i] for i in indices]
    for i, j in combinations(indices, 2):
        candidates.extend(weight * basis[i] + (1 - weight) * basis[j] for weight in (.25, .5, .75))
    return np.array(candidates)


def choose_weights(inner, model_names):
    weights = pair_weights(model_names)
    scores = []
    for heat, predictions in inner:
        rows = target_indices(heat)
        valid = heat.eligible[rows]
        errors = np.einsum("tmk,cm->tck", predictions[valid], weights) - heat.gas[rows[valid], None, :]
        scores.append(np.mean(np.abs(errors), axis=0))
    return weights[np.argmin(np.mean(scores, axis=0), axis=0)]


def metrics(measured, predicted):
    error = predicted - measured
    rmse = np.sqrt(np.mean(error ** 2))
    variance = np.var(measured)
    return np.mean(np.abs(error)), rmse, 1 - rmse ** 2 / variance if variance > 0 else None


def evaluate(heats, lag_candidates):
    usable = [heat for heat in heats if heat.eligible[target_indices(heat)].any()]
    scores, weights, series = [], [], []
    held_out_predictions = {}
    for horizon in HORIZONS:
        def predictions(training, test):
            key = (tuple(heat.name for heat in training), test.name, horizon)
            if key not in held_out_predictions:
                held_out_predictions[key] = predict_members(training, test, horizon, lag_candidates)
            return held_out_predictions[key]

        for test in heats:
            training = [heat for heat in usable if heat.name != test.name]
            inner = [
                (heat, predictions([other for other in training if other.name != heat.name], heat)[0])
                for heat in training
            ]
            test_members, lags = predictions(training, test)
            models = dict(zip(MODELS, test_members.transpose(1, 0, 2)))
            for ensemble, pool in zip(ENSEMBLES, (JOINT, MODELS)):
                blend = choose_weights(inner, pool)
                models[ensemble] = np.einsum("tmk,km->tk", test_members, blend)
                for j, target in enumerate(TARGETS):
                    weights.append(dict(heat=test.name, horizon_s=horizon * STEP_S, target=target,
                                        model=ensemble, candidate_lag_s=lags[j][0], lag_heats=lags[j][1],
                                        **dict(zip(MODELS, blend[j]))))

            rows = target_indices(test)
            valid = test.eligible[rows]
            for model, pred in models.items():
                for j, target in enumerate(TARGETS):
                    mae, rmse, r2 = metrics(test.gas[rows[valid], j], pred[valid, j]) if valid.any() else (None,) * 3
                    scores.append(dict(heat=test.name, horizon_s=horizon * STEP_S, target=target, model=model,
                                       n_eval=int(valid.sum()), n_pred=len(rows), mae=mae, rmse=rmse, r2=r2))
            for i, row in enumerate(rows):
                series.append(dict(heat=test.name, horizon_s=horizon * STEP_S, target_s=test.time[row],
                                   origin_s=test.time[row - horizon], eligible=bool(valid[i]),
                                   recorded_CO2=test.gas[row, 0], recorded_CO=test.gas[row, 1],
                                   **{f"{model}_{target}": round(float(models[model][i, j]), 6)
                                      for model in ("process", "process_history", "spectrum_history", *ENSEMBLES)
                                      for j, target in enumerate(TARGETS)}))
    return scores, weights, series


def summarize(scores):
    summary = []
    contrasts = []
    rng = np.random.default_rng(2026)
    for horizon in HORIZONS:
        for target in TARGETS:
            by_model = {
                model: [row for row in scores if row["horizon_s"] == horizon * STEP_S
                        and row["target"] == target and row["model"] == model and row["n_eval"]]
                for model in (*MODELS, *ENSEMBLES)
            }
            for model, group in by_model.items():
                r2 = [row["r2"] for row in group if row["r2"] is not None]
                summary.append(dict(horizon_s=horizon * STEP_S, target=target, model=model, heats=len(group),
                                    macro_mae=np.mean([row["mae"] for row in group]),
                                    macro_rmse=np.mean([row["rmse"] for row in group]),
                                    macro_r2=np.mean(r2) if r2 else None))
            draws = rng.integers(len(by_model["mean"]), size=(10000, len(by_model["mean"])))
            for a, b in (("joint_ensemble", "process_history"), ("spectrum_history", "spectrum"),
                         ("lag_fusion", "fusion_history"), ("adaptive_ensemble", "mean")):
                left, right = by_model[a], by_model[b]
                assert [row["heat"] for row in left] == [row["heat"] for row in right]
                delta = np.array([p["mae"] - q["mae"] for p, q in zip(left, right)])
                low, high = np.quantile(delta[draws].mean(axis=1), [.025, .975])
                contrasts.append(dict(horizon_s=horizon * STEP_S, target=target, model=a, reference=b,
                                      delta_mae=delta.mean(), lower_95=low, upper_95=high,
                                      improved_heats=int(np.sum(delta < 0)), heats=len(delta)))
    return summary, contrasts


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def load_heats(exports):
    with heat_exports(exports) as directory:
        heats = [load_heat(path) for path in sorted(directory.glob("*.npz"))]
    return sorted(heats, key=lambda heat: heat.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path, help="Directory of verified per-heat NPZ files")
    parser.add_argument("--lags", type=Path, default=CURRENT_LAGS)
    parser.add_argument("--output", type=Path, default=ROOT / "q3" / "results")
    args = parser.parse_args()
    heats = load_heats(args.exports)
    if len(heats) != 10 or len({heat.name for heat in heats}) != len(heats):
        parser.error("Expected ten distinct heat exports")
    scores, weights, series = evaluate(heats, read_lag_candidates(args.lags))
    summary, contrasts = summarize(scores)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, rows in (("validation", scores), ("summary", summary), ("contrasts", contrasts),
                       ("weights", weights), ("predictions", series)):
        write_csv(args.output / f"{name}.csv", rows)


if __name__ == "__main__":
    main()

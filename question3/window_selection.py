"""Nested leave-one-heat-out window selection for the 10-second forecast."""
import argparse
from pathlib import Path
import numpy as np
if __package__:
    from .run import features, fit_predict, read_heats, write_csv
else:
    from run import features, fit_predict, read_heats, write_csv
from q3.data import heat_exports

ALPHAS = (1, 10, 100)


def evaluate(directory, output):
    targets = {}
    windows = {name: {} for name in ("current", "5s", "10s", "20s", "all")}
    for heat, (data, wave, eligible) in read_heats(directory).items():
        if not eligible[60:].any():
            continue
        bands, history, _ = features(data, wave)
        rows = np.flatnonzero(eligible[60:]) + 60
        targets[heat] = data[rows, -2:]
        windows["current"][heat] = bands[rows - 20]
        windows["all"][heat] = history[rows - 20]
        for index, name in enumerate(("5s", "10s", "20s")):
            start = 16 + 32 * index
            windows[name][heat] = np.column_stack((bands, history[:, start:start + 32]))[rows - 20]

    def predict(inputs, training, test, alpha):
        return fit_predict(np.vstack([inputs[h] for h in training]),
                           np.vstack([targets[h] for h in training]), inputs[test], alpha)

    rows, candidates = [], []
    for test, actual in targets.items():
        training = [h for h in targets if h != test]
        scores = {}
        for name, inputs in windows.items():
            for alpha in ALPHAS:
                errors = []
                for valid in training:
                    inner = [h for h in training if h != valid]
                    pred = predict(inputs, inner, valid, alpha)
                    errors.append(np.abs(pred - targets[valid]).mean(axis=0))
                scores[name, alpha] = np.mean(errors, axis=0)
                candidates.append(dict(test=test, window=name, alpha=alpha,
                                       inner_MAE_CO2=scores[name, alpha][0], inner_MAE_CO=scores[name, alpha][1]))
        baseline = {}
        for name in ("current", "all"):
            pred = predict(windows[name], training, test, 10)
            baseline[name] = np.abs(pred - actual).mean(axis=0)
        for j, gas in enumerate(("CO2", "CO")):
            name, alpha = min(scores, key=lambda key: scores[key][j])
            err = predict(windows[name], training, test, alpha)[:, j] - actual[:, j]
            mae = np.abs(err).mean()
            rows.append(dict(heat=test, gas=gas, window=name, alpha=alpha, n=len(err),
                             MAE=mae, RMSE=np.sqrt(np.mean(err**2)), bias=err.mean(),
                             current_MAE=baseline["current"][j], all_MAE=baseline["all"][j],
                             delta_vs_current=mae-baseline["current"][j], delta_vs_all=mae-baseline["all"][j]))
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "window_selection.csv", rows)
    write_csv(output / "window_inner_scores.csv", candidates)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Directory of heat NPZ files or legacy NPY cache")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "results")
    args = parser.parse_args()
    with heat_exports(args.input) as directory:
        evaluate(directory, args.output)

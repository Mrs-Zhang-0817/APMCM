"""Continuous offline process curves and sensitivity to their reconstruction."""

from dataclasses import dataclass

import numpy as np


@dataclass
class Process:
    time: np.ndarray
    raw: tuple
    knots: tuple
    changes: list
    dense_time: np.ndarray
    dense: tuple
    flow_at_observations: np.ndarray
    balance: dict
    all_zero: bool


def clean_knots(time, values, name):
    invalid = ~np.isfinite(values) | (values < 0)
    isolated = np.zeros(len(values), dtype=bool)
    left, middle, right = values[:-2], values[1:-1], values[2:]
    neighbors_valid = ~(invalid[:-2] | invalid[1:-1] | invalid[2:])
    if name == "oxygen":
        isolated[1:-1] = neighbors_valid & (left <= right) & ((middle < left) | (middle > right))
    else:
        excursion = ((middle - left) * (middle - right) > 0) & (
            np.minimum(np.abs(middle - left), np.abs(middle - right)) >= 3
        )
        isolated[1:-1] = neighbors_valid & (np.abs(left - right) <= 0.2) & excursion
    bad = invalid | isolated
    if bad[0] or bad[-1] or not np.any(~bad):
        raise ValueError(f"{name} has no defensible interpolation at the record boundary")
    cleaned = values.copy()
    cleaned[bad] = np.interp(time[bad], time[~bad], values[~bad])
    if name == "oxygen" and np.any(np.diff(cleaned) < 0):
        raise ValueError("Cumulative oxygen contains an unresolved multi-sample decrease")
    changes = [dict(signal=name, time_s=time[i], original=values[i], replacement=cleaned[i],
                    reason="nonfinite_or_negative" if invalid[i] else "isolated_excursion")
               for i in np.flatnonzero(bad)]
    return cleaned, changes


def monotone_slopes(x, y):
    gaps = np.diff(x)
    secants = np.diff(y) / gaps
    if len(secants) == 1:
        return np.repeat(secants, 2)
    first, last = secants[:-1], secants[1:]
    left_weight = 2 * gaps[1:] + gaps[:-1]
    right_weight = gaps[1:] + 2 * gaps[:-1]
    interior = np.zeros(len(x) - 2)
    increasing = (first > 0) & (last > 0)
    interior[increasing] = (left_weight + right_weight)[increasing] / (
        left_weight[increasing] / first[increasing] + right_weight[increasing] / last[increasing]
    )
    ends = []
    for h0, h1, m0, m1 in ((gaps[0], gaps[1], secants[0], secants[1]),
                           (gaps[-1], gaps[-2], secants[-1], secants[-2])):
        estimate = ((2 * h0 + h1) * m0 - h0 * m1) / (h0 + h1)
        ends.append(np.clip(estimate, 0, 3 * m0))
    return np.r_[ends[0], interior, ends[1]]


def oxygen_model(time, oxygen):
    # Keep the start and finish and interpolate every 11th observation (5.5 s).
    keep = np.unique(np.r_[np.arange(0, len(time), 11), len(time) - 1])
    x, y = time[keep], oxygen[keep]
    h, dy = np.diff(x), np.diff(y)
    d = monotone_slopes(x, y)
    b = h * d[:-1]
    c = 3 * dy - h * (2 * d[:-1] + d[1:])
    e = -2 * dy + h * (d[:-1] + d[1:])

    def evaluate(at):
        k = np.clip(np.searchsorted(x, at, side="right") - 1, 0, len(h) - 1)
        u = (at - x[k]) / h[k]
        return y[k] + u * (b[k] + u * (c[k] + u * e[k])), (b[k] + u * (2*c[k] + 3*u*e[k])) / h[k]

    # Simpson's rule is exact on each quadratic derivative segment.
    simpson = np.sum(h * (d[:-1] + 4 * evaluate((x[:-1] + x[1:]) / 2)[1] + d[1:]) / 6)
    return evaluate, simpson, len(x)


def gas_curves(time, gas, dense_time):
    intervals = np.diff(time)
    integral_knots = np.r_[0.0, np.cumsum(intervals * (gas[:-1] + gas[1:]) / 2)]
    left = np.clip(np.searchsorted(time, dense_time, side="right") - 1, 0, len(time) - 2)
    delta = dense_time - time[left]
    slope = np.diff(gas)[left] / intervals[left]
    return gas[left] + slope * delta, integral_knots[left] + gas[left] * delta + slope * delta**2 / 2


def reconstruct(time, oxygen, co2, co):
    raw = (oxygen, co2, co)
    knots, changes = [], []
    for name, values in zip(("oxygen", "CO2", "CO"), raw):
        cleaned, edits = clean_knots(time, values, name)
        knots.append(cleaned)
        changes.extend(edits)
    dense_time = np.linspace(time[0], time[-1], 5 * (len(time) - 1) + 1)
    evaluate_oxygen, integrated, anchors = oxygen_model(time, knots[0])
    dense_oxygen, dense_flow = evaluate_oxygen(dense_time)
    dense_co2, co2_integral = gas_curves(time, knots[1], dense_time)
    dense_co, co_integral = gas_curves(time, knots[2], dense_time)
    raw_change = oxygen[-1] - oxygen[0]
    trapezoid = np.sum(np.diff(dense_time) * (dense_flow[:-1] + dense_flow[1:]) / 2)
    np.testing.assert_allclose(integrated, raw_change, rtol=0, atol=1e-9)
    if np.min(dense_flow) < -1e-9:
        raise ValueError("Shape-preserving oxygen fit produced a negative flow")
    balance = dict(oxygen_anchors=anchors, raw_oxygen_change_m3=raw_change,
                   integrated_flow_m3=integrated, balance_error_m3=integrated - raw_change,
                   trapezoid_0p1s_error_m3=trapezoid - raw_change, raw_peak_flow_m3_s=np.max(np.diff(oxygen)/np.diff(time)),
                   reconstructed_grid_peak_flow_m3_s=np.max(dense_flow), final_co2_m3=co2_integral[-1],
                   final_co_m3=co_integral[-1])
    dense = (dense_flow, dense_oxygen, dense_co2, dense_co, co2_integral, co_integral)
    return Process(time, raw, tuple(knots), changes, dense_time, dense, evaluate_oxygen(time)[1], balance,
                   bool(np.all(co2 == 0) and np.all(co == 0)))


def correlation(left, right):
    return np.corrcoef(left, right)[0, 1] if min(left.std(), right.std()) > 1e-8 else np.nan


def backward_mean(values):
    return np.convolve(np.pad(values, (10, 0), mode="edge"), np.ones(11) / 11, "valid")


def five_second_change(values):
    return values - np.roll(values, 10)


def lag_sensitivity(process, recorded):
    """Change the archived inputs while preserving the archived scan settings."""
    oxygen, _, _ = process.raw
    display_flow = process.flow_at_observations
    i = np.arange(21, len(oxygen) - 80)
    rows = []
    for target, gas in zip(("CO2", "CO"), process.knots[1:]):
        y = five_second_change(backward_mean(gas))
        x = five_second_change(display_flow)
        groups = {
            "all": i, "first": i[i < len(oxygen) / 2], "second": i[i >= len(oxygen) / 2],
            "low": i[display_flow[i] <= np.quantile(display_flow[i], .33)],
            "high": i[display_flow[i] >= np.quantile(display_flow[i], .67)],
        }
        for group, j in groups.items():
            previous = recorded[target, group]
            peak = np.array([correlation(x[j], y[j + k]) for k in range(81)])
            if np.isnan(peak).all():
                continue
            k = np.nanargmax(np.abs(peak))
            rows.append(dict(target=target, group=group, audit_n=int(previous["n"]), audit_lag_s=float(previous["lag_s"]),
                             audit_r=float(previous["r"]), reconstructed_n=len(j), reconstructed_lag_s=k / 2,
                             reconstructed_r=peak[k], reconstructed_r0=peak[0],
                             reconstructed_flow_median=np.median(display_flow[j]),
                             candidate_shift_s=k / 2 - float(previous["lag_s"])))
    return rows


def oxygen_associations(process):
    oxygen = process.raw[0]
    reconstructed = np.interp(process.time, process.dense_time, process.dense[1])
    for name, original, cleaned in zip(("CO2", "CO", "CO2_integral", "CO_integral"),
                                       (*process.raw[1:], *(gas_curves(process.time, g, process.time)[1]
                                                            for g in process.raw[1:])),
                                       (*process.knots[1:], *(gas_curves(process.time, g, process.time)[1]
                                                              for g in process.knots[1:]))):
        r_raw, r_reconstructed = correlation(oxygen, original), correlation(reconstructed, cleaned)
        yield dict(target=name, audit_r=r_raw, reconstructed_r=r_reconstructed,
                   difference=r_reconstructed - r_raw)

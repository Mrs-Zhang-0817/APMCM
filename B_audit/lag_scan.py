"""Candidate lag scans shared by the data audit and the process reconstruction."""

import numpy as np


def smooth(values, width, kernel=None):
    if kernel is None:
        kernel = np.ones(width)
    return np.convolve(np.pad(values, (width - 1, 0), mode="edge"), kernel / kernel.sum(), "valid")


def corr(x, y):
    return np.corrcoef(x, y)[0, 1] if min(x.std(), y.std()) > 1e-8 else np.nan


def five_second_change(values):
    return values - np.roll(values, 10)


def flow_groups(flow, indices):
    local = flow[indices]
    return {
        "all": indices,
        "first": indices[indices < len(flow) / 2],
        "second": indices[indices >= len(flow) / 2],
        "low": indices[local <= np.quantile(local, .33)],
        "high": indices[local >= np.quantile(local, .67)],
    }


def peak(x, y, indices, shifts):
    correlations = np.array([corr(x[indices], y[indices + step]) for step in shifts])
    if np.isnan(correlations).all():
        return None
    index = np.nanargmax(np.abs(correlations))
    return shifts[index] / 2, correlations[index]


def forward_lags(heat, oxygen, co2, co, brightness):
    step_flow = np.diff(oxygen, prepend=oxygen[0]) * 2
    for width in (5, 11, 31):
        flow, light = smooth(step_flow, width), smooth(brightness, width)
        groups = flow_groups(flow, np.arange(width + 10, len(flow) - 80))
        for target, gas in (("CO2", co2), ("CO", co)):
            gas_smoothed = smooth(gas, width)
            for source, signal in (("flow", flow), ("brightness", light)):
                for transform, x, y in (("level", signal, gas_smoothed),
                                        ("change", five_second_change(signal), five_second_change(gas_smoothed))):
                    for group, indices in groups.items():
                        if len(indices) < 40:
                            continue
                        result = peak(x, y, indices, range(81))
                        if result is not None:
                            lag, r = result
                            yield dict(heat=heat, window_s=width/2, target=target, source=source,
                                       transform=transform, group=group, n=len(indices), lag_s=lag, r=r,
                                       r0=corr(x[indices], y[indices]), flow_median=np.median(flow[indices]))


def signed_lags(heat, oxygen, co2, co):
    step_flow = np.diff(oxygen, prepend=oxygen[0]) * 2
    for width in (5, 11, 31):
        kernels = (("box", np.ones(width)),
                   ("triangle", np.r_[np.arange(1, width // 2 + 2), np.arange(width // 2, 0, -1)]))
        indices = np.arange(80 + width + 10, len(oxygen) - 80)
        for method, kernel in kernels:
            x = five_second_change(smooth(step_flow, width, kernel))
            for target, gas in (("CO", co), ("CO2", co2)):
                y = five_second_change(smooth(gas, width, kernel))
                result = peak(x, y, indices, range(-80, 81))
                if result is not None:
                    lag, r = result
                    yield dict(heat=heat, method=method, window=width/2, target=target, lag=lag, r=r)

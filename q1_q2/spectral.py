"""Offline spectral screening and reconstruction on the native heat grid."""

import numpy as np


HOLDOUT_SEED = 20261126
HOLDOUT_COUNT = 1000


def isolated_points(values, valid):
    """Require an excursion beyond all four valid axial neighbors."""
    candidate = np.zeros(values.shape, dtype=bool)
    # Bound the temporary arrays for the full-resolution spectral matrices.
    for start in range(1, len(values) - 1, 128):
        end = min(start + 128, len(values) - 1)
        core = values[start:end, 1:-1]
        neighbors = np.stack((
            values[start - 1:end - 1, 1:-1], values[start + 1:end + 1, 1:-1],
            values[start:end, :-2], values[start:end, 2:],
        ))
        eligible = (valid[start:end, 1:-1] & valid[start - 1:end - 1, 1:-1]
                    & valid[start + 1:end + 1, 1:-1] & valid[start:end, :-2] & valid[start:end, 2:])
        center = np.median(neighbors, axis=0)
        mad = np.median(np.abs(neighbors - center), axis=0)
        threshold = np.maximum(1000, 8 * 1.4826 * mad)
        outside = (core > neighbors.max(axis=0)) | (core < neighbors.min(axis=0))
        candidate[start:end, 1:-1] = eligible & outside & (np.abs(core - center) > threshold)
    return candidate


def repair_grid(values, time, wave, flags, held_out=None):
    missing = (flags & 5) != 0
    if held_out is not None:
        missing |= held_out
    observed = values.copy()
    observed[missing] = np.nan
    available = (flags == 0) & ~missing
    spikes = isolated_points(observed, available)
    repair = missing | spikes
    donor = available & ~spikes
    repaired = observed.copy()
    for i, j in np.argwhere(repair):
        vertical = np.flatnonzero(donor[:, j])
        horizontal = np.flatnonzero(donor[i])
        for indices, target, coord, line in (
            (horizontal, j, wave, observed[i]),
            (vertical, i, time, observed[:, j]),
        ):
            at = np.searchsorted(indices, target)
            if 0 < at < len(indices):
                pair = indices[at - 1:at + 1]
                repaired[i, j] = np.interp(coord[target], coord[pair], line[pair])
                break
        else:
            raise ValueError(f"No bracketing measured donors for spectral cell ({i}, {j})")
    return repaired, repair


def holdout_mask(flags, repaired, rng):
    # This screen defines the evaluation population only. It supplies no donors,
    # estimates or anomaly decisions to the masked reconstruction.
    good = (flags == 0) & ~repaired
    eligible = (good[1:-1, 1:-1] & good[:-2, 1:-1] & good[2:, 1:-1]
                & good[1:-1, :-2] & good[1:-1, 2:])
    row, col = np.nonzero(eligible)
    row, col = row + 1, col + 1
    row_phase, col_phase = rng.integers(3, size=2)
    phase = (row % 3 == row_phase) & (col % 3 == col_phase)
    pool = np.flatnonzero(phase)
    take = rng.choice(pool, size=HOLDOUT_COUNT, replace=False)
    masked = np.zeros(flags.shape, dtype=bool)
    masked[row[take], col[take]] = True
    return masked


def surface_grid(values, time, wave, max_rows=121, max_columns=181):
    """Evaluate the tensor-product piecewise bilinear field on a display grid."""
    plot_time = np.linspace(time[0], time[-1], min(len(time), max_rows))
    plot_wave = np.linspace(wave[0], wave[-1], min(len(wave), max_columns))
    along_wave = np.stack([np.interp(plot_wave, wave, row) for row in values])
    plot_values = np.stack([np.interp(plot_time, time, col) for col in along_wave.T], axis=1)
    return plot_time, plot_wave, plot_values


def supported_peak(values, flags, repaired):
    """Select a prominent measured peak supported on both axes for display."""
    core = values[2:-2, 5:-5]
    edge = np.maximum(values[2:-2, :-10], values[2:-2, 10:])
    prominence = core - edge
    support = ((values[1:-3, 5:-5] >= 0.8 * core) & (values[3:-1, 5:-5] >= 0.8 * core)
               & (values[2:-2, 4:-6] >= 0.8 * core) & (values[2:-2, 6:-4] >= 0.8 * core)
               & (values[2:-2, 4:-6] <= core) & (values[2:-2, 6:-4] <= core))
    # A representative window must be entirely observed, unmodified and unclipped.
    bad = (flags != 0) | repaired
    scores = np.where(support, prominence, -np.inf).ravel()
    best = np.argpartition(scores, -512)[-512:]
    ranked = best[np.argsort(scores[best])[::-1]]
    for i, j in zip(*np.unravel_index(ranked, core.shape)):
        if not support[i, j] or prominence[i, j] <= 0:
            break
        i, j = int(i + 2), int(j + 5)
        if 6 <= i < len(values) - 6 and 10 <= j < values.shape[1] - 10 and not bad[i-6:i+7, j-10:j+11].any():
            return i, j
    return None

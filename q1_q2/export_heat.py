"""Export one heat; run with python export_heat.py INPUT.xlsb NEW_OUTPUT.npz."""
import argparse
import json
from pathlib import Path

import numpy as np
from pyxlsb import open_workbook


def valid_headers(labels):
    if len(labels) != 2051:
        return False
    sequence, oxygen, co2, co = (str(labels[i]).strip() for i in (0, -3, -2, -1))
    return (
        sequence in {"Sequence", "序列Sequence", "序列"}
        and oxygen in {"YQXH", "Cumulative oxygen consumption", "累积耗氧量"}
        and co2.replace("₂", "2") in {"CO2 concentration", "CO2浓度"}
        and co in {"CO concentration", "CO浓度"}
    )


def export(source, target, window):
    if window < 1:
        raise ValueError("window must be positive")
    with open_workbook(str(source)) as book:
        heat, = book.sheets
        with book.get_sheet(heat) as sheet:
            rows = iter(sheet.rows(sparse=True))
            labels = [cell.v for cell in next(rows)]
            if not valid_headers(labels):
                raise ValueError(f"Unexpected headers in {source}: {labels[0]!r}, {labels[-3:]!r}")
            wave = np.asarray(labels[1:-3], dtype=float)
            data = np.asarray([[c.v for c in r] for r in rows], dtype=float)
    seq = data[:, 0]
    if not np.array_equal(seq, np.arange(1, len(data) + 1)) or not np.all(np.diff(wave) > 0):
        raise ValueError("Unexpected sequence or wavelength coordinates")
    spectrum = data[:, 1:-3]
    oxygen, co2, co = data[:, -3:].T
    time = (seq - 1) * 0.5
    flow = np.full(len(time), np.nan)
    flow[window:] = (oxygen[window:] - oxygen[:-window]) / (0.5 * window)
    flags = (~np.isfinite(spectrum)).astype(np.uint8)
    flags |= (spectrum == 65535).astype(np.uint8) * 2
    flags |= (spectrum < 0).astype(np.uint8) * 4
    gas_ok = np.isfinite(co2) & np.isfinite(co) & (co2 >= 0) & (co >= 0)
    all_zero = bool(np.all(co2 == 0) and np.all(co == 0))
    payload = dict(heat_id=heat, time_s=time, wavelength_nm=wave, spectrum=spectrum,
                   oxygen_cumulative=oxygen, oxygen_flow=flow, co2=co2, co=co,
                   quality_flags=flags, gas_label_eligible=gas_ok & (not all_zero),
                   flow_window_steps=window)
    # Validate the interval balance for the one-step estimate.
    if window == 1 and np.all(np.isfinite(oxygen)):
        np.testing.assert_allclose(np.sum(flow[1:] * np.diff(time)), oxygen[-1] - oxygen[0])
    with target.open("xb") as stream:
        np.savez_compressed(stream, **payload)
    with np.load(target, allow_pickle=False) as saved:
        for key, value in payload.items():
            np.testing.assert_array_equal(saved[key], value)
    print(json.dumps(dict(heat=heat, rows=len(time), channels=len(wave), end_s=time[-1],
                          ceiling_cells=int((flags & 2 != 0).sum()),
                          duplicate_adjacent_traces=int(np.all(spectrum[:, 1:] == spectrum[:, :-1], axis=0).sum()),
                          decreasing_oxygen_steps=int((np.diff(oxygen)<0).sum()),
                          oxygen_first=oxygen[0], oxygen_last=oxygen[-1],
                          co2_max=float(co2.max()), co_max=float(co.max()),
                          all_zero_gas=all_zero)))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--window", type=int, default=1)
    args = p.parse_args()
    export(args.source, args.output, args.window)

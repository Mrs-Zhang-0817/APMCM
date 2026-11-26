"""Generate the first two questions' offline figures and validation tables."""

import argparse
import csv
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from q1_q2.formal_figures import gas_window, oxygen_window, process_panels, spectral_surface, spectral_windows
from q1_q2.process_curves import lag_sensitivity, oxygen_associations, reconstruct
from q1_q2.spectral import HOLDOUT_SEED, holdout_mask, repair_grid, supported_peak, surface_grid


ROOT = Path(__file__).resolve().parents[1]
HEATS = ("6B03205", "6B03206", "6B03270", "6B03271", "6C02057", "6C02058",
         "6C02059", "6C02060", "6C02107", "6C02108")


@contextmanager
def heat_exports(directory):
    if directory is not None:
        yield directory
        return
    from q1_q2.export_heat import export

    with TemporaryDirectory() as temp:
        directory = Path(temp)
        for i, heat in enumerate(HEATS, 1):
            source = ROOT / "work_b" / "Data" / f"Attachment {i}. Heat No. {heat}.xlsb"
            export(source, directory / f"{heat}.npz", 1)
        yield directory


def read_audit_lags():
    with (ROOT / "B_audit" / "lags.csv").open(encoding="utf-8-sig", newline="") as stream:
        return {(row["heat"], row["target"], row["group"]): row for row in csv.DictReader(stream)
                if (float(row["window_s"]), row["source"], row["transform"]) == (5.5, "flow", "change")}


def write_table(path, rows, columns=None):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def coordinates(heat, time, wave, i, j):
    return dict(heat=heat, row_index=i, channel_index=j, time_s=time[i], wavelength_nm=wave[j])


def errors_row(heat, error):
    return dict(heat=heat, test_points=len(error), mae=np.mean(np.abs(error)),
                rmse=np.sqrt(np.mean(error**2)))


def save_reconstruction(path, heat, time, wave, raw, clean, flags, changed, process):
    np.savez_compressed(
        path / f"{heat}.npz", heat_id=heat, time_s=time, wavelength_nm=wave,
        original_spectrum=raw, reconstructed_spectrum=clean, repair_mask=changed,
        original_quality_flags=flags, clipped_mask=(flags & 2) != 0,
        original_oxygen_cumulative=process.raw[0], original_co2=process.raw[1], original_co=process.raw[2],
        oxygen_knots=process.knots[0], co2_knots=process.knots[1], co_knots=process.knots[2],
        plot_time_s=process.dense_time, plot_oxygen_flow=process.dense[0],
        plot_oxygen_cumulative=process.dense[1], plot_co2=process.dense[2], plot_co=process.dense[3],
        plot_co2_total=process.dense[4], plot_co_total=process.dense[5],
    )


def spectral_example(kind, example):
    heat, time, wave, raw, clean, i, j = example
    return dict(kind=kind, **coordinates(heat, time, wave, i, j), original=raw[i, j], reconstructed=clean[i, j],
                earlier=raw[i-1, j], later=raw[i+1, j], shorter_wave=raw[i, j-1], longer_wave=raw[i, j+1])


def run(exports, output, reconstruction_path):
    surface_dir, process_dir = output / "spectra", output / "process"
    for directory in (surface_dir, process_dir, reconstruction_path):
        if directory is not None:
            directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(HOLDOUT_SEED)
    audit = read_audit_lags()
    errors, pooled, holdouts, repairs, grids = [], [], [], [], []
    balances, process_edits, lag_cases, associations = [], [], [], []
    spike_example, peak_example, process_example, gas_example = None, None, None, None

    for heat in HEATS:
        with np.load(exports / f"{heat}.npz", allow_pickle=False) as data:
            if data["heat_id"].item() != heat:
                raise ValueError(f"Unexpected identifier in {heat}.npz")
            time, wave, raw, flags = (data[key] for key in ("time_s", "wavelength_nm", "spectrum", "quality_flags"))
            process = reconstruct(time, data["oxygen_cumulative"], data["co2"], data["co"])
        np.testing.assert_array_equal(time, np.arange(len(time)) / 2)
        if not np.all(np.diff(wave) > 0):
            raise ValueError(f"Wavelengths must be strictly increasing for {heat}")
        clean, changed = repair_grid(raw, time, wave, flags)
        np.testing.assert_array_equal(clean[~changed], raw[~changed])
        np.testing.assert_array_equal(clean[(flags & 2) != 0], raw[(flags & 2) != 0])
        for i, j in np.argwhere(changed):
            repairs.append(dict(**coordinates(heat, time, wave, i, j), original=raw[i, j], replacement=clean[i, j],
                                reason="nonfinite_or_negative" if flags[i, j] & 5 else "isolated_excursion"))

        test = holdout_mask(flags, changed, rng)
        estimated, _ = repair_grid(raw, time, wave, flags, test)
        error = estimated[test] - raw[test]
        errors.append(errors_row(heat, error))
        pooled.append(error)
        for i, j in np.argwhere(test):
            holdouts.append(dict(**coordinates(heat, time, wave, i, j), measured=raw[i, j], predicted=estimated[i, j]))

        render_t, render_w, render_z = surface_grid(clean, time, wave)
        spectral_surface(heat, render_t, render_w, render_z, surface_dir / f"{heat}.png")
        grids.append(dict(heat=heat, time_nodes=len(time), wavelength_nodes=len(wave), end_s=time[-1],
                          wavelength_min_nm=wave[0], wavelength_max_nm=wave[-1], repairs=int(changed.sum()),
                          clipped_cells=int(np.sum((flags & 2) != 0)), plot_time_nodes=len(render_t),
                          plot_wavelength_nodes=len(render_w), plot_dt_s=render_t[1]-render_t[0],
                          plot_dw_nm=render_w[1]-render_w[0]))

        if spike_example is None and changed[6:-6, 10:-10].any():
            i, j = np.unravel_index(np.argmax(np.where(changed[6:-6, 10:-10],
                                                       np.abs(raw-clean)[6:-6, 10:-10], -np.inf)),
                                    changed[6:-6, 10:-10].shape)
            spike_example = (heat, time, wave, raw, clean, i + 6, j + 10)
        if peak_example is None and (peak := supported_peak(raw, flags, changed)) is not None:
            peak_example = (heat, time, wave, raw, clean, *peak)

        process_panels(heat, process, process_dir / f"{heat}.png")
        balances.append(dict(heat=heat, end_s=time[-1], plot_step_s=0.1, **process.balance,
                             oxygen_edits=sum(row["signal"] == "oxygen" for row in process.changes),
                             co2_edits=sum(row["signal"] == "CO2" for row in process.changes),
                             co_edits=sum(row["signal"] == "CO" for row in process.changes),
                             zero_gas_record=process.all_zero))
        process_edits.extend(dict(heat=heat, **row) for row in process.changes)
        associations.extend(dict(heat=heat, **row) for row in oxygen_associations(process))
        if not process.all_zero:
            recorded = {(target, group): audit[heat, target, group] for target in ("CO2", "CO")
                        for group in ("all", "first", "second", "low", "high")}
            lag_cases.extend(dict(heat=heat, **row) for row in lag_sensitivity(process, recorded))
        j = np.argmax(np.abs(process.dense[1][::5] - process.raw[0]))
        delta = process.dense[1][5*j] - process.raw[0][j]
        if process_example is None or abs(delta) > abs(process_example[3]):
            process_example = heat, process, j, delta
        gas_edits = [row for row in process.changes if row["signal"] != "oxygen"]
        if gas_example is None and gas_edits:
            gas_example = heat, process, gas_edits[0]
        if reconstruction_path is not None:
            save_reconstruction(reconstruction_path, heat, time, wave, raw, clean, flags, changed, process)
        print(f"{heat}: {grids[-1]['repairs']} spectral repairs, {errors[-1]['test_points']} masked points")

    spectral_windows((spike_example, peak_example), output / "spectral_windows.png")
    examples = [spectral_example("isolated_excursion", spike_example), spectral_example("supported_peak", peak_example)]
    heat, process, j, delta = process_example
    oxygen_window(heat, process, process.time[j], output / "oxygen_window.png")
    process_notes = [dict(heat=heat, signal="oxygen_reconstructed_curve", time_s=process.time[j],
                          original=process.raw[0][j], replacement=process.raw[0][j]+delta,
                          reason="maximum_deviation_from_measurement")]
    if gas_example is not None:
        heat, process, edit = gas_example
        gas_window(heat, edit["signal"], process, edit["time_s"], output / "gas_window.png")
        process_notes.append(dict(heat=heat, **edit))
    for name, rows in (
        ("spectral_errors", [*errors, errors_row("pooled", np.concatenate(pooled))]),
        ("spectral_holdouts", holdouts), ("spectral_repairs", repairs), ("spectral_grids", grids),
        ("spectral_examples", examples), ("process_balance", balances), ("process_examples", process_notes),
        ("oxygen_association_sensitivity", associations), ("lag_sensitivity", lag_cases),
    ):
        write_table(output / f"{name}.csv", rows)
    write_table(output / "process_repairs.csv", process_edits,
                ("heat", "signal", "time_s", "original", "replacement", "reason"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path, help="Directory containing the verified heat interface files")
    parser.add_argument("--output", type=Path, default=ROOT / "q1_q2" / "results")
    parser.add_argument("--reconstructed", type=Path, help="Optional directory for full offline arrays and masks")
    args = parser.parse_args()
    with heat_exports(args.exports) as directory:
        run(directory, args.output, args.reconstructed)

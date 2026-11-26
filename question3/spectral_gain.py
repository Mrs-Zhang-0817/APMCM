"""Paired 10 s ablation using the teammate's pinned process and spectral features."""
import argparse
import csv
import importlib.util
import io
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from run import BAD_HEAT, ROOT, read_heats, write_csv

REVISION = "e1222adedd9aed1a9911d10b63c78b899ab66914"


def snapshot(path):
    return subprocess.check_output(["git", "show", f"{REVISION}:{path}"], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "B_audit")
    parser.add_argument("--clip-test", action="store_true",
                        help="Compare raw fusion with within-frame interpolation at clipped channels")
    parser.add_argument("--lag-test", action="store_true", help="Evaluate the training-only lag rule")
    args = parser.parse_args()
    if args.lag_test and args.clip_test:
        parser.error("Run each ablation separately")
    reference = {}
    for row in csv.DictReader(io.StringIO(snapshot("q3/results/predictions.csv").decode("utf-8-sig"))):
        if row["eligible"] == "True" and float(row["horizon_s"]) == 10:
            key = row["heat"], float(row["target_s"])
            reference[key] = [float(row[f"process_history_{g}"]) for g in ("CO2", "CO")]
    records = []
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / "peer_q3.py"
        script.write_bytes(snapshot("q3/predict.py"))
        spec = importlib.util.spec_from_file_location("peer_q3", script)
        peer = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = peer
        spec.loader.exec_module(peer)
        lag_file = Path(folder) / "signed_lags.csv"
        lag_file.write_bytes(snapshot("B_audit/signed_lags.csv"))
        candidates = peer.read_lag_candidates(lag_file) if args.lag_test else {}
        heats = []
        for name, (a, wave) in read_heats(args.input).items():
            if name == BAD_HEAT:
                continue
            spectra = a[:, 1:-3]
            assert np.isfinite(a).all() and (spectra >= 0).all() and (a[:, -2:] >= 0).all()
            npz = Path(folder) / "heat.npz"
            np.savez(npz, heat_id=name, time_s=(a[:, 0]-1)*0.5, oxygen_cumulative=a[:, -3],
                     co2=a[:, -2], co=a[:, -1], wavelength_nm=wave, spectrum=spectra,
                     quality_flags=(spectra == 65535).astype(np.uint8)*2,
                     gas_label_eligible=np.ones(len(a), dtype=bool))
            heat = peer.load_heat(npz)
            if args.clip_test:
                # The original clipping indicator stays available in both models.
                # Estimate only interior clipped channels between observed wavelengths.
                clipped = spectra == 65535
                cleaned = spectra.copy()
                for i in np.flatnonzero(clipped.any(axis=1)):
                    good = ~clipped[i]
                    if good.sum() < 2:
                        continue
                    interior = clipped[i] & (wave > wave[good][0]) & (wave < wave[good][-1])
                    cleaned[i, interior] = np.interp(wave[interior], wave[good], spectra[i, good])
                with np.load(npz) as saved:
                    payload = dict(saved)
                payload["spectrum"] = cleaned
                np.savez(npz, **payload)
                heat.features["clean_fusion"] = peer.load_heat(npz).features["fusion_history"]
            heats.append(heat)
        for test in heats:
            training = [h for h in heats if h.name != test.name]
            indices = [peer.target_indices(h) for h in training]
            targets = [h.gas[idx] for h, idx in zip(training, indices)]
            rows = np.arange(60, len(test.time))
            if args.lag_test:
                members, lags = peer.predict_members(training, test, 20, candidates)
                target_times = peer.target_indices(test)
                selected = target_times >= 60
                assert np.array_equal(target_times[selected], rows)
                base = members[selected, peer.MODELS.index("fusion_history")]
                adjusted = members[selected, peer.MODELS.index("lag_fusion")]
                for j, gas in enumerate(peer.TARGETS):
                    lag, count = lags[j]
                    contributors = [h.name for h in training if (h.name, gas) in candidates]
                    assert count == len(contributors) and test.name not in contributors
                    active = lag > 10
                    if not active:
                        np.testing.assert_array_equal(base[:, j], adjusted[:, j])
                    truth = test.gas[rows, j]
                    before = np.abs(base[:, j] - truth).mean()
                    after = np.abs(adjusted[:, j] - truth).mean()
                    records.append(dict(heat=test.name, gas=gas, n=len(rows), eligible_heats=count,
                                        contributing_heats="|".join(contributors), rule_lag_s=lag,
                                        active=active, extra_lookback_s=max(0, lag-10),
                                        baseline_MAE=before, lag_MAE=after, delta_MAE=after-before))
                continue
            errors = []
            for model in (("fusion_history", "clean_fusion") if args.clip_test else ("process_history", "fusion_history")):
                x = [peer.design(h, idx, 20, model) for h, idx in zip(training, indices)]
                pred = np.maximum(0, peer.fit_ridge(x, targets, peer.design(test, rows, 20, model), 100))
                if model == "process_history":
                    expected = [reference[test.name, t] for t in test.time[rows]]
                    np.testing.assert_allclose(pred, expected, atol=0.00000051, rtol=0)
                errors.append(np.abs(pred-test.gas[rows]).mean(axis=0))
            for j, gas in enumerate(peer.TARGETS):
                base, fusion = (err[j] for err in errors)
                if args.clip_test:
                    records.append(dict(heat=test.name, gas=gas, n=len(rows), raw_MAE=base,
                                        clean_MAE=fusion, delta_MAE=fusion-base))
                    continue
                records.append(dict(heat=test.name, gas=gas, n=len(rows), process_MAE=base,
                                    with_spectra_MAE=fusion, delta_MAE=fusion-base))
    if args.lag_test:
        output = ROOT / "question3/results/lag_test_10s.csv"
        with (output.parent / "spectral_gain_10s.csv").open(encoding="utf-8-sig") as stream:
            previous = {(r["heat"], r["gas"]): float(r["with_spectra_MAE"]) for r in csv.DictReader(stream)}
        for r in records:
            np.testing.assert_allclose(r["baseline_MAE"], previous[r["heat"], r["gas"]])
            print(r["heat"], r["gas"], r["eligible_heats"], r["rule_lag_s"], round(r["delta_MAE"],4))
        write_csv(output, records)
        for gas in ("CO", "CO2"):
            group = [r for r in records if r["gas"] == gas]
            print(gas, np.mean([r["baseline_MAE"] for r in group]), np.mean([r["lag_MAE"] for r in group]))
        return
    if args.clip_test:
        output = ROOT / "question3/results/clip_test_10s.csv"
        previous = ROOT / "question3/results/spectral_gain_10s.csv"
        with previous.open(encoding="utf-8-sig") as stream:
            raw = {(r["heat"], r["gas"]): float(r["with_spectra_MAE"]) for r in csv.DictReader(stream)}
        for r in records:
            np.testing.assert_allclose(r["raw_MAE"], raw[r["heat"], r["gas"]], atol=1e-9)
        write_csv(output, records)
        for r in records:
            print(r["heat"], r["gas"], round(r["clean_MAE"], 5), round(r["delta_MAE"], 5))
        return
    output = ROOT / "question3/results/spectral_gain_10s.csv"
    output.parent.mkdir(exist_ok=True)
    write_csv(output, records)
    for gas in ("CO", "CO2"):
        group = [r for r in records if r["gas"] == gas]
        print(gas, *(round(np.mean([r[k] for r in group]), 3) for k in
                     ("process_MAE", "with_spectra_MAE", "delta_MAE")),
              sum(r["delta_MAE"] < 0 for r in group), "improved")
        print([(r["heat"], round(r["delta_MAE"], 2)) for r in group])


if __name__ == "__main__":
    main()

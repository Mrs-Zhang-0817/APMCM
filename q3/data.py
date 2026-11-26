"""Shared input files and label eligibility for question 3."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CURRENT_LAGS = ROOT / "q1_q2" / "results" / "signed_lags_current.csv"


@contextmanager
def heat_exports(directory=None):
    if directory is not None:
        yield directory
        return
    from q1_q2.export_heat import export

    with TemporaryDirectory() as temp:
        for i, source in enumerate(sorted((ROOT / "work_b" / "Data").glob("*.xlsb"))):
            export(source, Path(temp) / f"{i}.npz", 1)
        yield Path(temp)


def label_mask(gas):
    return (np.isfinite(gas) & (gas >= 0)).all(axis=1) & np.any(gas != 0)

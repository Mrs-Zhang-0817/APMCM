"""Read the supplied XLSB files and report their original layout and data quality."""

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from pyxlsb import open_workbook


def is_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def inspect_workbook(path):
    with open_workbook(str(path)) as workbook:
        if len(workbook.sheets) != 1:
            raise ValueError(f"{path.name}: expected one heat worksheet")
        heat = workbook.sheets[0]
        with workbook.get_sheet(heat) as sheet:
            rows = iter(sheet.rows(sparse=True))
            header = [cell.v for cell in next(rows)]
            wavelengths = header[1:-3]
            if (
                not str(header[0]).endswith("Sequence")
                or header[-3] not in ("Cumulative oxygen consumption", "YQXH")
                or header[-2:] != ["CO\u2082 concentration", "CO concentration"]
                or not wavelengths
                or not all(map(is_number, wavelengths))
                or any(a >= b for a, b in zip(wavelengths, wavelengths[1:]))
            ):
                raise ValueError(f"{path.name}: unrecognized column layout")

            signals = {key: [] for key in ("oxygen", "co2", "co")}
            sequence_issues = []
            nonnumeric_spectrum = 0
            sample_500 = None
            count = 0
            for count, row in enumerate(rows, 1):
                sequence = row[0].v
                if sequence != count:
                    sequence_issues.append({"excel_row": row[0].r + 1, "sequence": sequence})
                nonnumeric_spectrum += sum(not is_number(cell.v) for cell in row[1:-3])
                for values, cell in zip(signals.values(), row[-3:]):
                    values.append(cell.v)
                if sequence == 500:
                    sample_500 = {
                        "excel_row": row[0].r + 1,
                        "first_two_intensities": [cell.v for cell in row[1:3]],
                        "last_two_intensities": [cell.v for cell in row[-5:-3]],
                        **dict(zip(signals, (cell.v for cell in row[-3:]))),
                    }

    summary = {}
    for name, values in signals.items():
        numeric = [value for value in values if is_number(value)]
        nonzero = sum(value != 0 for value in numeric)
        summary[name] = {
            "min": min(numeric, default=None),
            "max": max(numeric, default=None),
            "nonnumeric": count - len(numeric),
            "nonzero": nonzero,
            "all_zero": count > 0 and len(numeric) == count and nonzero == 0,
        }

    return {
        "file": path.name,
        "heat": heat,
        "rows": count,
        "column_count": len(header),
        "sequence_header": header[0],
        "oxygen_header": header[-3],
        "sequence_issues": sequence_issues,
        "wavelength_count": len(wavelengths),
        "wavelength_nm": [wavelengths[0], wavelengths[-1]],
        "wavelength_grid_sha256": hashlib.sha256(json.dumps(wavelengths).encode()).hexdigest(),
        "nonnumeric_spectrum_cells": nonnumeric_spectrum,
        "signals": summary,
        "sequence_500": sample_500,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path, help="Directory containing the extracted XLSB files")
    parser.add_argument("-o", "--output", type=Path, help="Save the JSON report to this file")
    args = parser.parse_args()
    files = sorted(
        args.data.glob("Attachment *.xlsb"),
        key=lambda path: int(re.match(r"Attachment (\d+)\.", path.name)[1]),
    )
    if not files:
        parser.error(f"No attachment workbooks found in {args.data}")
    report = json.dumps([inspect_workbook(path) for path in files], indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    main()

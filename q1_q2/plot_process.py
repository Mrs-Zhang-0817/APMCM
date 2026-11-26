"""Plot unsmoothed input diagnostics for one exported heat."""
import argparse
from pathlib import Path

from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
import numpy as np


def integral(times, flow):
    increments = np.diff(times) * (flow[:-1] + flow[1:]) / 2
    return np.r_[0., np.cumsum(increments)]


def plot(source, destination):
    with np.load(source, allow_pickle=False) as data:
        heat = data["heat_id"].item()
        times = data["time_s"]
        co2, co = data["co2"], data["co"]
        series = [data["oxygen_flow"], data["oxygen_cumulative"], co2, co,
                  integral(times, co2), integral(times, co)]
        titles = ["Oxygen flow (backward estimate)", "Cumulative oxygen", "CO2 flow",
                  "CO flow", "Integrated recorded CO2", "Integrated recorded CO"]
        units = ["m³/s", "m³", "m³/s", "m³/s", "m³", "m³"]
        figure = Drawing(760, 620)
        note = "" if data["gas_label_eligible"].any() else " | gas labels unavailable"
        figure.add(String(30, 595, f"{heat} | Raw process diagnostics{note}", fontSize=16))
        for i, (values, title, unit) in enumerate(zip(series, titles, units)):
            left = 52 + (i % 2) * 375
            bottom = 425 - (i // 2) * 194
            chart = LinePlot()
            chart.x, chart.y, chart.width, chart.height = left, bottom, 288, 126
            chart.data = [[(float(t), float(v)) for t, v in zip(times, values) if np.isfinite(v)]]
            chart.xValueAxis.valueMin, chart.xValueAxis.valueMax = 0, float(times[-1])
            chart.yValueAxis.valueMin = min(0., float(np.nanmin(values)))
            chart.yValueAxis.valueMax = max(chart.yValueAxis.valueMin + 1., float(np.nanmax(values)))
            chart.lines[0].strokeColor = colors.HexColor("#20647b")
            chart.lines[0].strokeWidth = 0.8
            figure.add(chart)
            figure.add(String(left, bottom + 139, f"{title} ({unit})", fontSize=11))
            figure.add(String(left + 110, bottom - 32, "Time (s)", fontSize=9))
        figure.save(formats=["svg"], outDir=str(destination.resolve().parent), fnRoot=destination.stem)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    plot(args.source, args.destination)



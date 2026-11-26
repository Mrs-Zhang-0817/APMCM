"""Plot held-out 10-second joint predictions using the project's Pillow dependency."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from q3.predict import ROOT, TARGETS


def font(size):
    for face in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(face, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def plot_predictions(source, destination):
    heats = defaultdict(list)
    with source.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if float(row["horizon_s"]) == 10:
                heats[row["heat"]].append(row)

    image = Image.new("RGB", (1600, 1950), "white")
    draw = ImageDraw.Draw(image)
    title, label, small = font(36), font(25), font(20)
    ink, grid, measured, forecast = "#162332", "#d7dfe6", "#364453", "#007e8a"
    draw.text((80, 32), "Ten held-out heats | 10 s ahead", fill=ink, font=title)
    draw.line((80, 95, 123, 95), measured, 3)
    draw.text((132, 82), "Measured", fill=ink, font=small)
    draw.line((300, 95, 343, 95), forecast, 4)
    draw.text((352, 82), "Joint ensemble", fill=ink, font=small)
    last_time = max(float(heat[-1]["target_s"]) for heat in heats.values())
    x_max = (int(last_time) // 200 + 1) * 200

    for col, target in enumerate(TARGETS):
        observed_key = f"recorded_{target}"
        predicted_key = f"joint_ensemble_{target}"
        peak = max(float(row[key]) for heat in heats.values() for row in heat
                   for key in (observed_key, predicted_key))
        tick = 10 if col == 0 else 20
        y_max = (int(peak) // tick + 1) * tick
        left = 184 + col * 708
        width, height = 640, 135
        draw.text((left, 132), f"{target} (m³/s)", fill=ink, font=label)
        for i, (name, rows) in enumerate(heats.items()):
            top = 176 + i * 168
            bottom = top + height
            if col == 0:
                draw.text((20, top + 53), name, fill=ink, font=label)
            for x in range(0, x_max + 1, 200):
                px = left + x / x_max * width
                draw.line((px, top, px, bottom), grid, 1)
                if i == len(heats) - 1:
                    draw.text((px, bottom + 8), str(x), fill=ink, font=small, anchor="mt")
            for y in range(0, y_max + 1, tick):
                py = bottom - y / y_max * height
                draw.line((left, py, left + width, py), grid, 1)
                draw.text((left - 8, py), str(y), fill=ink, font=small, anchor="rm")
            available = [row for row in rows if row["eligible"] == "True"]
            for key, data, color in ((observed_key, available, measured), (predicted_key, rows, forecast)):
                points = [(left + float(row["target_s"]) / x_max * width,
                           bottom - float(row[key]) / y_max * height) for row in data]
                if len(points) > 1:
                    draw.line(points, color, 3)
            if not available:
                draw.text((left + 15, top + 10), "Prediction only: gas labels unavailable", fill=ink, font=small)
        draw.text((left + width / 2, 1875), "Target time (s)", fill=ink, font=label, anchor="mt")
    image.save(destination, dpi=(200, 200))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT / "q3" / "results")
    args = parser.parse_args()
    plot_predictions(args.results / "predictions.csv", args.results / "predictions_10s.png")

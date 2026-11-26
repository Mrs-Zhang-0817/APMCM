"""Render the publication figures for the offline reconstructions."""

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
import numpy as np


plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.labelcolor": "#203447", "axes.titlecolor": "#142d44",
                     "grid.color": "#d9e2ea", "savefig.facecolor": "white"})
COLOR = "#007e8a"


def save(fig, destination):
    fig.savefig(destination, dpi=170)
    plt.close(fig)


def spectral_surface(heat, time, wave, values, destination):
    fig = plt.figure(figsize=(8.2, 6.2))
    ax = fig.add_subplot(projection="3d")
    w, t = np.meshgrid(wave, time)
    surface = ax.plot_surface(w, t, values, cmap="viridis", norm=Normalize(0, 65535),
                              rstride=1, cstride=1, linewidth=0, antialiased=False)
    ax.set(xlabel="Wavelength (nm)", ylabel="Time (s)", zlabel="Intensity (W/cm²)",
           xlim=(wave[0], wave[-1]), ylim=(time[0], time[-1]), zlim=(0, 65535))
    ax.set_zticks([0, 20000, 40000, 60000])
    ax.set_box_aspect((1.2, 1, 0.65))
    ax.view_init(elev=29, azim=-59)
    fig.suptitle(f"{heat}   Reconstructed flame spectrum", y=0.95, fontsize=15)
    fig.colorbar(surface, ax=ax, shrink=0.65, pad=0.13, label="Intensity (W/cm²)")
    fig.subplots_adjust(left=0.02, right=0.92, bottom=0.08, top=0.92)
    save(fig, destination)


def spectral_windows(examples, destination):
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.5), layout="constrained", sharey="row")
    for row, example in enumerate(examples):
        heat, time, wave, raw, cleaned, i, j = example
        ir = np.arange(max(0, i - 6), min(len(time), i + 7))
        jr = np.arange(max(0, j - 10), min(len(wave), j + 11))
        blocks = [values[np.ix_(ir, jr)] for values in (raw, cleaned)]
        color = Normalize(min(np.min(block) for block in blocks), max(np.max(block) for block in blocks))
        for col, (ax, block) in enumerate(zip(axes[row], blocks)):
            pane = ax.pcolormesh(wave[jr], time[ir], block, shading="nearest", cmap="viridis", norm=color)
            ax.scatter(wave[j], time[i], s=130, facecolors="none", edgecolors="#f55e61", linewidth=1.7)
            view = "Before" if col == 0 else "After"
            label = "isolated spike" if row == 0 else "supported peak"
            value = (raw if col == 0 else cleaned)[i, j]
            ax.set_title(f"{view}   {heat} · {label} · {value:,.2f}")
            ax.set_xlabel("Wavelength (nm)")
        axes[row, 0].set_ylabel("Time (s)")
        fig.colorbar(pane, ax=axes[row], label="Intensity (W/cm²)", shrink=0.94)
    save(fig, destination)


PROCESS_AXES = (
    ("Oxygen lance flow", "m³/s"), ("Cumulative oxygen", "m³"),
    ("CO₂ flow", "m³/s"), ("CO flow", "m³/s"),
    ("Cumulative CO₂", "m³"), ("Cumulative CO", "m³"),
)


def zero_label():
    families = {font.name for font in font_manager.fontManager.ttflist}
    for family in ("Microsoft YaHei", "Noto Sans CJK SC", "SimSun", "PingFang SC"):
        if family in families:
            return "原始记录全零，标签有效性待确认", family
    return "Raw gas records all zero · label validity unconfirmed", "DejaVu Sans"


def process_panels(heat, process, destination):
    fig, axes = plt.subplots(3, 2, figsize=(10.5, 8.1), sharex=True, layout="constrained")
    fig.suptitle(f"{heat}   Continuous process curves · 0–{process.time[-1]:g} s", fontsize=15)
    for n, (ax, values, (title, unit)) in enumerate(zip(axes.flat, process.dense, PROCESS_AXES)):
        ax.plot(process.dense_time, values, color=COLOR, lw=1.3)
        ax.set(xlim=(0, process.time[-1]), ylim=(0, 1.06 * values.max() if values.max() else 1),
               title=title, ylabel=unit)
        ax.grid(alpha=0.7)
        if process.all_zero and n >= 2:
            note, family = zero_label()
            ax.text(0.04, 0.88, note, transform=ax.transAxes, ha="left", va="top",
                    fontfamily=family, fontsize=8.5, color="#8a302a")
        if n >= 4:
            ax.set_xlabel("Time (s)")
    save(fig, destination)


def oxygen_window(heat, process, center, destination):
    t = process.time
    raw = process.raw[0]
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True, layout="constrained")
    fig.suptitle(f"{heat}   Cumulative-oxygen reconstruction near {center:g} s", fontsize=14)
    axes[0].plot(t, raw, ".-", color="#657789", ms=3, lw=0.8, label="Measured")
    axes[0].plot(process.dense_time, process.dense[1], color=COLOR, lw=1.6, label="Reconstructed")
    axes[1].stairs(np.diff(raw) / np.diff(t), t, color="#657789", lw=0.85, label="Raw interval difference")
    axes[1].plot(process.dense_time, process.dense[0], color=COLOR, lw=1.6, label="Reconstructed derivative")
    limits = (max(t[0], center - 10), min(t[-1], center + 10))
    axes[0].set_ylabel("Cumulative oxygen (m³)")
    axes[1].set_ylabel("Oxygen flow (m³/s)")
    axes[1].set_xlabel("Time (s)")
    for index, (ax, values) in enumerate(zip(axes, (raw, np.r_[np.diff(raw) / np.diff(t), 0]))):
        local = values[(t >= limits[0]) & (t <= limits[1])]
        low, high = local.min(), local.max()
        ax.set(xlim=limits, ylim=(low - 0.1 * (high - low), high + 0.12 * (high - low)))
        ax.grid(alpha=0.7)
        ax.legend(loc="upper left", ncols=2 if index == 0 else 1)
    save(fig, destination)


def gas_window(heat, signal, process, center, destination):
    j = {"CO2": 1, "CO": 2}[signal]
    fig, ax = plt.subplots(figsize=(9, 3), layout="constrained")
    shown = np.abs(process.time - center) <= 10
    ax.plot(process.time[shown], process.raw[j][shown], ".-", color="#657789", label="Measured")
    ax.plot(process.time[shown], process.knots[j][shown], color=COLOR, label="Reconstructed")
    ax.set(title=f"{heat}   {signal} repair near {center:g} s", xlabel="Time (s)", ylabel="Flow (m³/s)")
    ax.grid(alpha=0.7)
    ax.legend()
    save(fig, destination)

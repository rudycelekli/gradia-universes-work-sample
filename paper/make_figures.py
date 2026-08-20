"""Generate manuscript figures from committed machine-readable evidence."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
PAPER = Path(__file__).resolve().parent
FIGURES = PAPER / "figures"
INK = "#191714"
WARM = "#5c554e"
ORANGE = "#d95520"
SAND = "#f3eee8"
BLUE = "#315f7d"
LINE = "#d8d0c8"


def _save(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{name}.png", dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def evolution_witness() -> None:
    labels = [
        "Frozen\nevent",
        "Declared\nboundary",
        "Root-owned\napplication",
        "Roots + visible\nprojection",
        "Restore +\nchain lineage",
        "Judgment +\nepisode receipt",
    ]
    fig, ax = plt.subplots(figsize=(12.5, 2.7))
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, 2.7)
    ax.axis("off")
    for index, label in enumerate(labels):
        x = 0.22 + index * 2.05
        box = FancyBboxPatch(
            (x, 0.76),
            1.72,
            1.12,
            boxstyle="round,pad=0.06,rounding_size=0.08",
            linewidth=1.2,
            edgecolor=ORANGE if index in {0, 5} else LINE,
            facecolor=SAND if index % 2 == 0 else "white",
        )
        ax.add_patch(box)
        ax.text(
            x + 0.86,
            1.32,
            label,
            ha="center",
            va="center",
            color=INK,
            fontsize=10.5,
            weight="semibold",
        )
        if index < len(labels) - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x + 1.75, 1.32),
                    (x + 2.01, 1.32),
                    arrowstyle="-|>",
                    mutation_scale=13,
                    linewidth=1.15,
                    color=BLUE,
                )
            )
    ax.text(
        6.25,
        0.30,
        "One verifier tests declaration, application, disclosure, ordering and restore history together.",
        ha="center",
        va="center",
        color=WARM,
        fontsize=10.5,
    )
    _save(fig, "evolution-witness")


def harness_sensitivity() -> None:
    panel = json.loads((ROOT / "results/reference/panel.json").read_text(encoding="utf-8"))
    rows = panel["by_agent"]
    labels = [row["agent_policy"].replace("_", " ") for row in rows]
    rates = [float(row["pass_rate"]) * 100 for row in rows]
    lows = [(float(row["pass_rate"]) - float(row["wilson_95"][0])) * 100 for row in rows]
    highs = [(float(row["wilson_95"][1]) - float(row["pass_rate"])) * 100 for row in rows]

    fig, ax = plt.subplots(figsize=(9.4, 4.4))
    bars = ax.bar(labels, rates, color=[ORANGE, BLUE, WARM], width=0.58, zorder=3)
    ax.errorbar(labels, rates, yerr=[lows, highs], fmt="none", ecolor=INK, capsize=5, linewidth=1.25, zorder=4)
    ax.set_ylim(0, 112)
    ax.set_ylabel("Perfect pass rate (%)", color=INK)
    ax.set_title("Constructed controls exercise distinct judge paths", loc="left", color=INK, weight="bold", pad=12)
    ax.text(
        0,
        1.015,
        "Five synthetic episodes per scripted policy; Wilson 95% intervals",
        transform=ax.transAxes,
        color=WARM,
        fontsize=10,
    )
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, rate + 3.2, f"{rate:.0f}%", ha="center", color=INK, weight="bold")
    ax.grid(axis="y", color=LINE, linewidth=0.7, alpha=0.8, zorder=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(LINE)
    ax.tick_params(axis="y", length=0, colors=WARM)
    ax.tick_params(axis="x", length=0, colors=INK, pad=8)
    ax.text(
        0,
        -0.24,
        "Harness-sensitivity check only - not a language-model capability or difficulty estimate.",
        transform=ax.transAxes,
        color=ORANGE,
        fontsize=9.5,
        weight="semibold",
    )
    fig.subplots_adjust(left=0.09, right=0.98, top=0.82, bottom=0.27)
    _save(fig, "harness-sensitivity")


if __name__ == "__main__":
    evolution_witness()
    harness_sensitivity()

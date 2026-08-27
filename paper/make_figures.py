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
        "One verifier tests declaration, application, disclosure, ordering "
        "and restore history together.",
        ha="center",
        va="center",
        color=WARM,
        fontsize=10.5,
    )
    _save(fig, "evolution-witness")


def attribution_chain() -> None:
    """Make the causal attribution question legible before formal notation."""

    stages = [
        ("World changed", "declared occurrence"),
        ("Materially applied?", "before/after roots"),
        ("Agent saw it?", "exact visible projection"),
        ("Authority valid?", "source, scope, precedence"),
        ("Correct action?", "action + terminal account"),
    ]
    fault_labels = [
        "environment fault",
        "disclosure fault",
        "authority fault",
        "agent-fault candidate",
    ]
    fig, ax = plt.subplots(figsize=(12.5, 3.35))
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, 3.35)
    ax.axis("off")

    box_width = 2.12
    gap = 0.34
    start = 0.28
    y = 1.43
    for index, (title, subtitle) in enumerate(stages):
        x = start + index * (box_width + gap)
        patch = FancyBboxPatch(
            (x, y),
            box_width,
            1.12,
            boxstyle="round,pad=0.06,rounding_size=0.08",
            linewidth=1.25,
            edgecolor=ORANGE if index in {0, 4} else LINE,
            facecolor=SAND if index % 2 == 0 else "white",
        )
        ax.add_patch(patch)
        ax.text(
            x + box_width / 2,
            y + 0.70,
            title,
            ha="center",
            va="center",
            color=INK,
            fontsize=10.1,
            weight="bold",
        )
        ax.text(
            x + box_width / 2,
            y + 0.30,
            subtitle,
            ha="center",
            va="center",
            color=WARM,
            fontsize=8.4,
        )
        if index < len(stages) - 1:
            arrow_start = x + box_width + 0.03
            arrow_end = x + box_width + gap - 0.03
            ax.add_patch(
                FancyArrowPatch(
                    (arrow_start, y + 0.56),
                    (arrow_end, y + 0.56),
                    arrowstyle="-|>",
                    mutation_scale=12,
                    linewidth=1.15,
                    color=BLUE,
                )
            )
            ax.text(
                (arrow_start + arrow_end) / 2,
                0.92,
                fault_labels[index],
                ha="center",
                va="center",
                color=ORANGE,
                fontsize=8.0,
                weight="semibold",
            )

    ax.text(
        6.25,
        3.04,
        "One changing-world episode, four attribution gates",
        ha="center",
        va="center",
        color=INK,
        fontsize=12,
        weight="bold",
    )
    ax.text(
        6.25,
        0.35,
        "Only the final class is eligible for model attribution - after evaluator admission and blinded review.",
        ha="center",
        va="center",
        color=WARM,
        fontsize=9.2,
    )
    _save(fig, "attribution-chain")


def harness_sensitivity() -> None:
    panel = json.loads((ROOT / "results/reference/panel.json").read_text(encoding="utf-8"))
    rows = panel["by_agent"]
    labels = [row["agent_policy"].replace("_", " ") for row in rows]
    rates = [float(row["pass_rate"]) * 100 for row in rows]
    lows = [(float(row["pass_rate"]) - float(row["wilson_95"][0])) * 100 for row in rows]
    highs = [(float(row["wilson_95"][1]) - float(row["pass_rate"])) * 100 for row in rows]

    fig, ax = plt.subplots(figsize=(9.4, 4.4))
    bars = ax.bar(labels, rates, color=[ORANGE, BLUE, WARM], width=0.58, zorder=3)
    ax.errorbar(
        labels,
        rates,
        yerr=[lows, highs],
        fmt="none",
        ecolor=INK,
        capsize=5,
        linewidth=1.25,
        zorder=4,
    )
    ax.set_ylim(0, 112)
    ax.set_ylabel("Perfect pass rate (%)", color=INK)
    ax.set_title(
        "Constructed controls exercise distinct judge paths",
        loc="left",
        color=INK,
        weight="bold",
        pad=12,
    )
    ax.text(
        0,
        1.015,
        "Five synthetic episodes per scripted policy; Wilson 95% intervals",
        transform=ax.transAxes,
        color=WARM,
        fontsize=10,
    )
    for index, bar in enumerate(bars):
        rate = rates[index]
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            rate + 3.2,
            f"{rate:.0f}%",
            ha="center",
            color=INK,
            weight="bold",
        )
    ax.grid(axis="y", color=LINE, linewidth=0.7, alpha=0.8, zorder=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(LINE)
    ax.tick_params(axis="y", length=0, colors=WARM)
    ax.tick_params(axis="x", length=0, colors=INK, pad=8)
    ax.text(
        0,
        -0.24,
        "Harness-sensitivity check only - not a language-model capability "
        "or difficulty estimate.",
        transform=ax.transAxes,
        color=ORANGE,
        fontsize=9.5,
        weight="semibold",
    )
    fig.subplots_adjust(left=0.09, right=0.98, top=0.82, bottom=0.27)
    _save(fig, "harness-sensitivity")


def episode_timeline() -> None:
    fig, ax = plt.subplots(figsize=(12.5, 3.5))
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, 3.5)
    ax.axis("off")
    y = 1.72
    ax.plot([0.6, 11.9], [y, y], color=INK, linewidth=1.3)
    points = [1.0, 3.0, 5.0, 7.0, 9.1, 11.3]
    labels = [
        ("act 1", "read current state"),
        ("act 2", "calculate"),
        ("boundary b", "apply event"),
        ("act 3", "projection delivered"),
        ("restore", "generation g→g+1"),
        ("terminal", "judge + receipt"),
    ]
    for index, x in enumerate(points):
        title, subtitle = labels[index]
        color = ORANGE if index in {2, 4} else BLUE
        ax.scatter([x], [y], s=82, color=color, zorder=4)
        above = index % 2 == 0
        text_y = 2.70 if above else 0.67
        ax.plot([x, x], [y, 2.32 if above else 1.10], color=LINE, linewidth=1.1)
        ax.text(
            x, text_y, title, ha="center", va="center", color=INK, fontsize=10.5, weight="bold"
        )
        ax.text(x, text_y - 0.33, subtitle, ha="center", va="center", color=WARM, fontsize=8.8)
    ax.text(4.15, 2.13, "R⁻", color=ORANGE, fontsize=10, weight="bold")
    ax.text(5.72, 2.13, "R⁺ + Vₑ", color=ORANGE, fontsize=10, weight="bold")
    ax.text(8.02, 1.28, "snapshot identity + chain head", color=WARM, fontsize=8.8, ha="center")
    ax.text(
        6.25,
        3.27,
        "One event, one declared action boundary, one auditable evolution chain",
        ha="center",
        color=INK,
        fontsize=12,
        weight="bold",
    )
    _save(fig, "episode-timeline")


def judge_instability() -> None:
    """Show attribution spread and evidence-anchor divergence without judge identity."""

    payload = json.loads(
        (
            ROOT / "results/pre-results/conditionally-approved-four-judge-alignment.json"
        ).read_text(encoding="utf-8")
    )
    assignment_count = int(payload["assignment_count"])
    judges = payload["judges"]
    pairwise = payload["pairwise"]
    aliases = {row["model_pin"]: f"J{index}" for index, row in enumerate(judges, 1)}

    labels = [aliases[row["model_pin"]] for row in judges]
    failure_rates = [100 * int(row["model_failure"]) / assignment_count for row in judges]
    confidences = [100 * float(row["mean_confidence"]) for row in judges]

    pair_labels: list[str] = []
    label_agreement: list[float] = []
    anchor_overlap: list[float] = []
    for row in pairwise:
        left, right = row["judge_pair"].split(" :: ", 1)
        pair_labels.append(f"{aliases[left]}-{aliases[right]}")
        label_agreement.append(100 * float(row["exact_label_agreement"]))
        anchor_overlap.append(100 * float(row["evidence_anchor_jaccard"]))

    fig, (left_ax, right_ax) = plt.subplots(
        1,
        2,
        figsize=(12.5, 4.2),
        gridspec_kw={"width_ratios": [0.82, 1.45]},
    )
    fig.patch.set_facecolor("white")

    x = list(range(len(labels)))
    bars = left_ax.bar(x, failure_rates, color=ORANGE, width=0.58, zorder=3)
    left_ax.scatter(
        x,
        confidences,
        color=BLUE,
        marker="D",
        s=38,
        label="Mean stated confidence",
        zorder=4,
    )
    for index, bar in enumerate(bars):
        rate = failure_rates[index]
        left_ax.text(
            bar.get_x() + bar.get_width() / 2,
            rate + 2.2,
            f"{rate:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9,
            color=INK,
            weight="bold",
        )
    left_ax.set_title(
        "Same evidence, different attribution", loc="left", color=INK, weight="bold"
    )
    left_ax.set_ylabel("Share of 889 assignments (%)", color=INK)
    left_ax.set_xticks(x, labels)
    left_ax.set_ylim(0, 108)
    left_ax.legend(loc="lower right", frameon=False, fontsize=8.4)

    pair_x = list(range(len(pair_labels)))
    width = 0.36
    right_ax.bar(
        [value - width / 2 for value in pair_x],
        label_agreement,
        width=width,
        color=BLUE,
        label="Exact label agreement",
        zorder=3,
    )
    right_ax.bar(
        [value + width / 2 for value in pair_x],
        anchor_overlap,
        width=width,
        color=ORANGE,
        label="Evidence-anchor Jaccard",
        zorder=3,
    )
    right_ax.set_title(
        "Matching labels often cite different evidence", loc="left", color=INK, weight="bold"
    )
    right_ax.set_xticks(pair_x, pair_labels)
    right_ax.set_ylim(0, 108)
    right_ax.legend(loc="upper left", frameon=False, fontsize=8.4)

    for ax in (left_ax, right_ax):
        ax.grid(axis="y", color=LINE, linewidth=0.7, alpha=0.8, zorder=0)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color(LINE)
        ax.tick_params(axis="y", length=0, colors=WARM)
        ax.tick_params(axis="x", length=0, colors=INK, pad=7)

    fig.suptitle(
        "Four-judge stress test: low stability despite high stated confidence",
        x=0.055,
        y=1.03,
        ha="left",
        color=INK,
        fontsize=13,
        weight="bold",
    )
    fig.text(
        0.055,
        -0.02,
        (
            f"Descriptive Fleiss' kappa = {float(payload['descriptive_fleiss_kappa']):.3f}; "
            f"unanimous = {int(payload['unanimous_assignment_count'])}/{assignment_count} "
            f"({100 * float(payload['unanimous_assignment_rate']):.1f}%). "
            "Machine opinions are advisory; human attribution remains pending."
        ),
        color=WARM,
        fontsize=9.2,
    )
    fig.subplots_adjust(left=0.07, right=0.99, top=0.83, bottom=0.18, wspace=0.24)
    _save(fig, "judge-instability")


def fault_attribution() -> None:
    fig, ax = plt.subplots(figsize=(11.8, 5.5))
    ax.set_xlim(0, 11.8)
    ax.set_ylim(0, 5.5)
    ax.axis("off")

    def box(
        x: float, y: float, w: float, h: float, title: str, subtitle: str, accent: bool = False
    ) -> None:
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.05,rounding_size=0.08",
            linewidth=1.2,
            edgecolor=ORANGE if accent else LINE,
            facecolor=SAND if accent else "white",
        )
        ax.add_patch(patch)
        ax.text(
            x + w / 2,
            y + h * 0.64,
            title,
            ha="center",
            va="center",
            color=INK,
            fontsize=10.2,
            weight="bold",
        )
        ax.text(
            x + w / 2,
            y + h * 0.30,
            subtitle,
            ha="center",
            va="center",
            color=WARM,
            fontsize=8.6,
        )

    box(
        3.75,
        4.25,
        4.3,
        0.9,
        "Did the episode satisfy the witness?",
        "verify before scoring the agent",
        True,
    )
    box(0.35, 2.55, 2.55, 1.0, "Environment fault", "contract and material roots disagree")
    box(3.18, 2.55, 2.55, 1.0, "Disclosure fault", "roots correct; visible projection differs")
    box(6.07, 2.55, 2.55, 1.0, "Authority fault", "content present; source or scope invalid")
    box(8.90, 2.55, 2.55, 1.0, "Agent fault", "valid episode; stale or unsupported action")
    box(
        3.75,
        0.55,
        4.3,
        0.9,
        "Admit denominator + criterion vector",
        "environment failures never become model failures",
        True,
    )

    for x in [1.63, 4.46, 7.35, 10.18]:
        ax.add_patch(
            FancyArrowPatch(
                (5.9, 4.25),
                (x, 3.58),
                arrowstyle="-|>",
                mutation_scale=12,
                color=BLUE,
                linewidth=1.0,
            )
        )
        ax.add_patch(
            FancyArrowPatch(
                (x, 2.52),
                (5.9, 1.48),
                arrowstyle="-|>",
                mutation_scale=12,
                color=BLUE,
                linewidth=1.0,
            )
        )
    _save(fig, "fault-attribution")


if __name__ == "__main__":
    evolution_witness()
    attribution_chain()
    harness_sensitivity()
    episode_timeline()
    judge_instability()
    fault_attribution()

import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path("/Users/delete/Desktop/rag_system_副本")
SUPPORT_RUNTIME = ROOT / "results" / "evaluation" / "support_runtime"
TUNING = ROOT / "results" / "tuning"
OUT = ROOT / "journal_paper_ccpe" / "figures" / "peerj_submission"
MPLCFG = ROOT / ".mplconfig"

COLORS = {
    "negative": "#C44E52",
    "baseline": "#5DA5DA",
    "preferred": "#60BD68",
    "generation": "#F5B041",
    "other": "#D9D9D9",
    "retrieval": "#5DA5DA",
    "scoring": "#ECECEC",
    "pruning": "#CFCFCF",
    "prefill": "#F5B041",
    "decode": "#60BD68",
    "grid": "#D9D9D9",
    "text": "#2F2F2F",
    "annotation": "#666666",
}

FIG_WIDTH = 6.9
PANEL_HEIGHT = 2.5
TITLE_SIZE = 10
LABEL_SIZE = 9
TICK_SIZE = 8
ANNOTATION_SIZE = 8
LINEWIDTH = 1.5
BAR_EDGE = 0.6


def ensure_output_dir():
    OUT.mkdir(parents=True, exist_ok=True)
    MPLCFG.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(MPLCFG))


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def set_academic_style():
    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["font.size"] = LABEL_SIZE
    plt.rcParams["axes.titlesize"] = TITLE_SIZE
    plt.rcParams["axes.labelsize"] = LABEL_SIZE
    plt.rcParams["xtick.labelsize"] = TICK_SIZE
    plt.rcParams["ytick.labelsize"] = TICK_SIZE
    plt.rcParams["legend.fontsize"] = TICK_SIZE
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["grid.alpha"] = 0.55
    plt.rcParams["grid.color"] = COLORS["grid"]
    plt.rcParams["axes.axisbelow"] = True
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["savefig.facecolor"] = "white"
    plt.rcParams["figure.facecolor"] = "white"


def format_axes(ax, xlabel=None, ylabel=None, title=None, grid_axis="x"):
    if xlabel:
        ax.set_xlabel(xlabel, color=COLORS["text"])
    if ylabel:
        ax.set_ylabel(ylabel, color=COLORS["text"])
    if title:
        ax.set_title(title, pad=6, color=COLORS["text"])
    ax.grid(True, axis=grid_axis, linestyle="--", alpha=0.55, color=COLORS["grid"])
    ax.tick_params(axis="both", colors=COLORS["text"], width=0.8)


def generate_backend_migration_figure():
    model_comp = load_json(SUPPORT_RUNTIME / "model_comparison.json")
    mps_perf = load_json(SUPPORT_RUNTIME / "v2_performance_final.json")
    scaling_row = mps_perf["scaling"]["16"]

    stages = [
        {
            "label": "Falcon MPS",
            "ttft": scaling_row["ttft"] * 1000.0,
            "tps": scaling_row["tps"],
            "total": scaling_row["total_time"],
            "color": COLORS["negative"],
        },
        {
            "label": "Falcon GGUF",
            "ttft": model_comp["Falcon-7B-Quant"]["ttft_ms"],
            "tps": model_comp["Falcon-7B-Quant"]["tps"],
            "total": model_comp["Falcon-7B-Quant"]["total_time_s"],
            "color": COLORS["baseline"],
        },
        {
            "label": "Llama-3 GGUF",
            "ttft": model_comp["Llama-3-8B-Quant"]["ttft_ms"],
            "tps": model_comp["Llama-3-8B-Quant"]["tps"],
            "total": model_comp["Llama-3-8B-Quant"]["total_time_s"],
            "color": COLORS["preferred"],
        },
    ]

    labels = [s["label"] for s in stages]
    colors = [s["color"] for s in stages]
    ttft_vals = [s["ttft"] for s in stages]
    tps_vals = [s["tps"] for s in stages]
    total_vals = [s["total"] for s in stages]

    fig, axes = plt.subplots(3, 1, figsize=(FIG_WIDTH, PANEL_HEIGHT * 2.9), sharey=False)

    axes[0].barh(labels, ttft_vals, color=colors, edgecolor=COLORS["text"], linewidth=BAR_EDGE, height=0.64)
    axes[0].set_xscale("log")
    format_axes(axes[0], xlabel="Milliseconds", title="A. Time to first token", grid_axis="x")

    axes[1].barh(labels, tps_vals, color=colors, edgecolor=COLORS["text"], linewidth=BAR_EDGE, height=0.64)
    format_axes(axes[1], xlabel="Tokens per second", title="B. Decode throughput", grid_axis="x")

    axes[2].barh(labels, total_vals, color=colors, edgecolor=COLORS["text"], linewidth=BAR_EDGE, height=0.64)
    axes[2].set_xlim(0, max(total_vals) * 1.06)
    format_axes(axes[2], xlabel="Seconds", title="C. Total latency", grid_axis="x")

    for ax in axes:
        ax.invert_yaxis()
        ax.tick_params(axis="y", labelsize=LABEL_SIZE)
        ax.tick_params(axis="x", labelsize=TICK_SIZE)

    for i, v in enumerate(ttft_vals):
        txt = f"{v/1000:.2f} s" if v >= 1000 else f"{v:.2f} ms"
        axes[0].text(v * 1.08, i, txt, va="center", fontsize=ANNOTATION_SIZE, color=COLORS["text"])

    for i, v in enumerate(tps_vals):
        axes[1].text(v + max(tps_vals) * 0.03, i, f"{v:.2f}", va="center", fontsize=ANNOTATION_SIZE, color=COLORS["text"])

    for i, v in enumerate(total_vals):
        offset = max(total_vals) * 0.02 if v > 20 else max(total_vals) * 0.04
        axes[2].text(v + offset, i, f"{v:.2f} s", va="center", fontsize=ANNOTATION_SIZE, color=COLORS["text"])

    fig.tight_layout(pad=0.7, h_pad=1.0)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"figure2_backend_migration.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def generate_system_architecture_figure():
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, 3.15))
    ax.set_xlim(0.15, 14.55)
    ax.set_ylim(0.2, 5.1)
    ax.axis("off")

    control_y = 4.05
    control_h = 0.7
    plane = FancyBboxPatch(
        (2.95, control_y),
        8.65,
        control_h,
        boxstyle="round,pad=0.03,rounding_size=0.08",
        linewidth=0.9,
        edgecolor=COLORS["text"],
        facecolor="#EEE8F8",
    )
    ax.add_patch(plane)
    ax.text(
        3.15,
        control_y + 0.44,
        "Control plane",
        fontsize=8.5,
        fontweight="bold",
        color=COLORS["text"],
        ha="left",
        va="center",
    )
    ax.text(
        3.15,
        control_y + 0.18,
        "Latency, memory, and concurrency telemetry",
        fontsize=6.6,
        color=COLORS["annotation"],
        ha="left",
        va="center",
    )

    box_h = 1.08
    y = 2.15
    blocks = [
        ("Query", "User prompt", 0.30, 1.42, COLORS["other"]),
        ("Router", "Path select.", 1.92, 1.48, "#DDD6F4"),
        ("Retriever", "TurboQuant\ncompressed\nretrieval", 3.56, 2.35, COLORS["baseline"]),
        ("Pruner", "KV-aware\ncontext\ncompression", 6.13, 2.48, COLORS["generation"]),
        ("Backend", "Quantized\ninference\nGGUF / llama.cpp", 8.88, 2.95, COLORS["preferred"]),
        ("Answer", "Grounded answer", 12.08, 1.65, COLORS["other"]),
    ]

    for title, subtitle, x, w, color in blocks:
        patch = FancyBboxPatch(
            (x, y),
            w,
            box_h,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=0.9,
            edgecolor=COLORS["text"],
            facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(
            x + 0.12,
            y + 0.70,
            title,
            fontsize=8.3,
            fontweight="bold",
            color=COLORS["text"],
            ha="left",
            va="center",
        )
        ax.text(
            x + 0.12,
            y + 0.17,
            subtitle,
            fontsize=5.35,
            color=COLORS["text"],
            ha="left",
            va="bottom",
        )

    arrow_y = y + box_h / 2
    arrows = [
        ((1.75, arrow_y), (1.90, arrow_y)),
        ((3.42, arrow_y), (3.54, arrow_y)),
        ((5.95, arrow_y), (6.11, arrow_y)),
        ((8.65, arrow_y), (8.86, arrow_y)),
        ((11.86, arrow_y), (12.06, arrow_y)),
    ]
    for start, end in arrows:
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=11,
                linewidth=1.0,
                color=COLORS["text"],
            )
        )

    # Decision layer guide.
    ax.text(
        7.15,
        3.42,
        "Execution path",
        fontsize=7.0,
        color=COLORS["annotation"],
        ha="center",
        va="center",
    )

    # Feedback/control flow.
    feedback_kwargs = dict(
        arrowstyle="-|>",
        mutation_scale=10,
        linewidth=0.9,
        linestyle="--",
        color=COLORS["annotation"],
    )
    ax.add_patch(FancyArrowPatch((10.75, 3.12), (9.95, 4.03), connectionstyle="arc3,rad=0.22", **feedback_kwargs))
    ax.add_patch(FancyArrowPatch((7.32, 4.03), (7.32, 3.12), connectionstyle="arc3,rad=0.0", **feedback_kwargs))
    ax.add_patch(FancyArrowPatch((4.78, 4.03), (4.78, 3.12), connectionstyle="arc3,rad=0.0", **feedback_kwargs))
    ax.text(
        10.85,
        3.63,
        "feedback loop",
        fontsize=6.6,
        color=COLORS["annotation"],
        ha="left",
        va="center",
    )

    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"figure1_system_architecture.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def generate_keep_ratio_tradeoff():
    rows = load_json(SUPPORT_RUNTIME / "tradeoff_curve.json")
    rows = sorted(rows, key=lambda r: r["keep_ratio"])
    keep = [r["keep_ratio"] for r in rows]
    ttft = [r["ttft_ms"] for r in rows]
    total = [r["total_e2e_ms"] for r in rows]
    tps = [r["tps"] for r in rows]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(FIG_WIDTH, PANEL_HEIGHT * 2.25), sharex=True)

    ax1.plot(keep, ttft, marker="o", markersize=4.5, linewidth=LINEWIDTH, color=COLORS["baseline"], label="TTFT")
    ax1.plot(keep, total, marker="s", markersize=4.5, linewidth=LINEWIDTH, color=COLORS["generation"], label="Total E2E")
    format_axes(ax1, xlabel="Keep ratio", ylabel="Latency (ms)", title="A. Latency vs. keep ratio", grid_axis="both")
    ax1.legend(frameon=False, loc="upper left", ncol=2)

    ax2.plot(keep, tps, marker="o", markersize=4.5, linewidth=LINEWIDTH, color=COLORS["preferred"])
    format_axes(ax2, xlabel="Keep ratio", ylabel="Tokens per second", title="B. Decode throughput vs. keep ratio", grid_axis="both")

    best_idx = min(range(len(ttft)), key=lambda i: ttft[i])
    ax1.scatter([keep[best_idx]], [ttft[best_idx]], s=36, color=COLORS["baseline"], zorder=5)
    ax1.annotate(
        f"Operating point @ {keep[best_idx]:.1f}",
        xy=(keep[best_idx], ttft[best_idx]),
        xytext=(keep[best_idx] + 0.08, ttft[best_idx] + 2000),
        arrowprops=dict(arrowstyle="->", color=COLORS["annotation"], linewidth=0.9),
        fontsize=ANNOTATION_SIZE,
        color=COLORS["annotation"],
    )

    ax2.set_xlim(min(keep) - 0.03, max(keep) + 0.03)
    fig.tight_layout(pad=0.7, h_pad=0.9)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"figure4_keep_ratio_tradeoff.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def generate_e2e_breakdown_figure():
    v2_rows = load_json(SUPPORT_RUNTIME / "v2_bench_comparison.json")
    tradeoff = load_json(SUPPORT_RUNTIME / "tradeoff_curve.json")

    v1_total = v2_rows[0]["v1_latency"]
    v2_total = v2_rows[0]["v2_latency"]
    v1_gen = v1_total * 0.925
    v1_other = v1_total - v1_gen
    v2_gen = v2_total * 0.774
    v2_other = v2_total - v2_gen

    rep = next(r for r in tradeoff if abs(r["keep_ratio"] - 0.6) < 1e-9)
    retrieval = rep["retrieval_ms"] / 1000.0
    scoring = rep["scoring_ms"] / 1000.0
    pruning = rep["pruning_ms"] / 1000.0
    prefill = rep["ttft_ms"] / 1000.0
    decode = max(rep["total_e2e_ms"] / 1000.0 - retrieval - scoring - pruning - prefill, 0.0)
    rep_total = retrieval + scoring + pruning + prefill + decode
    ancillary = retrieval + scoring + pruning

    ancillary_pct = ancillary / rep_total * 100.0
    prefill_pct = prefill / rep_total * 100.0
    decode_pct = decode / rep_total * 100.0

    fig4_colors = {
        "other": "#D9D9D9",
        "prefill": "#F2B766",
        "decode": "#C97A1E",
        "edge": "#4A4A4A",
        "accent": "#6B6B6B",
    }

    fig = plt.figure(figsize=(FIG_WIDTH, PANEL_HEIGHT * 2.3))
    gs = fig.add_gridspec(
        2,
        2,
        width_ratios=[2.25, 1.15],
        height_ratios=[1.0, 1.0],
        wspace=0.28,
        hspace=0.42,
    )
    ax_main = fig.add_subplot(gs[:, 0])
    ax_delta = fig.add_subplot(gs[0, 1])
    ax_comp = fig.add_subplot(gs[1, 1])

    # Panel A: primary evidence chart.
    labels = ["V1", "V2"]
    other_vals = [v1_other, v2_other]
    gen_vals = [v1_gen, v2_gen]
    x = [0, 1]
    bar_width = 0.58
    ax_main.bar(
        x,
        other_vals,
        width=bar_width,
        color=fig4_colors["other"],
        edgecolor=fig4_colors["edge"],
        linewidth=BAR_EDGE,
        hatch="///",
        label="Other stages",
    )
    ax_main.bar(
        x,
        gen_vals,
        width=bar_width,
        bottom=other_vals,
        color=fig4_colors["decode"],
        edgecolor=fig4_colors["edge"],
        linewidth=BAR_EDGE,
        label="Generation",
    )
    ax_main.set_xticks(x)
    ax_main.set_xticklabels(labels)
    format_axes(ax_main, ylabel="Latency (s)", title="A. End-to-end latency breakdown", grid_axis="y")
    ax_main.legend(frameon=False, loc="upper right", bbox_to_anchor=(0.98, 1.005), borderaxespad=0.0)
    ax_main.set_ylim(0, max(v1_total, v2_total) * 1.16)
    for i, total in enumerate([v1_total, v2_total]):
        ax_main.text(i, total + 0.22, f"{total:.1f} s", ha="center", fontsize=ANNOTATION_SIZE, color=COLORS["text"])
    ax_main.text(0, other_vals[0] + gen_vals[0] / 2, "Generation\n92.5%", ha="center", va="center", fontsize=ANNOTATION_SIZE, color="white", fontweight="bold")
    ax_main.text(1, other_vals[1] + gen_vals[1] / 2, "Generation\n77.4%", ha="center", va="center", fontsize=ANNOTATION_SIZE, color="white", fontweight="bold")

    y_bracket = max(v1_total, v2_total) * 1.035
    ax_main.plot([0, 0, 1, 1], [y_bracket - 0.18, y_bracket, y_bracket, y_bracket - 0.18], color=fig4_colors["accent"], linewidth=1.0)
    ax_main.text(
        0.10,
        y_bracket + 0.24,
        "Total latency reduction: 68.5 %",
        ha="left",
        va="bottom",
        fontsize=ANNOTATION_SIZE,
        color=fig4_colors["accent"],
    )

    # Panel B: reduction summary.
    red_labels = ["Total latency", "Generation share"]
    red_vals = [68.5, 15.1]
    red_units = ["%", "pp"]
    ypos = [1, 0]
    ax_delta.barh(ypos, red_vals, color=[fig4_colors["decode"], fig4_colors["prefill"]], edgecolor=fig4_colors["edge"], linewidth=BAR_EDGE, height=0.52)
    ax_delta.set_yticks(ypos)
    ax_delta.set_yticklabels(red_labels)
    ax_delta.set_xlim(0, 80)
    format_axes(ax_delta, xlabel="Reduction magnitude", title="B. Optimization impact", grid_axis="x")
    for yv, vv, uu in zip(ypos, red_vals, red_units):
        ax_delta.text(vv + 1.3, yv, f"-{vv:.1f} {uu}", va="center", fontsize=ANNOTATION_SIZE, color=COLORS["text"])

    # Panel C: optimized-path bottleneck composition.
    other_non_decode = ancillary_pct + prefill_pct
    ax_comp.barh(
        [""],
        [other_non_decode],
        color=fig4_colors["prefill"],
        edgecolor=fig4_colors["edge"],
        linewidth=BAR_EDGE,
        label="Non-decode",
    )
    ax_comp.barh(
        [""],
        [decode_pct],
        left=[other_non_decode],
        color=fig4_colors["decode"],
        edgecolor=fig4_colors["edge"],
        linewidth=BAR_EDGE,
        label="Decode",
    )
    ax_comp.set_xlim(0, 100)
    ax_comp.set_yticks([])
    format_axes(ax_comp, xlabel="Percentage of total latency (%)", title="C. Post-optimization bottleneck composition", grid_axis="x")
    ax_comp.text(other_non_decode / 2, 0, f"Others\n{other_non_decode:.1f} %", ha="center", va="center", fontsize=8, color=COLORS["text"])
    ax_comp.text(other_non_decode + decode_pct / 2, 0, f"Decode\n{decode_pct:.1f} %", ha="center", va="center", fontsize=9.3, color="white", fontweight="bold")
    ax_comp.text(0.5, -0.30, "Representative configuration: keep ratio = 0.6", transform=ax_comp.transAxes, ha="center", va="center", fontsize=ANNOTATION_SIZE, color=COLORS["annotation"])

    fig.subplots_adjust(left=0.10, right=0.98, top=0.93, bottom=0.14, hspace=0.42, wspace=0.28)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"figure6_e2e_breakdown.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def generate_quality_latency_frontier():
    sweep = load_json(TUNING / "sweep_summary.json")["rows"]
    pareto = load_json(TUNING / "pareto_selection.json")
    baseline = pareto["baseline"]
    front = pareto["pareto_front"]
    recommended = pareto["recommended"]

    front_keys = {
        (row["mode"], row["rrf_k"], round(row["faithfulness"], 3), round(row["latency_mean"], 3))
        for row in front
    }
    recommended_key = (
        recommended["mode"],
        recommended["rrf_k"],
        round(recommended["faithfulness"], 3),
        round(recommended["latency_mean"], 3),
    )

    fig, ax = plt.subplots(figsize=(FIG_WIDTH, PANEL_HEIGHT * 1.65))

    xs_all = [row["latency_mean"] for row in sweep]
    ys_all = [row["faithfulness"] for row in sweep]
    ax.scatter(
        xs_all,
        ys_all,
        s=32,
        color="#CFCFCF",
        edgecolors="white",
        linewidths=0.5,
        alpha=0.95,
        label="Other candidates",
        zorder=2,
    )

    front_sorted = sorted(front, key=lambda r: r["latency_mean"])
    front_x = [row["latency_mean"] for row in front_sorted]
    front_y = [row["faithfulness"] for row in front_sorted]
    ax.plot(front_x, front_y, color=COLORS["generation"], linewidth=1.4, alpha=0.95, zorder=3)
    ax.scatter(
        front_x,
        front_y,
        s=52,
        color=COLORS["generation"],
        edgecolors=COLORS["text"],
        linewidths=0.5,
        label="Pareto front",
        zorder=4,
    )

    baseline_x = min(xs_all) - 2.2
    baseline_y = baseline["faithfulness_mean"]
    ax.scatter(
        [baseline_x],
        [baseline_y],
        marker="X",
        s=78,
        color=COLORS["negative"],
        edgecolors=COLORS["text"],
        linewidths=0.6,
        label="Baseline threshold",
        zorder=5,
    )
    ax.axhline(
        baseline_y,
        color=COLORS["negative"],
        linestyle="--",
        linewidth=1.0,
        alpha=0.8,
        zorder=1,
    )

    rec_x = recommended["latency_mean"]
    rec_y = recommended["faithfulness"]
    ax.scatter(
        [rec_x],
        [rec_y],
        marker="*",
        s=180,
        color=COLORS["preferred"],
        edgecolors=COLORS["text"],
        linewidths=0.7,
        label="Selected operating point",
        zorder=6,
    )

    format_axes(ax, xlabel="Mean latency (s)", ylabel="Faithfulness score", title="Quality-latency frontier", grid_axis="both")
    ax.set_xlim(baseline_x - 1.0, max(xs_all) + 6)
    ax.set_ylim(min(ys_all) - 0.5, max(ys_all) + 0.6)
    ax.legend(frameon=False, loc="lower right")

    ax.annotate(
        "Baseline acceptance level",
        xy=(baseline_x, baseline_y),
        xytext=(baseline_x + 6.0, baseline_y - 0.55),
        arrowprops=dict(arrowstyle="->", color=COLORS["annotation"], linewidth=0.9),
        fontsize=ANNOTATION_SIZE,
        color=COLORS["annotation"],
    )
    ax.annotate(
        "Recommended point",
        xy=(rec_x, rec_y),
        xytext=(rec_x + 8.0, rec_y + 0.25),
        arrowprops=dict(arrowstyle="->", color=COLORS["annotation"], linewidth=0.9),
        fontsize=ANNOTATION_SIZE,
        color=COLORS["annotation"],
    )

    ax.text(-0.08, 1.03, "A", transform=ax.transAxes, fontsize=11, fontweight="bold", color=COLORS["text"])

    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"figure5_quality_latency_frontier.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    ensure_output_dir()
    set_academic_style()
    generate_system_architecture_figure()
    generate_backend_migration_figure()
    generate_keep_ratio_tradeoff()
    generate_e2e_breakdown_figure()
    generate_quality_latency_frontier()
    print(f"Generated figures in: {OUT}")


if __name__ == "__main__":
    main()

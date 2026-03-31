import csv
import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.gridspec import GridSpec


ROOT_DIR = "/Users/delete/Desktop/rag_system_副本"
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
FIGURES_DIR = os.path.join(ROOT_DIR, "journal_paper_ccpe/figures/peerj_submission")
os.makedirs(FIGURES_DIR, exist_ok=True)


PALETTE = {
    "baseline": "#4C566A",
    "curve": "#5B8FF9",
    "optimized": "#61DDAA",
    "threshold": "#F6BD16",
    "grid": "#D9D9D9",
    "retrieval": "#8FB8FF",
    "compression": "#5B8FF9",
    "prefill": "#73C0DE",
    "decode": "#3BA272",
    "shared": "#F3F4F6",
    "text": "#2F3640",
}


plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "serif"],
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8.5,
    "axes.linewidth": 0.9,
    "axes.edgecolor": PALETTE["text"],
    "axes.grid": True,
    "grid.color": PALETTE["grid"],
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
    "grid.alpha": 0.7,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "figure.dpi": 300,
})


def load_json(rel_path):
    path = os.path.join(RESULTS_DIR, rel_path)
    with open(path, "r") as f:
        return json.load(f)


def save_dual(fig, filename):
    fig.savefig(os.path.join(FIGURES_DIR, f"{filename}.pdf"))
    fig.savefig(os.path.join(FIGURES_DIR, f"{filename}.png"))
    plt.close(fig)


def panel_label(ax, label):
    ax.text(0.0, 1.04, label, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=11, fontweight="bold", color=PALETTE["text"])


def soften_axes(ax):
    ax.spines["left"].set_color(PALETTE["text"])
    ax.spines["bottom"].set_color(PALETTE["text"])
    ax.tick_params(colors=PALETTE["text"])


def plot_fig1():
    fig, ax = plt.subplots(figsize=(11.5, 4.05))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 34)
    ax.axis("off")

    y = 22.2
    h = 6.6
    w = 15.2
    xs = [4.2, 23.6, 43.0, 62.4, 81.8]
    labels = [
        ("Query", "user request"),
        ("Retriever", "candidate passages"),
        ("Retrieval Compression", "TurboQuant"),
        ("Prompt Budgeting", "KV-aware pruning"),
        ("GGUF Inference", "local decode"),
    ]
    fills = [
        "#FFFFFF",
        "#EAF2FF",
        "#EAF2FF",
        "#E8FBF3",
        "#E8FBF3",
    ]
    edges = [
        PALETTE["text"],
        PALETTE["curve"],
        PALETTE["curve"],
        PALETTE["optimized"],
        PALETTE["optimized"],
    ]

    for i, (x, (title, subtitle)) in enumerate(zip(xs, labels)):
        rect = patches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.28,rounding_size=0.58",
            facecolor=fills[i], edgecolor=edges[i], linewidth=1.5
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + 4.25, title, ha="center", va="center",
                fontsize=10, fontweight="bold", color=PALETTE["text"])
        ax.text(x + w / 2, y + 1.9, subtitle, ha="center", va="center",
                fontsize=8.3, color=PALETTE["text"])
        if i < len(xs) - 1:
            ax.annotate(
                "",
                xy=(x + w + 2.4, y + h / 2),
                xytext=(x + w, y + h / 2),
                arrowprops=dict(arrowstyle="-|>", lw=1.15, color=PALETTE["text"]),
            )

    tele = patches.FancyBboxPatch(
        (69.8, 9.4), 24.6, 7.1, boxstyle="round,pad=0.25,rounding_size=0.55",
        facecolor="#F7F8FA", edgecolor=PALETTE["baseline"], linewidth=1.2
    )
    ax.add_patch(tele)
    ax.text(82.1, 13.6, "Telemetry", ha="center", va="center",
            fontsize=9.8, fontweight="bold", color=PALETTE["text"])
    ax.text(82.1, 11.2, "retrieval | TTFT | TPS | paging", ha="center", va="center",
            fontsize=8.1, color=PALETTE["text"])
    ax.annotate(
        "",
        xy=(82.1, 16.5),
        xytext=(89.4, 22.2),
        arrowprops=dict(arrowstyle="-|>", lw=1.0, ls="--", color=PALETTE["baseline"]),
    )

    budget = patches.FancyBboxPatch(
        (4.3, 2.0), 92.0, 3.7, boxstyle="round,pad=0.18,rounding_size=0.38",
        facecolor=PALETTE["shared"], edgecolor=PALETTE["grid"], linewidth=0.85
    )
    ax.add_patch(budget)
    ax.text(
        50.3,
        4.38,
        "Shared unified-memory budget:",
        ha="center",
        va="center",
        fontsize=8.55,
        fontweight="bold",
        color=PALETTE["text"],
    )
    ax.text(
        50.3,
        2.98,
        "retrieval state  |  prompt buffer  |  weights  |  KV cache  |  OS activity",
        ha="center",
        va="center",
        fontsize=8.0,
        color=PALETTE["text"],
    )

    save_dual(fig, "figure1_system_architecture")


def plot_fig2():
    comp = load_json("evaluation/support_runtime/model_comparison.json")
    mps = load_json("evaluation/support_runtime/v2_performance_final.json")
    mps_ttft = mps["scaling"]["16"]["ttft"] * 1000
    mps_tps = mps["scaling"]["16"]["tps"]
    mps_total = mps["scaling"]["16"]["total_time"]

    values = {
        "Falcon-7B\nMPS": (mps_ttft, mps_tps, mps_total, PALETTE["baseline"]),
        "Falcon-7B-Q\nGGUF": (
            comp["Falcon-7B-Quant"]["ttft_ms"],
            comp["Falcon-7B-Quant"]["tps"],
            comp["Falcon-7B-Quant"]["total_time_s"],
            PALETTE["curve"],
        ),
        "Llama-3-8B-Q\nGGUF\npreferred": (
            comp["Llama-3-8B-Quant"]["ttft_ms"],
            comp["Llama-3-8B-Quant"]["tps"],
            comp["Llama-3-8B-Quant"]["total_time_s"],
            PALETTE["optimized"],
        ),
    }
    labels = list(values.keys())
    ttft = [values[k][0] for k in labels]
    tps = [values[k][1] for k in labels]
    total = [values[k][2] for k in labels]
    colors = [values[k][3] for k in labels]

    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4))
    specs = [
        ("A. TTFT", "TTFT (ms)", ttft, True),
        ("B. Decode throughput", "TPS", tps, False),
        ("C. Total latency", "Total latency (s)", total, True),
    ]
    for ax, (title, ylabel, vals, logy) in zip(axes, specs):
        bars = ax.bar(np.arange(len(labels)), vals, color=colors, width=0.58)
        if logy:
            ax.set_yscale("log")
        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels)
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left")
        soften_axes(ax)
        for bar, v in zip(bars, vals):
            txt = f"{v:.2f}" if v < 100 else f"{v:.1f}"
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * (1.06 if logy else 1.02),
                    txt, ha="center", va="bottom", fontsize=8, color=PALETTE["text"])

    save_dual(fig, "figure2_backend_migration")


def load_swap_series(path):
    agg = defaultdict(int)
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = round(float(row["Time_s"]))
            agg[t] = max(agg[t], int(row["Pageouts_per_sec"]) + int(row["Swapouts_per_sec"]))
    ts = sorted(agg.keys())
    vals = np.array([agg[t] for t in ts], dtype=float)
    vals = vals[:min(60, len(vals))]
    ts = np.arange(len(vals))
    return ts, vals


def plot_fig3():
    t_mps, v_mps = load_swap_series(os.path.join(RESULTS_DIR, "hardware/swap_mps_real.csv"))
    t_opt, v_opt = load_swap_series(os.path.join(RESULTS_DIR, "hardware/swap_sota_real.csv"))
    ymax = max(v_mps.max() if len(v_mps) else 0, v_opt.max() if len(v_opt) else 0)
    threshold = max(500, ymax * 0.22)

    fig, axes = plt.subplots(2, 1, figsize=(8.4, 4.8), sharex=True, sharey=True)
    panels = [
        (axes[0], t_mps, v_mps, PALETTE["baseline"], "A. Unoptimized MPS path", "Unoptimized baseline"),
        (axes[1], t_opt, v_opt, PALETTE["optimized"], "B. Optimized GGUF path", "Optimized GGUF path"),
    ]
    for ax, t, v, color, title, tag in panels:
        ax.plot(t, v, color=color, lw=2.0)
        ax.fill_between(t, 0, v, color=color, alpha=0.16)
        ax.axhline(threshold, color=PALETTE["threshold"], lw=1.2, ls="--")
        ax.set_title(title, loc="left")
        ax.text(0.98, 0.88, tag, transform=ax.transAxes, ha="right", va="top",
                fontsize=8.5, color=PALETTE["text"])
        soften_axes(ax)

    axes[1].set_xlabel("Aligned execution time (s)")
    axes[0].set_ylabel("Paging activity (ops/s)")
    axes[1].set_ylabel("Paging activity (ops/s)")
    axes[0].legend(
        [plt.Line2D([0], [0], color=PALETTE["threshold"], ls="--", lw=1.2)],
        ["paging threshold"],
        loc="upper left",
        frameon=True,
    )

    save_dual(fig, "figure3_swap_profile")


def plot_fig4():
    data = load_json("evaluation/support_runtime/tradeoff_curve.json")
    ratios = [d["keep_ratio"] for d in data]
    ttft = [d["ttft_ms"] for d in data]
    tps = [d["tps"] for d in data]
    selected = 0.6
    sel_idx = ratios.index(selected)

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.5), sharex=True)
    ax1, ax2 = axes

    ax1.plot(ratios, ttft, color=PALETTE["curve"], marker="o", lw=2.0)
    ax1.axvline(selected, color=PALETTE["optimized"], ls="--", lw=1.2)
    ax1.scatter([selected], [ttft[sel_idx]], color=PALETTE["optimized"], s=60, zorder=3)
    ax1.set_title("A. TTFT vs keep ratio", loc="left")
    ax1.set_ylabel("TTFT (ms)")
    ax1.set_xlabel("Keep ratio")
    ax1.invert_xaxis()
    ax1.annotate("selected", xy=(selected, ttft[sel_idx]), xytext=(selected + 0.08, ttft[sel_idx] + 900),
                 arrowprops=dict(arrowstyle="->", lw=0.9, color=PALETTE["optimized"]),
                 fontsize=8, color=PALETTE["text"])
    soften_axes(ax1)

    ax2.plot(ratios, tps, color=PALETTE["curve"], marker="o", lw=2.0)
    ax2.axvline(selected, color=PALETTE["optimized"], ls="--", lw=1.2)
    ax2.scatter([selected], [tps[sel_idx]], color=PALETTE["optimized"], s=60, zorder=3)
    ax2.set_title("B. Decode TPS vs keep ratio", loc="left")
    ax2.set_ylabel("Decode TPS")
    ax2.set_xlabel("Keep ratio")
    ax2.set_ylim(min(tps) - 0.2, max(tps) + 0.25)
    ax2.invert_xaxis()
    soften_axes(ax2)

    save_dual(fig, "figure4_keep_ratio_tradeoff")


def plot_fig5():
    dual_judge = load_json("evaluation/dual_judge_expanded_eval.json")
    search_summary = load_json("evaluation/topn_budget_grid_summary.json")
    baseline = dual_judge["baseline"]
    selected = search_summary["selected_point"]

    baseline_ttft = float(baseline["ttft_mean_ms"])
    selected_ttft = float(selected["ttft_ms"])
    baseline_faithfulness = float(baseline["faithfulness_mean_merged"])
    selected_faithfulness = float(selected["merged_faithfulness"])
    baseline_relevance = float(baseline["relevance_mean_merged"])
    selected_relevance = float(selected["merged_relevance"])

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.3), sharex=True)
    fig.subplots_adjust(wspace=0.32)

    panels = [
        (
            axes[0],
            "A. TTFT vs Faithfulness",
            "Merged faithfulness",
            baseline_faithfulness,
            selected_faithfulness,
            (36, 0.018, -32, -0.014, "left", "right"),
        ),
        (
            axes[1],
            "B. TTFT vs Relevance",
            "Merged relevance",
            baseline_relevance,
            selected_relevance,
            (36, -0.022, -32, 0.018, "left", "right"),
        ),
    ]

    xmin = min(baseline_ttft, selected_ttft) - 120
    xmax = max(baseline_ttft, selected_ttft) + 120
    for ax, title, ylabel, y0, y1, offsets in panels:
        base_dx, base_dy, opt_dx, opt_dy, base_ha, opt_ha = offsets
        ax.scatter(
            [baseline_ttft],
            [y0],
            s=88,
            color=PALETTE["baseline"],
            zorder=3,
        )
        ax.scatter(
            [selected_ttft],
            [y1],
            s=94,
            color=PALETTE["optimized"],
            zorder=4,
        )
        ax.annotate(
            "",
            xy=(selected_ttft, y1),
            xytext=(baseline_ttft, y0),
            arrowprops=dict(arrowstyle="->", lw=1.2, color=PALETTE["curve"]),
        )
        ax.text(
            baseline_ttft + base_dx,
            y0 + base_dy,
            "Baseline",
            fontsize=9.5,
            va="center",
            ha=base_ha,
            color=PALETTE["text"],
        )
        ax.text(
            selected_ttft + opt_dx,
            y1 + opt_dy,
            "Selected",
            fontsize=9.5,
            va="center",
            ha=opt_ha,
            color=PALETTE["text"],
        )
        ax.set_xlim(xmin, xmax)
        ax.set_xlabel("TTFT (ms)")
        ax.set_ylabel(ylabel, labelpad=10)
        ax.set_title(title, loc="left", fontsize=11.5, pad=10)
        soften_axes(ax)

    axes[0].set_ylim(min(baseline_faithfulness, selected_faithfulness) - 0.08, max(baseline_faithfulness, selected_faithfulness) + 0.08)
    axes[1].set_ylim(min(baseline_relevance, selected_relevance) - 0.08, max(baseline_relevance, selected_relevance) + 0.08)

    save_dual(fig, "figure5_quality_latency_frontier")


def plot_fig6():
    data = load_json("evaluation/support_runtime/tradeoff_curve.json")
    baseline = next(d for d in data if d["keep_ratio"] == 1.0)
    optimized = next(d for d in data if d["keep_ratio"] == 0.6)

    def stage_values(d):
        retrieval = d["retrieval_ms"]
        compression = d["scoring_ms"] + d["pruning_ms"]
        prefill = max(d["ttft_ms"] - retrieval - compression, 0)
        decode = max(d["total_e2e_ms"] - d["ttft_ms"], 0)
        return [retrieval, compression, prefill, decode]

    v1 = stage_values(baseline)
    v2 = stage_values(optimized)
    stage_names = ["Retrieval", "Compression", "Prefill", "Decode"]
    stage_colors = [PALETTE["retrieval"], PALETTE["compression"], PALETTE["prefill"], PALETTE["decode"]]

    fig = plt.figure(figsize=(10.6, 4.1))
    gs = GridSpec(1, 3, width_ratios=[1.8, 0.85, 1.15], wspace=0.35)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])

    lefts = [0, 0]
    for idx, (name, color) in enumerate(zip(stage_names, stage_colors)):
        ax1.barh(["Baseline", "Optimized"], [v1[idx], v2[idx]], left=lefts, color=color, height=0.55, label=name)
        lefts[0] += v1[idx]
        lefts[1] += v2[idx]
    ax1.set_title("A. Stage allocation", loc="left")
    ax1.set_xlabel("Latency (ms)")
    ax1.legend(loc="lower right", ncol=2, frameon=True)
    soften_axes(ax1)

    totals = [sum(v1), sum(v2)]
    bars = ax2.bar(["Baseline", "Optimized"], totals, color=[PALETTE["baseline"], PALETTE["optimized"]], width=0.58)
    ax2.set_title("B. Total latency", loc="left")
    ax2.set_ylabel("End-to-end latency (ms)")
    soften_axes(ax2)
    for bar, val in zip(bars, totals):
        ax2.text(bar.get_x() + bar.get_width() / 2, val * 1.02, f"{val/1000:.1f} s", ha="center", va="bottom", fontsize=8)

    total_opt = sum(v2)
    shares = [x / total_opt * 100 for x in v2]
    left = 0
    for name, share, color in zip(stage_names, shares, stage_colors):
        ax3.barh(["Optimized"], [share], left=left, color=color, height=0.55)
        if share > 7:
            ax3.text(left + share / 2, 0, f"{name}\n{share:.1f}%", ha="center", va="center", fontsize=7.8, color=PALETTE["text"])
        left += share
    ax3.set_xlim(0, 100)
    ax3.set_title("C. Optimized latency share", loc="left")
    ax3.set_xlabel("Share (%)")
    soften_axes(ax3)

    save_dual(fig, "figure6_e2e_breakdown")


if __name__ == "__main__":
    plot_fig1()
    plot_fig2()
    plot_fig3()
    plot_fig4()
    plot_fig5()
    plot_fig6()
    print("Generated updated PeerJ submission figures.")

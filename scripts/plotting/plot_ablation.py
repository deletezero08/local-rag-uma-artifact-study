#!/usr/bin/env python3
import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent.parent
SUMMARY_PATH = ROOT / "results" / "evaluation" / "legacy_misc" / "ablation_summary.json"
OUT_DIR = ROOT / "results" / "figures" / "legacy_misc"


def load_summary() -> dict:
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError(f"Missing summary file: {SUMMARY_PATH}")
    return json.loads(SUMMARY_PATH.read_text("utf-8"))


def save_fig(fig: plt.Figure, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / f"{name}.eps", bbox_inches="tight")


def extract_metric(data: dict, metric: str) -> tuple[list[str], list[float], list[float], list[float]]:
    modes, means, lower, upper = [], [], [], []
    for mode, content in data.items():
        if not isinstance(content, dict):
            continue
        stats = content.get(metric) if metric != "latency_mean" else content.get("latency")
        if not stats:
            continue
        modes.append(mode)
        means.append(float(stats.get("mean", 0.0)))
        lower.append(float(stats.get("ci_lower", stats.get("mean", 0.0))))
        upper.append(float(stats.get("ci_upper", stats.get("mean", 0.0))))
    return modes, means, lower, upper


def plot_metric(data: dict, metric: str, title: str, ylabel: str, filename: str) -> None:
    modes, means, lower, upper = extract_metric(data, metric)
    if not modes:
        return
    x = list(range(len(modes)))
    yerr = [
        [max(0.0, means[i] - lower[i]) for i in range(len(means))],
        [max(0.0, upper[i] - means[i]) for i in range(len(means))],
    ]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(x, means, yerr=yerr, capsize=5)
    ax.set_xticks(x)
    ax.set_xticklabels(modes)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    save_fig(fig, filename)
    plt.close(fig)


def main() -> None:
    summary = load_summary()
    plot_metric(summary, "faithfulness", "MemoraRAG Ablation - Faithfulness", "Faithfulness", "ablation_faithfulness")
    plot_metric(summary, "relevance", "MemoraRAG Ablation - Relevance", "Relevance", "ablation_relevance")
    plot_metric(summary, "latency_mean", "MemoraRAG Ablation - Mean Latency", "Latency (s)", "ablation_latency")
    print(f"✅ figures saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()

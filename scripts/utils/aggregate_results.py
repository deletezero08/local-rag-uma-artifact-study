#!/usr/bin/env python3
"""
统计汇总脚本 (Aggregate Results)
读取 results/evaluation/ 下所有 evaluation_<mode>_*.json 文件，
计算每种模式的均值、标准差和 95% 置信区间，输出汇总 JSON 与格式化对比表。
"""
import os
import sys
import json
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple

try:
    from scipy.stats import wilcoxon
except Exception:
    wilcoxon = None

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = ROOT_DIR / "experiments" / "results"


def load_latest_results() -> Dict[str, Dict[str, Any]]:
    """
    扫描结果目录，为每种模式找到最新的评测结果文件。
    返回 {mode: parsed_json}
    """
    modes = ["vector_only", "bm25_only", "ensemble", "rrf"]
    latest: Dict[str, Dict[str, Any]] = {}

    for mode in modes:
        candidates = sorted(
            RESULTS_DIR.glob(f"evaluation_{mode}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            print(f"⚠️  未找到 {mode} 的评测结果文件，跳过。")
            continue
        path = candidates[0]
        try:
            data = json.loads(path.read_text("utf-8"))
            latest[mode] = data
            print(f"✅ 加载 {mode}: {path.name}")
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  加载 {path.name} 失败: {e}")

    return latest


def compute_stats(values: List[float]) -> Dict[str, float]:
    """
    计算一组数值的均值、标准差和 95% 置信区间。
    """
    n = len(values)
    if n == 0:
        return {"mean": 0, "std": 0, "ci_lower": 0, "ci_upper": 0, "n": 0}

    mean = sum(values) / n
    if n < 2:
        return {"mean": mean, "std": 0, "ci_lower": mean, "ci_upper": mean, "n": n}

    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    std = math.sqrt(variance)

    # 95% CI using t-distribution approximation (z=1.96 for large n, conservative for small n)
    z = 1.96
    margin = z * std / math.sqrt(n)

    return {
        "mean": round(mean, 3),
        "std": round(std, 3),
        "ci_lower": round(mean - margin, 3),
        "ci_upper": round(mean + margin, 3),
        "n": n,
    }


def _flatten_mode_scores(data: Dict[str, Any], metric: str) -> Dict[str, float]:
    flattened: Dict[str, float] = {}
    iterations = data.get("iterations", [])
    for iter_idx, rows in enumerate(iterations):
        for row in rows:
            if metric == "latency":
                value = row.get("latency")
            else:
                value = (row.get("scores") or {}).get(metric)
            if value is None:
                continue
            key = f"{iter_idx}:{row.get('id')}"
            flattened[key] = float(value)
    return flattened


def _paired_vectors(
    results: Dict[str, Dict[str, Any]],
    mode_a: str,
    mode_b: str,
    metric: str,
) -> Tuple[List[float], List[float]]:
    a_scores = _flatten_mode_scores(results.get(mode_a, {}), metric)
    b_scores = _flatten_mode_scores(results.get(mode_b, {}), metric)
    common_keys = sorted(set(a_scores.keys()) & set(b_scores.keys()))
    return [a_scores[k] for k in common_keys], [b_scores[k] for k in common_keys]


def _wilcoxon_test(
    results: Dict[str, Dict[str, Any]],
    mode_a: str,
    mode_b: str,
    metric: str,
) -> Dict[str, Any]:
    x, y = _paired_vectors(results, mode_a, mode_b, metric)
    if len(x) < 2:
        return {
            "available": False,
            "reason": "insufficient_pairs",
            "metric": metric,
            "mode_a": mode_a,
            "mode_b": mode_b,
            "n_pairs": len(x),
        }
    if wilcoxon is None:
        return {
            "available": False,
            "reason": "scipy_not_installed",
            "metric": metric,
            "mode_a": mode_a,
            "mode_b": mode_b,
            "n_pairs": len(x),
        }
    try:
        stat = wilcoxon(x, y, zero_method="wilcox", alternative="two-sided", method="auto")
        mean_diff = (sum(y) / len(y)) - (sum(x) / len(x))
        # Cohen's d effect size
        diffs = [b - a for a, b in zip(x, y)]
        d_mean = sum(diffs) / len(diffs)
        d_var = sum((d - d_mean) ** 2 for d in diffs) / max(1, len(diffs) - 1)
        pooled_std = math.sqrt(d_var) if d_var > 0 else 1e-9
        cohens_d = d_mean / pooled_std
        # Interpret effect size
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            effect_label = "negligible"
        elif abs_d < 0.5:
            effect_label = "small"
        elif abs_d < 0.8:
            effect_label = "medium"
        else:
            effect_label = "large"
        return {
            "available": True,
            "metric": metric,
            "mode_a": mode_a,
            "mode_b": mode_b,
            "n_pairs": len(x),
            "p_value": float(stat.pvalue),
            "statistic": float(stat.statistic),
            "cohens_d": round(cohens_d, 4),
            "effect_size": effect_label,
            "direction": f"{mode_b}_higher" if mean_diff > 0 else f"{mode_a}_higher",
            "mean_diff_b_minus_a": round(mean_diff, 4),
        }
    except Exception as exc:
        return {
            "available": False,
            "reason": f"wilcoxon_error:{exc}",
            "metric": metric,
            "mode_a": mode_a,
            "mode_b": mode_b,
            "n_pairs": len(x),
        }


def aggregate(results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    对每种模式的评测结果进行统计汇总。
    """
    summary: Dict[str, Any] = {}

    for mode, data in results.items():
        iterations = data.get("iterations", [])
        # Flatten all question results across iterations
        all_items = [item for iteration in iterations for item in iteration]

        faith_scores = [item["scores"].get("faithfulness", 0) for item in all_items if "scores" in item]
        rel_scores = [item["scores"].get("relevance", 0) for item in all_items if "scores" in item]
        latencies = [item.get("latency", 0) for item in all_items if "latency" in item]

        summary[mode] = {
            "faithfulness": compute_stats(faith_scores),
            "relevance": compute_stats(rel_scores),
            "latency": compute_stats(latencies),
            "source_file": data.get("metadata", {}).get("timestamp", "unknown"),
            "config_version": data.get("metadata", {}).get("config_version", "unknown"),
        }

    comparisons = [("vector_only", "ensemble"), ("vector_only", "rrf"), ("ensemble", "rrf")]
    tests: List[Dict[str, Any]] = []
    for mode_a, mode_b in comparisons:
        if mode_a not in results or mode_b not in results:
            continue
        tests.append(_wilcoxon_test(results, mode_a, mode_b, "faithfulness"))
        tests.append(_wilcoxon_test(results, mode_a, mode_b, "relevance"))

    summary["significance_tests"] = tests
    return summary


def print_table(summary: Dict[str, Any]) -> None:
    """
    输出格式化的对比表。
    """
    print("\n" + "=" * 100)
    print(f"{'📊 Ablation Study Summary Table':^100}")
    print("=" * 100)
    print(
        f"{'Mode':<15} | {'Faithfulness':^22} | {'Relevance':^22} | {'Latency (s)':^22} | {'n':>3}"
    )
    print(
        f"{'':15} | {'mean ± std (CI)':^22} | {'mean ± std (CI)':^22} | {'mean ± std (CI)':^22} |"
    )
    print("-" * 100)

    for mode in ["vector_only", "bm25_only", "ensemble", "rrf"]:
        if mode not in summary:
            print(f"{mode:<15} | {'(no data)':^22} | {'(no data)':^22} | {'(no data)':^22} | {'0':>3}")
            continue
        s = summary[mode]
        f = s["faithfulness"]
        r = s["relevance"]
        l = s["latency"]

        def fmt(stats):
            return f"{stats['mean']:.1f}±{stats['std']:.1f} [{stats['ci_lower']:.1f},{stats['ci_upper']:.1f}]"

        print(f"{mode:<15} | {fmt(f):^22} | {fmt(r):^22} | {fmt(l):^22} | {f['n']:>3}")

    print("=" * 100)
    print("Note: CI = 95% Confidence Interval (z=1.96)")
    print()


def print_significance(summary: Dict[str, Any]) -> None:
    tests = summary.get("significance_tests") or []
    if not tests:
        print("⚠️ 未生成显著性检验结果。")
        return
    print("=" * 120)
    print(f"{'📈 Wilcoxon Significance Tests + Effect Size':^120}")
    print("=" * 120)
    print(f"{'Comparison':<32} | {'Metric':<12} | {'n':<4} | {'p_value':<12} | {'Cohen\'s d':<10} | {'Effect':<10} | {'Direction'}")
    print("-" * 120)
    for t in tests:
        comp = f"{t.get('mode_a')} vs {t.get('mode_b')}"
        metric = t.get("metric", "-")
        n_pairs = t.get("n_pairs", 0)
        if t.get("available"):
            p_value = f"{t.get('p_value', 1.0):.6f}"
            cohens_d = f"{t.get('cohens_d', 0.0):.4f}"
            effect = t.get("effect_size", "-")
            direction = t.get("direction", "-")
        else:
            p_value = "N/A"
            cohens_d = "N/A"
            effect = "-"
            direction = t.get("reason", "unavailable")
        print(f"{comp:<32} | {metric:<12} | {n_pairs:<4} | {p_value:<12} | {cohens_d:<10} | {effect:<10} | {direction}")
    print("=" * 120)
    print("Note: p < 0.05 = 统计显著 | Cohen's d: <0.2 negligible, 0.2-0.5 small, 0.5-0.8 medium, >0.8 large")
    print()


def main():
    print("🚀 Starting Ablation Study Aggregation...")
    results = load_latest_results()

    if not results:
        print("❌ 没有找到任何评测结果文件。请先运行 scripts/evaluate.py。")
        return

    summary = aggregate(results)
    print_table(summary)
    print_significance(summary)

    # Save to JSON
    output_file = RESULTS_DIR / "ablation_summary.json"
    output_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), "utf-8")
    print(f"✅ 汇总已保存至 {output_file}")


if __name__ == "__main__":
    main()

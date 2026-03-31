#!/usr/bin/env python3
"""Generate an independent failure casebook for the current paper track."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DUAL = ROOT_DIR / "results" / "evaluation" / "dual_judge_expanded_eval.json"
DEFAULT_TQ = ROOT_DIR / "results" / "evaluation" / "turboquant_e2e_quality_ablation.json"
DEFAULT_GRID = ROOT_DIR / "results" / "tuning" / "topn_budget_grid.json"
DEFAULT_PRUNING = ROOT_DIR / "results" / "evaluation" / "pruning_policy_ablation.json"
DEFAULT_OUT = ROOT_DIR / "results" / "evaluation" / "failure_casebook.md"


def lowest_rows(rows: List[Dict[str, Any]], key: str, n: int = 5) -> List[Dict[str, Any]]:
    return sorted(rows, key=lambda row: float(row.get(key, 0.0)))[:n]


def highest_gap_rows(rows: List[Dict[str, Any]], n: int = 5) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: max(float(row.get("gap_f", 0.0)), float(row.get("gap_r", 0.0))),
        reverse=True,
    )[:n]


def append_rows(lines: List[str], rows: Iterable[Dict[str, Any]], formatter) -> None:
    for row in rows:
        lines.append(formatter(row))


def render_quality_section(data: Dict[str, Any]) -> List[str]:
    optimized_rows = data.get("optimized_rows", [])
    low_faith = lowest_rows(optimized_rows, "faith_m")
    high_gap = highest_gap_rows(optimized_rows)
    baseline = data.get("baseline", {})
    optimized = data.get("optimized", {})
    lines = [
        "## E4 Expanded Dual-Judge",
        "",
        f"- Baseline merged faithfulness / relevance: `{baseline.get('faithfulness_mean_merged')}` / `{baseline.get('relevance_mean_merged')}`",
        f"- Optimized merged faithfulness / relevance: `{optimized.get('faithfulness_mean_merged')}` / `{optimized.get('relevance_mean_merged')}`",
        "",
        "### Lowest-faithfulness optimized cases",
        "",
    ]
    append_rows(
        lines,
        low_faith,
        lambda row: f"- `{row['id']}` faith `{row['faith_m']}`, rel `{row['rel_m']}`, gap_f `{row['gap_f']}`, gap_r `{row['gap_r']}`: {row['question']}",
    )
    lines += ["", "### Highest judge-gap optimized cases", ""]
    append_rows(
        lines,
        high_gap,
        lambda row: f"- `{row['id']}` faith `{row['faith_m']}`, rel `{row['rel_m']}`, gap_f `{row['gap_f']}`, gap_r `{row['gap_r']}`: {row['question']}",
    )
    return lines


def render_turboquant_section(data: Dict[str, Any]) -> List[str]:
    fp32 = data.get("fp32_off", {})
    tq = data.get("turboquant_on", {})
    tq_rows = data.get("turboquant_on_rows", [])
    drift_rows = [row for row in tq_rows if row.get("auto_error_category") == "factual_drift"][:5]
    miss_rows = [row for row in tq_rows if row.get("auto_error_category") == "retrieval_miss"][:5]
    lines = [
        "## E2 TurboQuant On/Off",
        "",
        f"- FP32 off: recall `{fp32.get('recall_at_k_mean')}`, faith `{fp32.get('faithfulness_mean_merged')}`, rel `{fp32.get('relevance_mean_merged')}`, error `{fp32.get('answer_error_rate')}`",
        f"- TurboQuant on: recall `{tq.get('recall_at_k_mean')}`, faith `{tq.get('faithfulness_mean_merged')}`, rel `{tq.get('relevance_mean_merged')}`, error `{tq.get('answer_error_rate')}`",
        "",
        "### Representative factual-drift cases under TurboQuant",
        "",
    ]
    append_rows(
        lines,
        drift_rows,
        lambda row: f"- `{row['id']}` recall `{row['recall_at_k']}`, faith `{row['faith_m']}`, rel `{row['rel_m']}`: {row['question']}",
    )
    lines += ["", "### Representative retrieval-miss cases under TurboQuant", ""]
    append_rows(
        lines,
        miss_rows,
        lambda row: f"- `{row['id']}` recall `{row['recall_at_k']}`, faith `{row['faith_m']}`, rel `{row['rel_m']}`: {row['question']}",
    )
    return lines


def render_grid_section(data: Dict[str, Any]) -> List[str]:
    points = {point.get("point_id"): point for point in data.get("points", [])}
    selected = points.get("t5_b1500") or {}
    selected_rows = selected.get("rows", [])
    selected_failures = [row for row in selected_rows if row.get("auto_error_category") != "ok"][:5]
    candidates = []
    for pid in ["t5_b1500", "t10_b2000", "t10_b2500"]:
        point = points.get(pid)
        if point:
            candidates.append(point)
    lines = [
        "## E7 Topn x Budget Grid",
        "",
        "### Candidate operating points",
        "",
    ]
    append_rows(
        lines,
        candidates,
        lambda point: (
            f"- `{point['point_id']}` TTFT `{point.get('summary', {}).get('ttft_ms')}`, "
            f"faith `{point.get('summary', {}).get('merged_faithfulness')}`, "
            f"rel `{point.get('summary', {}).get('merged_relevance')}`, "
            f"note `{point.get('selection', {}).get('selection_note', '')}`"
        ),
    )
    lines += ["", "### Representative failures under selected point `t5_b1500`", ""]
    append_rows(
        lines,
        selected_failures,
        lambda row: f"- `{row['id']}` `{row.get('auto_error_category')}` faith `{row.get('faith_m')}` rel `{row.get('rel_m')}`: {row['question']}",
    )
    return lines


def render_pruning_section(path: Path) -> List[str]:
    if not path.exists():
        return [
            "## E8 Pruning Policy Ablation",
            "",
            "- Not available at generation time.",
        ]
    data = json.loads(path.read_text("utf-8"))
    policies = data.get("policies", [])
    completed = [p for p in policies if p.get("status") == "completed"]
    lines = [
        "## E8 Pruning Policy Ablation",
        "",
        "### Policy summaries",
        "",
    ]
    append_rows(
        lines,
        completed,
        lambda p: (
            f"- `{p['policy_id']}` TTFT `{p.get('summary', {}).get('ttft_mean_ms')}`, "
            f"faith `{p.get('summary', {}).get('faithfulness_mean_merged')}`, "
            f"rel `{p.get('summary', {}).get('relevance_mean_merged')}`, "
            f"error `{p.get('summary', {}).get('answer_error_rate')}`"
        ),
    )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a standalone paper-track failure casebook.")
    parser.add_argument("--dual-judge", default=str(DEFAULT_DUAL))
    parser.add_argument("--turboquant", default=str(DEFAULT_TQ))
    parser.add_argument("--grid", default=str(DEFAULT_GRID))
    parser.add_argument("--pruning", default=str(DEFAULT_PRUNING))
    parser.add_argument("--out-file", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    dual = json.loads(Path(args.dual_judge).read_text("utf-8"))
    turbo = json.loads(Path(args.turboquant).read_text("utf-8"))
    grid = json.loads(Path(args.grid).read_text("utf-8"))

    lines = [
        "# Failure Casebook",
        "",
        "This note consolidates representative failure and disagreement cases across the current paper-track experiments.",
        "",
    ]
    lines += render_quality_section(dual)
    lines += ["", "---", ""]
    lines += render_turboquant_section(turbo)
    lines += ["", "---", ""]
    lines += render_grid_section(grid)
    lines += ["", "---", ""]
    lines += render_pruning_section(Path(args.pruning))

    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", "utf-8")
    print(f"SAVED: {out_path}")


if __name__ == "__main__":
    main()

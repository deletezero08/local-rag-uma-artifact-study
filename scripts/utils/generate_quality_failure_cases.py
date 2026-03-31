#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DUAL = ROOT_DIR / "results" / "evaluation" / "dual_judge_expanded_eval.json"
DEFAULT_TQ = ROOT_DIR / "results" / "evaluation" / "turboquant_e2e_quality_ablation.json"
DEFAULT_OUT = ROOT_DIR / "results" / "evaluation" / "quality_failure_cases.md"


def lowest_rows(rows: List[Dict[str, Any]], key: str, n: int = 5) -> List[Dict[str, Any]]:
    return sorted(rows, key=lambda row: float(row.get(key, 0.0)))[:n]


def highest_gap_rows(rows: List[Dict[str, Any]], n: int = 5) -> List[Dict[str, Any]]:
    return sorted(rows, key=lambda row: max(float(row.get("gap_f", 0.0)), float(row.get("gap_r", 0.0))), reverse=True)[:n]


def render_dual_judge_section(data: Dict[str, Any]) -> List[str]:
    baseline = data["baseline"]
    optimized = data["optimized"]
    optimized_rows = data["optimized_rows"]
    low_faith = lowest_rows(optimized_rows, "faith_m")
    high_gap = highest_gap_rows(optimized_rows)

    lines = [
        "## E4 Selected Configuration",
        "",
        f"- Baseline merged faithfulness / relevance: `{baseline['faithfulness_mean_merged']}` / `{baseline['relevance_mean_merged']}`",
        f"- Optimized merged faithfulness / relevance: `{optimized['faithfulness_mean_merged']}` / `{optimized['relevance_mean_merged']}`",
        f"- Optimized judge agreement rate (gap <= 1 on both axes): `{optimized['judge_agreement_rate_gap_le_1']}`",
        "",
        "### Lowest merged-faithfulness optimized cases",
        "",
    ]
    for row in low_faith:
        lines.append(
            f"- `{row['id']}` faith `{row['faith_m']}`, relevance `{row['rel_m']}`, gap_f `{row['gap_f']}`, gap_r `{row['gap_r']}`: {row['question']}"
        )
    lines += ["", "### Highest judge-gap optimized cases", ""]
    for row in high_gap:
        lines.append(
            f"- `{row['id']}` faith `{row['faith_m']}`, relevance `{row['rel_m']}`, gap_f `{row['gap_f']}`, gap_r `{row['gap_r']}`: {row['question']}"
        )
    return lines


def render_turboquant_section(data: Dict[str, Any]) -> List[str]:
    fp32 = data["fp32_off"]
    tq = data["turboquant_on"]
    tq_rows = data["turboquant_on_rows"]
    drift_rows = [row for row in tq_rows if row.get("auto_error_category") == "factual_drift"][:5]
    miss_rows = [row for row in tq_rows if row.get("auto_error_category") == "retrieval_miss"][:5]

    lines = [
        "## E2 TurboQuant On/Off",
        "",
        f"- FP32 off: Recall@10 `{fp32['recall_at_k_mean']}`, merged faithfulness `{fp32['faithfulness_mean_merged']}`, merged relevance `{fp32['relevance_mean_merged']}`, error rate `{fp32['answer_error_rate']}`",
        f"- TurboQuant on: Recall@10 `{tq['recall_at_k_mean']}`, merged faithfulness `{tq['faithfulness_mean_merged']}`, merged relevance `{tq['relevance_mean_merged']}`, error rate `{tq['answer_error_rate']}`",
        "",
        "### Representative factual-drift cases under TurboQuant",
        "",
    ]
    for row in drift_rows:
        lines.append(
            f"- `{row['id']}` recall `{row['recall_at_k']}`, faith `{row['faith_m']}`, rel `{row['rel_m']}`: {row['question']}"
        )
        lines.append(f"  source docs: `{'; '.join(row.get('source_docs', []))}`")
    lines += ["", "### Representative retrieval-miss cases under TurboQuant", ""]
    for row in miss_rows:
        lines.append(
            f"- `{row['id']}` recall `{row['recall_at_k']}`, faith `{row['faith_m']}`, rel `{row['rel_m']}`: {row['question']}"
        )
        lines.append(f"  retrieved docs: `{'; '.join(row.get('retrieved_doc_paths', [])[:5])}`")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a markdown summary of quality failure cases.")
    parser.add_argument("--dual-judge", default=str(DEFAULT_DUAL))
    parser.add_argument("--turboquant", default=str(DEFAULT_TQ))
    parser.add_argument("--out-file", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    dual = json.loads(Path(args.dual_judge).read_text("utf-8"))
    turbo = json.loads(Path(args.turboquant).read_text("utf-8"))
    lines = [
        "# Quality Failure Cases",
        "",
        "This note summarizes representative low-quality and high-disagreement cases from the paper-track quality runs.",
        "",
    ]
    lines += render_dual_judge_section(dual)
    lines += ["", "---", ""]
    lines += render_turboquant_section(turbo)
    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", "utf-8")
    print(f"SAVED: {out_path}")


if __name__ == "__main__":
    main()

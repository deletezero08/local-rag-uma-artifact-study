#!/usr/bin/env python3
import json
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
OUT_FILE = ROOT_DIR / "results" / "evaluation" / "paper_p0_manifest.json"


def main() -> None:
    manifest = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "track": "journal_paper_ccpe",
        "principles": [
            "Prioritize evidence strength over new modules.",
            "Keep telemetry consistent across retrieval, compression, TTFT, TPS, wall time, tail latency, and quality.",
            "Write paper-facing outputs to results/evaluation, results/tuning, and results/hardware only.",
        ],
        "experiments": {
            "E1": {
                "name": "Repeated runs and error bars",
                "priority": "P0",
                "outputs": [
                    "results/evaluation/model_comparison_repeated.json",
                    "results/tuning/keep_ratio_repeat_scan.json",
                    "results/evaluation/concurrency_repeat_summary.json",
                ],
            },
            "E2": {
                "name": "TurboQuant on/off end-to-end quality",
                "priority": "P0",
                "outputs": [
                    "results/evaluation/turboquant_e2e_quality_ablation.json",
                    "results/evaluation/turboquant_manual_audit.csv",
                ],
            },
            "E3": {
                "name": "Concurrency tail latency",
                "priority": "P0",
                "outputs": [
                    "results/evaluation/concurrency_tail_latency_report.json",
                    "results/hardware/concurrency_vmstat_trace.csv",
                ],
            },
            "E4": {
                "name": "Expanded quality evaluation",
                "priority": "P0",
                "outputs": [
                    "results/evaluation/dual_judge_expanded_eval.json",
                    "results/evaluation/quality_failure_cases.md",
                ],
            },
        },
        "commands": {
            "E1_keep_ratio": "python3 scripts/benchmarking/paper_keep_ratio_repeat.py --out-file results/tuning/keep_ratio_repeat_scan.json",
            "E3_concurrency": "python3 scripts/benchmarking/paper_concurrency_suite.py --out-file results/evaluation/concurrency_tail_latency_report.json",
            "swap_trace": "python3 scripts/benchmarking/profile_swap.py --out results/hardware/concurrency_vmstat_trace.csv --duration 120",
        },
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    print(f"SAVED: {OUT_FILE}")


if __name__ == "__main__":
    main()

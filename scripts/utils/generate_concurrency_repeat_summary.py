#!/usr/bin/env python3
"""Derive a compact paper-facing summary from the full concurrency report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _round(value: float | int | None, digits: int = 3):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return round(float(value), digits)


def build_summary(report: dict) -> dict:
    modes = report["modes"]
    summary_rows = []
    deltas = {}

    for mode_name, groups in modes.items():
        for label, block in groups.items():
            stats = block["summary"]
            vm = stats.get("vm_stat_summary", {})
            summary_rows.append(
                {
                    "mode": mode_name,
                    "concurrency_label": label,
                    "concurrency": block["concurrency"],
                    "round_count": block["round_count"],
                    "successful_rounds": block["successful_rounds"],
                    "success_rate_mean": _round(stats.get("success_rate_mean")),
                    "success_rate_std": _round(stats.get("success_rate_std")),
                    "error_count_mean": _round(stats.get("error_count_mean")),
                    "error_count_std": _round(stats.get("error_count_std")),
                    "p50_ttft_ms_mean": _round(stats.get("p50_ttft_ms_mean")),
                    "p95_ttft_ms_mean": _round(stats.get("p95_ttft_ms_mean")),
                    "p99_ttft_ms_mean": _round(stats.get("p99_ttft_ms_mean")),
                    "aggregate_tps_mean": _round(stats.get("aggregate_tps_mean")),
                    "wall_time_sec_mean": _round(stats.get("wall_time_sec_mean")),
                    "vm_peak_total_ops_max": _round(vm.get("peak_total_ops_max")),
                    "vm_peak_pageouts_max": _round(vm.get("peak_pageouts_max")),
                    "vm_peak_swapouts_max": _round(vm.get("peak_swapouts_max")),
                }
            )

    for label, full_block in modes["full_context"].items():
        opt_block = modes["optimized_path"].get(label)
        if not opt_block:
            continue

        full_stats = full_block["summary"]
        opt_stats = opt_block["summary"]
        full_vm = full_stats.get("vm_stat_summary", {})
        opt_vm = opt_stats.get("vm_stat_summary", {})

        deltas[label] = {
            "p95_ttft_ms_delta": _round(
                opt_stats.get("p95_ttft_ms_mean", 0.0)
                - full_stats.get("p95_ttft_ms_mean", 0.0)
            ),
            "p95_ttft_ms_delta_percent": _round(
                (
                    (
                        opt_stats.get("p95_ttft_ms_mean", 0.0)
                        - full_stats.get("p95_ttft_ms_mean", 0.0)
                    )
                    / full_stats.get("p95_ttft_ms_mean", 1.0)
                )
                * 100.0
            ),
            "aggregate_tps_delta": _round(
                opt_stats.get("aggregate_tps_mean", 0.0)
                - full_stats.get("aggregate_tps_mean", 0.0)
            ),
            "wall_time_sec_delta": _round(
                opt_stats.get("wall_time_sec_mean", 0.0)
                - full_stats.get("wall_time_sec_mean", 0.0)
            ),
            "success_rate_delta": _round(
                opt_stats.get("success_rate_mean", 0.0)
                - full_stats.get("success_rate_mean", 0.0)
            ),
            "error_count_delta": _round(
                opt_stats.get("error_count_mean", 0.0)
                - full_stats.get("error_count_mean", 0.0)
            ),
            "peak_swapouts_max_delta": _round(
                opt_vm.get("peak_swapouts_max", 0.0)
                - full_vm.get("peak_swapouts_max", 0.0)
            ),
        }

    return {
        "timestamp": report.get("timestamp"),
        "source_report": "results/evaluation/concurrency_tail_latency_report.json",
        "schema_version": 1,
        "config": report.get("config", {}),
        "summary_rows": summary_rows,
        "mode_deltas_vs_full_context": deltas,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report-file",
        default="results/evaluation/concurrency_tail_latency_report.json",
        help="Full concurrency report JSON.",
    )
    parser.add_argument(
        "--out-file",
        default="results/evaluation/concurrency_repeat_summary.json",
        help="Compact summary JSON.",
    )
    args = parser.parse_args()

    report = json.loads(Path(args.report_file).read_text(encoding="utf-8"))
    summary = build_summary(report)
    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"SAVED: {out_path}")


if __name__ == "__main__":
    main()

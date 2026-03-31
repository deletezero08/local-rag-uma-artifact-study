#!/usr/bin/env python3
import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List

import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.rag_pipeline import MemoraRAGPipeline


DEFAULT_MODEL = str(ROOT_DIR / "models" / "Llama-3-8B-Instruct.Q4_K_M.gguf")
DEFAULT_OUTPUT = ROOT_DIR / "results" / "evaluation" / "concurrency_tail_latency_report.json"
DEFAULT_VMSTAT_DIR = ROOT_DIR / "results" / "hardware" / "concurrency_vmstat"


def build_mock_docs(num_docs: int, repeat: int) -> List[str]:
    docs = []
    for i in range(num_docs):
        docs.append(
            f"Context Chunk {i}: Apple Silicon UMA shares bandwidth across weights, KV cache, "
            f"retrieved evidence, and operating-system activity. "
            f"Tail latency rises when paging pressure increases. " * repeat
        )
    return docs


def worker_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        pipeline = MemoraRAGPipeline(
            model_path=payload["model_path"],
            index_path=payload["index_path"],
            n_ctx=payload["n_ctx"],
        )
        if not payload["use_dynamic"]:
            pipeline.compressor.keep_ratio = 1.0
        result = pipeline.run(
            payload["query"],
            top_k=payload["top_k"],
            mock_docs=payload["mock_docs"],
            use_dynamic=payload["use_dynamic"],
        )
        waterfall = result["waterfall"]
        decode_ms = float(waterfall.get("llm_decode_ms", 0.0))
        generated_tokens = int(result.get("generated_tokens", 0))
        decode_tps = generated_tokens / (decode_ms / 1000.0) if decode_ms > 0 else 0.0
        return {
            "success": True,
            "ttft_ms": float(waterfall.get("llm_prefill_ms", 0.0)),
            "total_ms": float(waterfall.get("total_pipeline_ms", 0.0)),
            "decode_tps": decode_tps,
            "generated_tokens": generated_tokens,
            "strategy": result.get("pruning_strategy", "unknown"),
        }
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def start_vmstat_trace(output_file: Path) -> subprocess.Popen[str]:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(
        [sys.executable, str(ROOT_DIR / "scripts" / "benchmarking" / "profile_swap.py"), "--out", str(output_file)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
    )


def stop_vmstat_trace(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if hasattr(os, "getpgid"):
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        else:
            process.terminate()
    except Exception:
        process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()


def summarize_vmstat(trace_file: Path) -> Dict[str, Any]:
    if not trace_file.exists():
        return {
            "available": False,
            "samples": 0,
            "peak_total_ops": 0,
            "mean_total_ops": 0.0,
            "peak_pageouts": 0,
            "peak_swapouts": 0,
        }
    totals: List[int] = []
    pageouts: List[int] = []
    swapouts: List[int] = []
    with trace_file.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                po = int(float(row["Pageouts_per_sec"]))
                so = int(float(row["Swapouts_per_sec"]))
            except Exception:
                continue
            pageouts.append(po)
            swapouts.append(so)
            totals.append(po + so)
    return {
        "available": True,
        "samples": len(totals),
        "peak_total_ops": max(totals) if totals else 0,
        "mean_total_ops": round(mean(totals), 3) if totals else 0.0,
        "peak_pageouts": max(pageouts) if pageouts else 0,
        "peak_swapouts": max(swapouts) if swapouts else 0,
    }


def summarize_round(mode: str, concurrency: int, round_id: int, rows: List[Dict[str, Any]], wall_time_sec: float) -> Dict[str, Any]:
    ttfts = [r["ttft_ms"] for r in rows]
    totals = [r["total_ms"] for r in rows]
    tpss = [r["decode_tps"] for r in rows]
    tokens = [r["generated_tokens"] for r in rows]
    aggregate_tps = sum(tokens) / wall_time_sec if wall_time_sec > 0 else 0.0
    return {
        "mode": mode,
        "concurrency": concurrency,
        "round": round_id,
        "successes": len(rows),
        "wall_time_sec": round(wall_time_sec, 3),
        "mean_ttft_ms": round(mean(ttfts), 3),
        "p50_ttft_ms": round(float(np.percentile(ttfts, 50)), 3),
        "p95_ttft_ms": round(float(np.percentile(ttfts, 95)), 3),
        "p99_ttft_ms": round(float(np.percentile(ttfts, 99)), 3),
        "mean_total_ms": round(mean(totals), 3),
        "mean_decode_tps": round(mean(tpss), 3),
        "aggregate_tps": round(aggregate_tps, 3),
        "strategies_used": sorted({r["strategy"] for r in rows}),
        "worker_rows": rows,
    }


def aggregate_mode(rounds: List[Dict[str, Any]]) -> Dict[str, Any]:
    keys = [
        "wall_time_sec",
        "mean_ttft_ms",
        "p50_ttft_ms",
        "p95_ttft_ms",
        "p99_ttft_ms",
        "mean_total_ms",
        "mean_decode_tps",
        "aggregate_tps",
        "success_rate",
        "error_count",
    ]
    summary: Dict[str, Any] = {"rounds": rounds}
    for key in keys:
        values = [float(r[key]) for r in rounds]
        summary[f"{key}_mean"] = round(mean(values), 3)
        summary[f"{key}_std"] = round(pstdev(values), 3) if len(values) > 1 else 0.0
    vm_rows = [r.get("vm_stat_summary", {}) for r in rounds if r.get("vm_stat_summary", {}).get("available")]
    if vm_rows:
        summary["vm_stat_summary"] = {
            "available": True,
            "samples_mean": round(mean(float(v["samples"]) for v in vm_rows), 3),
            "peak_total_ops_max": max(int(v["peak_total_ops"]) for v in vm_rows),
            "mean_total_ops_mean": round(mean(float(v["mean_total_ops"]) for v in vm_rows), 3),
            "peak_pageouts_max": max(int(v["peak_pageouts"]) for v in vm_rows),
            "peak_swapouts_max": max(int(v["peak_swapouts"]) for v in vm_rows),
        }
    return summary


def run_mode(
    mode_name: str,
    use_dynamic: bool,
    rounds: int,
    concurrency_levels: List[int],
    worker_payload: Dict[str, Any],
    vmstat_dir: Path,
) -> Dict[str, Any]:
    output: Dict[str, Any] = {}
    for concurrency in concurrency_levels:
        round_rows: List[Dict[str, Any]] = []
        for round_id in range(1, rounds + 1):
            started = time.perf_counter()
            successes: List[Dict[str, Any]] = []
            failures: List[str] = []
            trace_file = vmstat_dir / f"{mode_name}_n{concurrency}_r{round_id}.csv"
            vmstat_proc = start_vmstat_trace(trace_file)
            with ProcessPoolExecutor(max_workers=concurrency) as executor:
                futures = [
                    executor.submit(worker_task, {**worker_payload, "use_dynamic": use_dynamic})
                    for _ in range(concurrency)
                ]
                for future in as_completed(futures):
                    result = future.result()
                    if result.get("success"):
                        successes.append(result)
                    else:
                        failures.append(result.get("error", "unknown error"))
            stop_vmstat_trace(vmstat_proc)
            wall_time_sec = time.perf_counter() - started
            if not successes:
                round_rows.append(
                    {
                        "mode": mode_name,
                        "concurrency": concurrency,
                        "round": round_id,
                        "successes": 0,
                        "wall_time_sec": round(wall_time_sec, 3),
                        "failures": failures,
                        "success_rate": 0.0,
                        "error_count": len(failures),
                        "vm_stat_summary": summarize_vmstat(trace_file),
                    }
                )
                continue
            round_summary = summarize_round(mode_name, concurrency, round_id, successes, wall_time_sec)
            if failures:
                round_summary["failures"] = failures
            round_summary["success_rate"] = round(len(successes) / concurrency, 3)
            round_summary["error_count"] = len(failures)
            round_summary["vm_stat_summary"] = summarize_vmstat(trace_file)
            round_rows.append(round_summary)
        successful_rounds = [r for r in round_rows if r.get("successes", 0) > 0]
        output[f"N={concurrency}"] = {
            "mode": mode_name,
            "concurrency": concurrency,
            "round_count": rounds,
            "successful_rounds": len(successful_rounds),
            "summary": aggregate_mode(successful_rounds) if successful_rounds else {},
            "rounds": round_rows,
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repeated concurrency/tail-latency experiments for the paper track.")
    parser.add_argument("--model-path", default=DEFAULT_MODEL)
    parser.add_argument("--index-path", default=str(ROOT_DIR / "models" / "vector_indices" / "turbo_index.json"))
    parser.add_argument("--out-file", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--concurrency-levels", default="2,4")
    parser.add_argument("--n-ctx", type=int, default=2048)
    parser.add_argument("--top-k", type=int, default=15)
    parser.add_argument("--num-docs", type=int, default=25)
    parser.add_argument("--doc-repeat", type=int, default=2)
    parser.add_argument("--query", default="Explain the hardware bandwidth limitations when processing large contexts in local LLMs.")
    parser.add_argument("--vmstat-dir", default=str(DEFAULT_VMSTAT_DIR))
    args = parser.parse_args()

    concurrency_levels = [int(x.strip()) for x in args.concurrency_levels.split(",") if x.strip()]
    vmstat_dir = Path(args.vmstat_dir)
    worker_payload = {
        "model_path": args.model_path,
        "index_path": args.index_path,
        "n_ctx": args.n_ctx,
        "top_k": args.top_k,
        "query": args.query,
        "mock_docs": build_mock_docs(args.num_docs, args.doc_repeat),
    }

    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/benchmarking/paper_concurrency_suite.py",
        "output_schema_version": "1.0",
        "experiment": "E3_concurrency_tail_latency",
        "config": {
            "model_path": args.model_path,
            "index_path": args.index_path,
            "rounds": args.rounds,
            "concurrency_levels": concurrency_levels,
            "n_ctx": args.n_ctx,
            "top_k": args.top_k,
            "num_docs": args.num_docs,
            "doc_repeat": args.doc_repeat,
            "query": args.query,
            "vmstat_dir": str(vmstat_dir),
        },
        "modes": {
            "full_context": run_mode("full_context", False, args.rounds, concurrency_levels, worker_payload, vmstat_dir),
            "optimized_path": run_mode("optimized_path", True, args.rounds, concurrency_levels, worker_payload, vmstat_dir),
        },
    }

    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    print(f"SAVED: {out_path}")


if __name__ == "__main__":
    main()

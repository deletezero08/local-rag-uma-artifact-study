#!/usr/bin/env python3
"""Run a paper-track NIAH depth sweep with repeated trials."""

from __future__ import annotations

import argparse
import json
import random
import string
import sys
import time
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.rag_pipeline import MemoraRAGPipeline


DEFAULT_MODEL = str(ROOT_DIR / "models" / "Llama-3-8B-Instruct.Q4_K_M.gguf")
DEFAULT_OUTPUT = ROOT_DIR / "results" / "evaluation" / "niah_depth_expanded.json"
NEEDLE = "The anti-gravity engine activation code is NEBULA-VAULT-2026-SOTA-PRO."
QUERY = "What is the anti-gravity engine activation code?"


def build_haystack(target_chars: int, rng: random.Random) -> List[str]:
    topics = [
        "Unified memory platforms can collapse under paging-heavy prompt execution.",
        "Retrieval compression reduces footprint but may perturb ranking fidelity.",
        "Prompt budgeting can reduce prefill without materially changing decode throughput.",
        "Tail latency matters more than mean latency under concurrent local serving.",
        "Backend choice determines whether a local deployment is interactive at all.",
        "Context pruning must preserve anchor evidence to avoid support drift.",
    ]
    chunks: List[str] = []
    total = 0
    while total < target_chars:
        salt = "".join(rng.choices(string.ascii_lowercase, k=8))
        chunk = f"{rng.choice(topics)} Noise tag: {salt}."
        chunks.append(chunk)
        total += len(chunk)
    return chunks


def classify_failure(answer: str) -> str:
    if "NEBULA-VAULT-2026-SOTA-PRO" in answer:
        return "ok"
    if "NEBULA-VAULT-2026" in answer:
        return "partial_needle"
    if not answer.strip():
        return "empty_answer"
    return "needle_missed"


def summarize_depth(depth: int, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    latencies = [row["latency_sec"] for row in rows]
    success_values = [1.0 if row["success"] else 0.0 for row in rows]
    strategies = sorted({row["strategy"] for row in rows})
    failure_counts: Dict[str, int] = {}
    for row in rows:
        failure_counts[row["failure_type"]] = failure_counts.get(row["failure_type"], 0) + 1
    return {
        "depth_percent": depth,
        "rounds": len(rows),
        "success_rate": round(mean(success_values), 3) if rows else 0.0,
        "latency_sec_mean": round(mean(latencies), 3) if rows else 0.0,
        "latency_sec_std": round(pstdev(latencies), 3) if len(rows) > 1 else 0.0,
        "strategies_used": strategies,
        "failure_counts": failure_counts,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an expanded NIAH depth sweep for the paper track.")
    parser.add_argument("--model-path", default=DEFAULT_MODEL)
    parser.add_argument("--index-path", default=str(ROOT_DIR / "models" / "vector_indices" / "turbo_index.json"))
    parser.add_argument("--out-file", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--depths", default="0,25,50,75,90,95,99")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--haystack-chars", type=int, default=120000)
    parser.add_argument("--n-ctx", type=int, default=8192)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    depths = [int(x.strip()) for x in args.depths.split(",") if x.strip()]
    pipeline = MemoraRAGPipeline(
        model_path=args.model_path,
        index_path=args.index_path,
        n_ctx=args.n_ctx,
    )
    rng = random.Random(args.seed)

    summaries = []
    for depth in depths:
        rows = []
        for round_idx in range(1, args.rounds + 1):
            haystack = build_haystack(args.haystack_chars, rng)
            insert_idx = min(len(haystack), int(len(haystack) * (depth / 100.0)))
            haystack.insert(insert_idx, NEEDLE)

            start = time.perf_counter()
            result = pipeline.run(QUERY, mock_docs=haystack, use_dynamic=True)
            latency_sec = time.perf_counter() - start
            answer = result.get("answer", "")
            failure_type = classify_failure(answer)
            rows.append(
                {
                    "round": round_idx,
                    "depth_percent": depth,
                    "success": failure_type == "ok",
                    "failure_type": failure_type,
                    "latency_sec": round(latency_sec, 3),
                    "strategy": result.get("pruning_strategy", ""),
                    "answer_preview": answer[:220],
                }
            )
        summaries.append(summarize_depth(depth, rows))

    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/evaluation/paper_niah_depth_expanded.py",
        "output_schema_version": "1.0",
        "experiment": "E6_niah_depth_expanded",
        "config": {
            "model_path": args.model_path,
            "index_path": args.index_path,
            "depths": depths,
            "rounds": args.rounds,
            "haystack_chars": args.haystack_chars,
            "n_ctx": args.n_ctx,
            "seed": args.seed,
        },
        "rows": summaries,
    }

    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"SAVED: {out_path}")


if __name__ == "__main__":
    main()

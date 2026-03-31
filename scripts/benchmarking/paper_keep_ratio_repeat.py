#!/usr/bin/env python3
import argparse
import json
import sys
import time
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List

import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.rag_pipeline import MemoraRAGPipeline


DEFAULT_MODEL = str(ROOT_DIR / "models" / "Llama-3-8B-Instruct.Q4_K_M.gguf")
DEFAULT_OUTPUT = ROOT_DIR / "results" / "tuning" / "keep_ratio_repeat_scan.json"


def build_mock_docs(num_docs: int, repeat: int) -> List[str]:
    return [
        (
            f"Evidence block {i}: Shared-memory local RAG must budget retrieval state, prompt length, "
            f"and decode pressure together. Cliff-aware pruning can reduce prefill without materially changing "
            f"decode throughput when the retained context still preserves anchors. " * repeat
        )
        for i in range(num_docs)
    ]


def run_once(
    pipeline: MemoraRAGPipeline,
    query: str,
    keep_ratio: float,
    mock_docs: List[str],
    top_k: int,
) -> Dict[str, Any]:
    pipeline.compressor.keep_ratio = keep_ratio
    result = pipeline.run(query, top_k=top_k, mock_docs=mock_docs, use_dynamic=False)
    waterfall = result["waterfall"]
    decode_ms = float(waterfall.get("llm_decode_ms", 0.0))
    generated_tokens = int(result.get("generated_tokens", 0))
    decode_tps = generated_tokens / (decode_ms / 1000.0) if decode_ms > 0 else 0.0
    return {
        "keep_ratio": keep_ratio,
        "retrieval_ms": float(waterfall.get("retrieval_ms", 0.0)),
        "scoring_ms": float(waterfall.get("scoring_ms", 0.0)),
        "pruning_ms": float(waterfall.get("pruning_ms", 0.0)),
        "ttft_ms": float(waterfall.get("llm_prefill_ms", 0.0)),
        "decode_tps": decode_tps,
        "total_e2e_ms": float(waterfall.get("total_pipeline_ms", 0.0)),
        "generated_tokens": generated_tokens,
        "original_len": int(result.get("original_len", 0)),
        "compressed_len": int(result.get("compressed_len", 0)),
        "strategy": result.get("pruning_strategy", ""),
    }


def summarize(keep_ratio: float, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    metrics = [
        "retrieval_ms",
        "scoring_ms",
        "pruning_ms",
        "ttft_ms",
        "decode_tps",
        "total_e2e_ms",
        "generated_tokens",
        "original_len",
        "compressed_len",
    ]
    summary: Dict[str, Any] = {
        "keep_ratio": keep_ratio,
        "runs": rows,
        "selected_candidate": False,
        "strategies_used": sorted({r["strategy"] for r in rows}),
    }
    for metric in metrics:
        values = [float(r[metric]) for r in rows]
        summary[f"{metric}_mean"] = round(mean(values), 3)
        summary[f"{metric}_std"] = round(pstdev(values), 3) if len(values) > 1 else 0.0
        if metric in {"ttft_ms", "total_e2e_ms"}:
            summary[f"{metric}_p95"] = round(float(np.percentile(values, 95)), 3)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repeated keep-ratio scans for the paper track.")
    parser.add_argument("--model-path", default=DEFAULT_MODEL)
    parser.add_argument("--index-path", default=str(ROOT_DIR / "models" / "vector_indices" / "turbo_index.json"))
    parser.add_argument("--out-file", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--ratios", default="1.0,0.8,0.6,0.4,0.2")
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--n-ctx", type=int, default=4096)
    parser.add_argument("--top-k", type=int, default=15)
    parser.add_argument("--num-docs", type=int, default=25)
    parser.add_argument("--doc-repeat", type=int, default=2)
    parser.add_argument("--query", default="What execution bottlenecks dominate local RAG on constrained unified-memory hardware?")
    args = parser.parse_args()

    ratios = [float(x.strip()) for x in args.ratios.split(",") if x.strip()]
    pipeline = MemoraRAGPipeline(
        model_path=args.model_path,
        index_path=args.index_path,
        n_ctx=args.n_ctx,
    )
    mock_docs = build_mock_docs(args.num_docs, args.doc_repeat)

    rows_by_ratio: List[Dict[str, Any]] = []
    for ratio in ratios:
        rows = []
        for _ in range(args.rounds):
            rows.append(run_once(pipeline, args.query, ratio, mock_docs, args.top_k))
        rows_by_ratio.append(summarize(ratio, rows))

    best = min(rows_by_ratio, key=lambda row: row["ttft_ms_mean"]) if rows_by_ratio else None
    if best is not None:
        best["selected_candidate"] = True

    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/benchmarking/paper_keep_ratio_repeat.py",
        "output_schema_version": "1.0",
        "experiment": "E1_keep_ratio_repeat",
        "config": {
            "model_path": args.model_path,
            "index_path": args.index_path,
            "ratios": ratios,
            "rounds": args.rounds,
            "n_ctx": args.n_ctx,
            "top_k": args.top_k,
            "num_docs": args.num_docs,
            "doc_repeat": args.doc_repeat,
            "query": args.query,
        },
        "rows": rows_by_ratio,
    }

    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    print(f"SAVED: {out_path}")


if __name__ == "__main__":
    main()

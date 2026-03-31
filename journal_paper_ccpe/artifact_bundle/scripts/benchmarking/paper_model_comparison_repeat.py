#!/usr/bin/env python3
import argparse
import json
import math
import sys
import time
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List

import numpy as np
from llama_cpp import Llama


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT_DIR / "results" / "evaluation" / "model_comparison_repeated.json"
DEFAULT_LLAMA = ROOT_DIR / "models" / "Llama-3-8B-Instruct.Q4_K_M.gguf"
DEFAULT_FALCON = ROOT_DIR / "models" / "falcon-7b-multihop-q4_k_m.gguf"
DEFAULT_MPS = ROOT_DIR / "results" / "evaluation" / "v2_performance_final.json"


def run_stream_once(llm: Llama, prompt: str, max_tokens: int, stop_tokens: List[str]) -> Dict[str, Any]:
    started = time.perf_counter_ns()
    stream = llm(prompt, max_tokens=max_tokens, stream=True, stop=stop_tokens)

    ttft_ms = None
    parts: List[str] = []
    generated_tokens = 0
    for chunk in stream:
        text = chunk["choices"][0]["text"]
        if ttft_ms is None and text.strip():
            ttft_ms = (time.perf_counter_ns() - started) / 1_000_000
        parts.append(text)
        generated_tokens += 1

    total_ms = (time.perf_counter_ns() - started) / 1_000_000
    decode_ms = total_ms - (ttft_ms if ttft_ms is not None else total_ms)
    tps = generated_tokens / (decode_ms / 1000.0) if decode_ms > 0 else 0.0
    return {
        "ttft_ms": round(float(ttft_ms if ttft_ms is not None else total_ms), 3),
        "total_time_s": round(total_ms / 1000.0, 3),
        "tps": round(float(tps), 3),
        "generated_tokens": int(generated_tokens),
        "answer_preview": "".join(parts).strip()[:200],
    }


def summarize_runs(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    metrics = ["ttft_ms", "tps", "total_time_s"]
    payload: Dict[str, Any] = {"rounds": len(runs), "runs": runs}
    for metric in metrics:
        values = [float(row[metric]) for row in runs]
        std = pstdev(values) if len(values) > 1 else 0.0
        ci95 = 1.96 * std / math.sqrt(len(values)) if values else 0.0
        payload[f"{metric}_mean"] = round(mean(values), 3)
        payload[f"{metric}_std"] = round(std, 3)
        payload[f"{metric}_ci95"] = round(ci95, 3)
        payload[f"{metric}_p95"] = round(float(np.percentile(values, 95)), 3) if values else 0.0
    return payload


def benchmark_gguf(
    label: str,
    model_path: Path,
    rounds: int,
    n_ctx: int,
    max_tokens: int,
    prompt: str,
    stop_tokens: List[str],
) -> Dict[str, Any]:
    llm = Llama(model_path=str(model_path), n_gpu_layers=-1, n_ctx=n_ctx, verbose=False)
    runs = [run_stream_once(llm, prompt, max_tokens, stop_tokens) for _ in range(rounds)]
    payload = summarize_runs(runs)
    payload.update(
        {
            "label": label,
            "backend": "GGUF / llama.cpp",
            "model_path": str(model_path),
            "evidence_class": "repeated_measurement",
        }
    )
    return payload


def import_mps_observation(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text("utf-8"))
    row = data["scaling"]["16"]
    run = {
        "ttft_ms": round(float(row["ttft"]) * 1000.0, 3),
        "tps": round(float(row["tps"]), 3),
        "total_time_s": round(float(row["total_time"]), 3),
        "generated_tokens": int(float(row.get("tokens", 0.0))),
        "answer_preview": "Imported from cautionary single-run MPS baseline.",
    }
    payload = summarize_runs([run])
    payload.update(
        {
            "label": "Falcon-7B on MPS",
            "backend": "transformers + MPS",
            "model_path": str(path),
            "evidence_class": "cautionary_single_run_import",
            "note": "Imported from existing negative-result smoke baseline because the original MPS path is operationally impractical in the current paper track.",
        }
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Repeated backend/model comparison for the paper track.")
    parser.add_argument("--out-file", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--n-ctx", type=int, default=4096)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--prompt", default="Explain in two concise sentences why local RAG on constrained unified-memory hardware requires joint tuning of retrieval, prompt budget, and generation.")
    parser.add_argument("--falcon-model", default=str(DEFAULT_FALCON))
    parser.add_argument("--llama-model", default=str(DEFAULT_LLAMA))
    parser.add_argument("--mps-source", default=str(DEFAULT_MPS))
    args = parser.parse_args()

    stop_tokens = ["<|eot_id|>"]
    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/benchmarking/paper_model_comparison_repeat.py",
        "output_schema_version": "1.0",
        "experiment": "E1_backend_repeated",
        "config": {
            "rounds": args.rounds,
            "n_ctx": args.n_ctx,
            "max_tokens": args.max_tokens,
            "prompt": args.prompt,
        },
        "configs": [
            import_mps_observation(Path(args.mps_source)),
            benchmark_gguf("Falcon-7B-Q + GGUF", Path(args.falcon_model), args.rounds, args.n_ctx, args.max_tokens, args.prompt, stop_tokens),
            benchmark_gguf("Llama-3-8B-Q + GGUF", Path(args.llama_model), args.rounds, args.n_ctx, args.max_tokens, args.prompt, stop_tokens),
        ],
    }

    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    print(f"SAVED: {out_path}")


if __name__ == "__main__":
    main()

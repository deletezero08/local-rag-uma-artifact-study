#!/usr/bin/env python3
import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from langchain_ollama import OllamaLLM


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.rag_pipeline import MemoraRAGPipeline


OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = str(ROOT_DIR / "models" / "Llama-3-8B-Instruct.Q4_K_M.gguf")
DEFAULT_INDEX = str(ROOT_DIR / "models" / "vector_indices" / "turbo_index.json")
DEFAULT_CASES = ROOT_DIR / "data" / "eval" / "test_cases_test40.json"
DOCS_ROOT = ROOT_DIR / "docs"


class FP32ChunkRetriever:
    def __init__(self, chunks: List[str], metadatas: List[Dict[str, Any]], embeddings: np.ndarray, model: Any):
        self.chunks = chunks
        self.metadatas = metadatas
        self.embeddings = embeddings.astype(np.float32)
        self.model = model
        self.dim = int(self.embeddings.shape[1]) if self.embeddings.size else 0

    @classmethod
    def from_turbo_retriever(cls, turbo_retriever: Any) -> "FP32ChunkRetriever":
        chunks = list(turbo_retriever.chunks)
        metadatas = list(turbo_retriever.metadatas)
        model = turbo_retriever.model
        embeddings = np.array(model.encode(chunks, normalize_embeddings=True), dtype=np.float32)
        return cls(chunks=chunks, metadatas=metadatas, embeddings=embeddings, model=model)

    def search(self, query: str, top_k: int = 10) -> Tuple[List[Dict[str, Any]], float]:
        started = time.perf_counter_ns()
        query_emb = np.array(self.model.encode([query], normalize_embeddings=True)[0], dtype=np.float32)
        scores = self.embeddings @ query_emb
        top_indices = np.argsort(scores)[-top_k:][::-1]
        results = []
        for idx in top_indices:
            results.append(
                {
                    "content": self.chunks[int(idx)],
                    "metadata": self.metadatas[int(idx)],
                    "score": float(scores[int(idx)]),
                }
            )
        latency_ms = (time.perf_counter_ns() - started) / 1_000_000
        return results, latency_ms


def load_cases(path: Path, sample_size: int) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text("utf-8"))
    rows = []
    for item in data[:sample_size]:
        rows.append(
            {
                "id": item.get("id"),
                "question": item.get("question", ""),
                "ground_truth": item.get("ground_truth_candidate", item.get("ground_truth", "")),
                "source_docs": item.get("source_docs", []),
            }
        )
    return rows


def normalize_doc_path(raw_path: str) -> str:
    try:
        return str(Path(raw_path).resolve().relative_to(DOCS_ROOT.resolve())).replace("\\", "/")
    except Exception:
        path = Path(raw_path)
        parts = path.parts
        if "docs" in parts:
            idx = parts.index("docs")
            return "/".join(parts[idx + 1 :])
        if len(parts) >= 2:
            return "/".join(parts[-2:])
        return path.name


def build_prompt(question: str, answer: str, context: str, ground_truth: str, strict_mode: bool) -> str:
    rule = "只输出 JSON，不要解释。" if strict_mode else "输出 JSON。"
    return f"""你是严格的评估裁判。请根据参考资料评估回答质量。
参考资料: {context[:3600]}
问题: {question}
标准答案: {ground_truth[:1600]}
系统回答: {answer[:2200]}
请给出 0-10 分的 JSON：{{"faithfulness": x, "relevance": y}}
{rule}"""


def extract_scores(raw_text: str) -> Dict[str, float]:
    raw_text = (raw_text or "").strip()
    if "```" in raw_text:
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    import re

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    payload = json.loads(match.group() if match else raw_text)
    return {
        "faithfulness": float(payload.get("faithfulness", 0.0)),
        "relevance": float(payload.get("relevance", 0.0)),
    }


def judge_answer(judge: OllamaLLM, question: str, answer: str, context: str, ground_truth: str, strict_mode: bool) -> Dict[str, float]:
    raw = judge.invoke(build_prompt(question, answer, context, ground_truth, strict_mode))
    text = raw.content if hasattr(raw, "content") else str(raw)
    return extract_scores(text)


def classify_error(row: Dict[str, Any], threshold: float) -> str:
    if row.get("recall_hit_at_k", 0.0) < 1.0:
        return "retrieval_miss"
    if row.get("faith_m", 0.0) < threshold:
        return "factual_drift"
    if row.get("rel_m", 0.0) < threshold:
        return "low_relevance"
    return "ok"


def summarize_mode(rows: List[Dict[str, Any]], name: str, index_bytes: int, threshold: float) -> Dict[str, Any]:
    def avg(key: str) -> float:
        return round(statistics.fmean(float(row[key]) for row in rows), 3) if rows else 0.0

    return {
        "name": name,
        "n": len(rows),
        "index_footprint_bytes": int(index_bytes),
        "retrieval_latency_mean_ms": avg("retrieval_ms"),
        "ttft_mean_ms": avg("ttft_ms"),
        "total_mean_ms": avg("total_ms"),
        "recall_at_k_mean": avg("recall_at_k"),
        "hit_rate_at_k_mean": avg("recall_hit_at_k"),
        "faithfulness_mean_judge_a": avg("faith_a"),
        "relevance_mean_judge_a": avg("rel_a"),
        "faithfulness_mean_judge_b": avg("faith_b"),
        "relevance_mean_judge_b": avg("rel_b"),
        "faithfulness_mean_merged": avg("faith_m"),
        "relevance_mean_merged": avg("rel_m"),
        "judge_gap_faithfulness_mean": avg("gap_f"),
        "judge_gap_relevance_mean": avg("gap_r"),
        "answer_error_rate": round(
            statistics.fmean(1.0 if row["auto_error_category"] != "ok" else 0.0 for row in rows),
            3,
        )
        if rows
        else 0.0,
        "judge_agreement_rate_gap_le_1": round(
            statistics.fmean(1.0 if row["gap_f"] <= 1.0 and row["gap_r"] <= 1.0 else 0.0 for row in rows),
            3,
        )
        if rows
        else 0.0,
        "quality_threshold": threshold,
    }


def write_audit_csv(path: Path, rows_by_mode: Dict[str, List[Dict[str, Any]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "mode",
        "id",
        "question",
        "source_docs",
        "retrieved_doc_paths",
        "recall_at_k",
        "recall_hit_at_k",
        "retrieval_ms",
        "ttft_ms",
        "total_ms",
        "faith_m",
        "rel_m",
        "auto_error_category",
        "answer",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for mode, rows in rows_by_mode.items():
            for row in rows:
                writer.writerow(
                    {
                        "mode": mode,
                        "id": row["id"],
                        "question": row["question"],
                        "source_docs": ";".join(row["source_docs"]),
                        "retrieved_doc_paths": ";".join(row["retrieved_doc_paths"]),
                        "recall_at_k": row["recall_at_k"],
                        "recall_hit_at_k": row["recall_hit_at_k"],
                        "retrieval_ms": row["retrieval_ms"],
                        "ttft_ms": row["ttft_ms"],
                        "total_ms": row["total_ms"],
                        "faith_m": row.get("faith_m", ""),
                        "rel_m": row.get("rel_m", ""),
                        "auto_error_category": row.get("auto_error_category", ""),
                        "answer": row["answer"],
                    }
                )


def run_mode(
    pipeline: MemoraRAGPipeline,
    cases: List[Dict[str, Any]],
    label: str,
    top_k: int,
    keep_ratio: float,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    total = len(cases)
    pipeline.compressor.keep_ratio = keep_ratio
    for idx, case in enumerate(cases, start=1):
        print(f"[{label}] generate {idx}/{total} {case['id']}")
        started = time.time()
        result = pipeline.run(case["question"], top_k=top_k, use_dynamic=False)
        retrieved_doc_paths = [
            normalize_doc_path(item.get("metadata", {}).get("path", ""))
            for item in result.get("retrieved_results", [])
        ]
        gold_docs = [doc.replace("\\", "/") for doc in case.get("source_docs", [])]
        overlap = sorted(set(gold_docs) & set(retrieved_doc_paths))
        recall_at_k = round(len(overlap) / len(gold_docs), 3) if gold_docs else 0.0
        rows.append(
            {
                "id": case["id"],
                "question": case["question"],
                "ground_truth": case["ground_truth"],
                "source_docs": gold_docs,
                "answer": result["answer"],
                "context": result["compressed_context"],
                "latency": round(time.time() - started, 3),
                "retrieval_ms": round(float(result["waterfall"].get("retrieval_ms", 0.0)), 3),
                "ttft_ms": round(float(result["waterfall"].get("llm_prefill_ms", 0.0)), 3),
                "total_ms": round(float(result["waterfall"].get("total_pipeline_ms", 0.0)), 3),
                "top_k": top_k,
                "keep_ratio": keep_ratio,
                "use_dynamic": False,
                "strategy": result.get("pruning_strategy", "unknown"),
                "retrieved_doc_paths": retrieved_doc_paths,
                "recall_at_k": recall_at_k,
                "recall_hit_at_k": 1.0 if overlap else 0.0,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="TurboQuant on/off end-to-end quality ablation for the paper track.")
    parser.add_argument("--cases-file", default=str(DEFAULT_CASES))
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--model-path", default=DEFAULT_MODEL)
    parser.add_argument("--index-path", default=DEFAULT_INDEX)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--keep-ratio", type=float, default=0.6)
    parser.add_argument("--judge-a-model", default="qwen3:8b")
    parser.add_argument("--judge-b-model", default="deepseek-r1:8b")
    parser.add_argument("--error-threshold", type=float, default=5.0)
    parser.add_argument("--out-file", default=str(ROOT_DIR / "results" / "evaluation" / "turboquant_e2e_quality_ablation.json"))
    parser.add_argument("--audit-file", default=str(ROOT_DIR / "results" / "evaluation" / "turboquant_manual_audit.csv"))
    parser.add_argument("--checkpoint-file", default="")
    args = parser.parse_args()

    cases = load_cases(Path(args.cases_file), args.sample_size)
    out_path = Path(args.out_file)
    audit_path = Path(args.audit_file)
    checkpoint_path = Path(args.checkpoint_file) if args.checkpoint_file else out_path.with_suffix(".checkpoint.json")

    state: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/evaluation/paper_turboquant_e2e_ablation.py",
        "output_schema_version": "1.0",
        "cases_file": str(Path(args.cases_file)),
        "sample_size": len(cases),
        "fp32_off_rows": [],
        "turboquant_on_rows": [],
    }
    if checkpoint_path.exists():
        try:
            loaded = json.loads(checkpoint_path.read_text("utf-8"))
            if loaded.get("cases_file") == state["cases_file"] and loaded.get("sample_size") == state["sample_size"]:
                state.update(loaded)
                print(f"RESUME: {checkpoint_path}")
        except Exception:
            pass

    def save_checkpoint() -> None:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(json.dumps(state, ensure_ascii=False, separators=(",", ":")), "utf-8")

    pipeline = MemoraRAGPipeline(model_path=args.model_path, index_path=args.index_path, n_ctx=4096)
    turbo_retriever = pipeline.retriever
    fp32_retriever = FP32ChunkRetriever.from_turbo_retriever(turbo_retriever)

    turbo_index = turbo_retriever.index_data
    turbo_index_bytes = int(
        np.array(turbo_index["D"], dtype=np.float32).nbytes
        + np.array(turbo_index["W_qjl"], dtype=np.float32).nbytes
        + np.array(turbo_index["codes"], dtype=np.int8).nbytes
        + np.array(turbo_index["qjl"], dtype=np.int8).nbytes
        + np.array(turbo_index["scale_qjl"], dtype=np.float32).nbytes
        + np.array(turbo_index["norms"], dtype=np.float32).nbytes
    )
    fp32_index_bytes = int(fp32_retriever.embeddings.nbytes)

    fp32_off_rows = state.get("fp32_off_rows", [])
    if not fp32_off_rows:
        pipeline.retriever = fp32_retriever
        fp32_off_rows = run_mode(pipeline, cases, label="fp32_off", top_k=args.top_k, keep_ratio=args.keep_ratio)
        state["fp32_off_rows"] = fp32_off_rows
        save_checkpoint()

    turboquant_on_rows = state.get("turboquant_on_rows", [])
    if not turboquant_on_rows:
        pipeline.retriever = turbo_retriever
        turboquant_on_rows = run_mode(pipeline, cases, label="turboquant_on", top_k=args.top_k, keep_ratio=args.keep_ratio)
        state["turboquant_on_rows"] = turboquant_on_rows
        save_checkpoint()

    judge_a = OllamaLLM(model=args.judge_a_model, temperature=0.0, base_url=OLLAMA_HOST)
    judge_b = OllamaLLM(model=args.judge_b_model, temperature=0.0, base_url=OLLAMA_HOST)

    all_rows = [("fp32_off", row) for row in fp32_off_rows] + [("turboquant_on", row) for row in turboquant_on_rows]
    total_rows = len(all_rows)
    for idx, (label, row) in enumerate(all_rows, start=1):
        if "judge_a" not in row:
            print(f"[judge_a] {idx}/{total_rows} {label} {row['id']}")
            row["judge_a"] = judge_answer(judge_a, row["question"], row["answer"], row["context"], row["ground_truth"], True)
        if "judge_b" not in row:
            print(f"[judge_b] {idx}/{total_rows} {label} {row['id']}")
            row["judge_b"] = judge_answer(judge_b, row["question"], row["answer"], row["context"], row["ground_truth"], False)
        row["faith_a"] = round(row["judge_a"]["faithfulness"], 3)
        row["rel_a"] = round(row["judge_a"]["relevance"], 3)
        row["faith_b"] = round(row["judge_b"]["faithfulness"], 3)
        row["rel_b"] = round(row["judge_b"]["relevance"], 3)
        row["faith_m"] = round((row["faith_a"] + row["faith_b"]) / 2.0, 3)
        row["rel_m"] = round((row["rel_a"] + row["rel_b"]) / 2.0, 3)
        row["gap_f"] = round(abs(row["faith_a"] - row["faith_b"]), 3)
        row["gap_r"] = round(abs(row["rel_a"] - row["rel_b"]), 3)
        row["auto_error_category"] = classify_error(row, args.error_threshold)
        save_checkpoint()

    fp32_off = summarize_mode(fp32_off_rows, "fp32_off", fp32_index_bytes, args.error_threshold)
    turboquant_on = summarize_mode(turboquant_on_rows, "turboquant_on", turbo_index_bytes, args.error_threshold)

    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/evaluation/paper_turboquant_e2e_ablation.py",
        "output_schema_version": "1.0",
        "cases_file": str(Path(args.cases_file)),
        "sample_size": len(cases),
        "top_k": args.top_k,
        "keep_ratio": args.keep_ratio,
        "error_threshold": args.error_threshold,
        "fp32_off": fp32_off,
        "turboquant_on": turboquant_on,
        "comparison": {
            "retrieval_latency_delta_ms": round(turboquant_on["retrieval_latency_mean_ms"] - fp32_off["retrieval_latency_mean_ms"], 3),
            "ttft_delta_ms": round(turboquant_on["ttft_mean_ms"] - fp32_off["ttft_mean_ms"], 3),
            "total_latency_delta_ms": round(turboquant_on["total_mean_ms"] - fp32_off["total_mean_ms"], 3),
            "recall_at_k_delta": round(turboquant_on["recall_at_k_mean"] - fp32_off["recall_at_k_mean"], 3),
            "faithfulness_delta": round(turboquant_on["faithfulness_mean_merged"] - fp32_off["faithfulness_mean_merged"], 3),
            "relevance_delta": round(turboquant_on["relevance_mean_merged"] - fp32_off["relevance_mean_merged"], 3),
            "answer_error_rate_delta": round(turboquant_on["answer_error_rate"] - fp32_off["answer_error_rate"], 3),
        },
        "fp32_off_rows": fp32_off_rows,
        "turboquant_on_rows": turboquant_on_rows,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    write_audit_csv(audit_path, {"fp32_off": fp32_off_rows, "turboquant_on": turboquant_on_rows})
    if checkpoint_path.exists():
        checkpoint_path.unlink()
    print(f"SAVED: {out_path}")
    print(f"AUDIT: {audit_path}")


if __name__ == "__main__":
    main()

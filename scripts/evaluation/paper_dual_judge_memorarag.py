#!/usr/bin/env python3
import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from langchain_ollama import OllamaLLM


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.rag_pipeline import MemoraRAGPipeline


OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = str(ROOT_DIR / "models" / "Llama-3-8B-Instruct.Q4_K_M.gguf")
DEFAULT_INDEX = str(ROOT_DIR / "models" / "vector_indices" / "turbo_index.json")
DEFAULT_CASES = ROOT_DIR / "data" / "eval" / "test_cases_test40.json"


def load_cases(path: Path, sample_size: int) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text("utf-8"))
    rows = []
    for item in data[:sample_size]:
        rows.append(
            {
                "id": item.get("id"),
                "question": item.get("question", ""),
                "ground_truth": item.get("ground_truth_candidate", item.get("ground_truth", "")),
            }
        )
    return rows


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


def run_mode(
    pipeline: MemoraRAGPipeline,
    cases: List[Dict[str, Any]],
    top_k: int,
    use_dynamic: bool,
    label: str,
) -> List[Dict[str, Any]]:
    rows = []
    if not use_dynamic:
        pipeline.compressor.keep_ratio = 1.0
    total = len(cases)
    for idx, case in enumerate(cases, start=1):
        print(f"[{label}] generate {idx}/{total} {case['id']}")
        started = time.time()
        result = pipeline.run(case["question"], top_k=top_k, use_dynamic=use_dynamic)
        rows.append(
            {
                "id": case["id"],
                "question": case["question"],
                "ground_truth": case["ground_truth"],
                "answer": result["answer"],
                "context": result["compressed_context"] if use_dynamic else result["full_context"],
                "latency": round(time.time() - started, 3),
                "top_k": top_k,
                "use_dynamic": use_dynamic,
                "ttft_ms": round(float(result["waterfall"].get("llm_prefill_ms", 0.0)), 3),
                "total_ms": round(float(result["waterfall"].get("total_pipeline_ms", 0.0)), 3),
                "strategy": result.get("pruning_strategy", "unknown"),
            }
        )
    return rows


def aggregate(rows: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
    def avg(key: str) -> float:
        return round(statistics.fmean(float(row[key]) for row in rows), 3) if rows else 0.0

    return {
        "name": name,
        "n": len(rows),
        "latency_mean": avg("latency"),
        "ttft_mean_ms": avg("ttft_ms"),
        "total_mean_ms": avg("total_ms"),
        "faithfulness_mean_judge_a": avg("faith_a"),
        "relevance_mean_judge_a": avg("rel_a"),
        "faithfulness_mean_judge_b": avg("faith_b"),
        "relevance_mean_judge_b": avg("rel_b"),
        "faithfulness_mean_merged": avg("faith_m"),
        "relevance_mean_merged": avg("rel_m"),
        "judge_gap_faithfulness_mean": avg("gap_f"),
        "judge_gap_relevance_mean": avg("gap_r"),
        "judge_agreement_rate_gap_le_1": round(
            statistics.fmean(1.0 if row["gap_f"] <= 1.0 and row["gap_r"] <= 1.0 else 0.0 for row in rows),
            3,
        )
        if rows
        else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper-track dual-judge quality runner for MemoraRAG pipeline.")
    parser.add_argument("--cases-file", default=str(DEFAULT_CASES))
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--model-path", default=DEFAULT_MODEL)
    parser.add_argument("--index-path", default=DEFAULT_INDEX)
    parser.add_argument("--baseline-top-k", type=int, default=10)
    parser.add_argument("--optimized-top-k", type=int, default=8)
    parser.add_argument("--judge-a-model", default="qwen3:8b")
    parser.add_argument("--judge-b-model", default="deepseek-r1:8b")
    parser.add_argument("--out-file", default=str(ROOT_DIR / "results" / "evaluation" / "dual_judge_expanded_eval.json"))
    parser.add_argument("--checkpoint-file", default="")
    args = parser.parse_args()

    cases = load_cases(Path(args.cases_file), args.sample_size)
    out_path = Path(args.out_file)
    checkpoint_path = Path(args.checkpoint_file) if args.checkpoint_file else out_path.with_suffix(".checkpoint.json")

    state: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/evaluation/paper_dual_judge_memorarag.py",
        "output_schema_version": "1.0",
        "cases_file": str(Path(args.cases_file)),
        "sample_size": len(cases),
        "baseline_rows": [],
        "optimized_rows": [],
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
    baseline_rows = state.get("baseline_rows", [])
    if not baseline_rows:
        baseline_rows = run_mode(pipeline, cases, args.baseline_top_k, use_dynamic=False, label="baseline")
        state["baseline_rows"] = baseline_rows
        save_checkpoint()
    optimized_rows = state.get("optimized_rows", [])
    if not optimized_rows:
        optimized_rows = run_mode(pipeline, cases, args.optimized_top_k, use_dynamic=True, label="optimized")
        state["optimized_rows"] = optimized_rows
        save_checkpoint()

    judge_a = OllamaLLM(model=args.judge_a_model, temperature=0.0, base_url=OLLAMA_HOST)
    judge_b = OllamaLLM(model=args.judge_b_model, temperature=0.0, base_url=OLLAMA_HOST)

    all_rows = [("baseline", row) for row in baseline_rows] + [("optimized", row) for row in optimized_rows]
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
        save_checkpoint()

    baseline = aggregate(baseline_rows, "baseline")
    optimized = aggregate(optimized_rows, "optimized")
    faith_drop = round(baseline["faithfulness_mean_merged"] - optimized["faithfulness_mean_merged"], 3)
    latency_drop = round((baseline["latency_mean"] - optimized["latency_mean"]) / baseline["latency_mean"] * 100.0, 2) if baseline["latency_mean"] else 0.0

    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/evaluation/paper_dual_judge_memorarag.py",
        "output_schema_version": "1.0",
        "cases_file": str(Path(args.cases_file)),
        "sample_size": len(cases),
        "baseline": baseline,
        "optimized": optimized,
        "acceptance_by_merged_judge": {
            "faithfulness_drop_le_0_2": faith_drop <= 0.2,
            "latency_drop_ge_10_percent": latency_drop >= 10.0,
            "faithfulness_drop": faith_drop,
            "latency_drop_percent": latency_drop,
        },
        "baseline_rows": baseline_rows,
        "optimized_rows": optimized_rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    if checkpoint_path.exists():
        checkpoint_path.unlink()
    print(f"SAVED: {out_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Current paper-track pruning policy ablation with checkpointing."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_ollama import OllamaLLM


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.rag_pipeline import MemoraRAGPipeline


OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = str(ROOT_DIR / "models" / "Llama-3-8B-Instruct.Q4_K_M.gguf")
DEFAULT_INDEX = str(ROOT_DIR / "models" / "vector_indices" / "turbo_index.json")
DEFAULT_CASES = ROOT_DIR / "data" / "eval" / "test_cases_test40.json"
DEFAULT_GRID = ROOT_DIR / "results" / "tuning" / "topn_budget_grid.json"
DEFAULT_OUT = ROOT_DIR / "results" / "evaluation" / "pruning_policy_ablation.json"


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


def try_stop_model(model_name: str) -> None:
    try:
        subprocess.run(["ollama", "stop", model_name], check=False, capture_output=True, text=True)
    except Exception:
        pass


def judge_answer(
    judge: OllamaLLM,
    question: str,
    answer: str,
    context: str,
    ground_truth: str,
    strict_mode: bool,
    max_retries: int,
    trace_label: str,
    stop_model_name: str,
) -> Dict[str, float]:
    prompt = build_prompt(question, answer, context, ground_truth, strict_mode)
    for attempt in range(1, max_retries + 1):
        started = time.time()
        try:
            raw = judge.invoke(prompt)
            text = raw.content if hasattr(raw, "content") else str(raw)
            scores = extract_scores(text)
            print(f"✅ {trace_label} 完成，用时 {round(time.time() - started, 2)}s")
            return scores
        except Exception as exc:
            print(
                f"⚠️ {trace_label} 失败({attempt}/{max_retries})，"
                f"{round(time.time() - started, 2)}s，错误: {type(exc).__name__}"
            )
            try_stop_model(stop_model_name)
            if attempt < max_retries:
                time.sleep(min(2 * attempt, 5))
    print(f"❌ {trace_label} 达到最大重试，回落为 0 分")
    return {"faithfulness": 0.0, "relevance": 0.0}


def apply_budget_cap(text: str, budget: Optional[int]) -> Tuple[str, Dict[str, Any]]:
    if budget is None or budget <= 0:
        return text, {
            "budget_chars": None,
            "budget_applied": False,
            "budget_mode": "none",
            "pre_budget_chars": len(text),
            "post_budget_chars": len(text),
        }
    if len(text) <= budget:
        return text, {
            "budget_chars": budget,
            "budget_applied": False,
            "budget_mode": "within_limit",
            "pre_budget_chars": len(text),
            "post_budget_chars": len(text),
        }

    marker = f"\n...[paper-pruning budget cap: {budget} chars]...\n"
    if budget <= len(marker) + 8:
        clipped = text[:budget]
        mode = "hard_prefix_cap"
    else:
        head = max(1, (budget - len(marker)) // 2)
        tail = max(1, budget - len(marker) - head)
        clipped = text[:head] + marker + text[-tail:]
        mode = "symmetric_head_tail_cap"
    return clipped, {
        "budget_chars": budget,
        "budget_applied": True,
        "budget_mode": mode,
        "pre_budget_chars": len(text),
        "post_budget_chars": len(clipped),
    }


def count_prompt_tokens(pipeline: MemoraRAGPipeline, prompt: str) -> Optional[int]:
    raw = prompt.encode("utf-8")
    if not hasattr(pipeline.llm, "tokenize"):
        return None
    attempts = [{}, {"add_bos": False}, {"special": True}, {"add_bos": False, "special": True}]
    for kwargs in attempts:
        try:
            return len(pipeline.llm.tokenize(raw, **kwargs))
        except TypeError:
            continue
        except Exception:
            return None
    return None


def classify_error(row: Dict[str, Any], threshold: float) -> str:
    if float(row.get("recall_hit_at_k", 0.0)) < 1.0:
        return "retrieval_miss"
    if float(row.get("faith_m", 0.0)) < threshold:
        return "factual_drift"
    if float(row.get("rel_m", 0.0)) < threshold:
        return "low_relevance"
    return "ok"


def stable_rng(seed: int, policy_id: str, case_id: str) -> random.Random:
    payload = f"{seed}:{policy_id}:{case_id}".encode("utf-8")
    digest = hashlib.md5(payload).hexdigest()
    return random.Random(int(digest[:8], 16))


def compress_with_policy(
    pipeline: MemoraRAGPipeline,
    query: str,
    context: str,
    policy_id: str,
    keep_ratio: float,
    seed: int,
    case_id: str,
) -> Tuple[str, Dict[str, Any]]:
    compressor = pipeline.compressor
    start_ns = time.perf_counter_ns()
    all_chunks = compressor.chunk_text(context)
    total_chunks = len(all_chunks)
    if total_chunks <= 4:
        return context, {
            "original_chunks": total_chunks,
            "retained_chunks": total_chunks,
            "strategy": "passthrough",
            "scoring_ms": 0.0,
            "pruning_ms": (time.perf_counter_ns() - start_ns) / 1_000_000,
        }

    anchor_count = max(2, min(10, int(total_chunks * 0.02)))
    prefix = all_chunks[:anchor_count]
    suffix = all_chunks[-anchor_count:]
    middle = all_chunks[anchor_count:-anchor_count]
    if not middle:
        return context, {
            "original_chunks": total_chunks,
            "retained_chunks": total_chunks,
            "strategy": "passthrough_no_middle",
            "scoring_ms": 0.0,
            "pruning_ms": (time.perf_counter_ns() - start_ns) / 1_000_000,
        }

    max_retained = 10
    keep_count = max(1, int(len(middle) * keep_ratio))
    keep_count = min(keep_count, max_retained)
    scoring_ms = 0.0

    if policy_id == "dynamic_cliff":
        score_start = time.perf_counter_ns()
        middle_scores = compressor.score_chunks(query, middle)
        if len(middle_scores) > 0:
            n_mid = len(middle_scores)
            edge = max(1, int(n_mid * 0.1))
            middle_scores[:edge] += 0.05
            middle_scores[-edge:] += 0.05
        scoring_ms = (time.perf_counter_ns() - score_start) / 1_000_000
        paired = [(i, chunk, float(score)) for i, (chunk, score) in enumerate(zip(middle, middle_scores))]
        paired.sort(key=lambda x: x[2], reverse=True)
        sorted_scores = [x[2] for x in paired]
        keep_count, strategy_name = compressor.get_adaptive_cutoff(sorted_scores)
        keep_count = min(max_retained, keep_count)
        survivors = paired[:keep_count]
        survivors.sort(key=lambda x: x[0])
        kept_middle = [chunk for _, chunk, _ in survivors]
    elif policy_id == "random_middle_60":
        rng = stable_rng(seed, policy_id, case_id)
        selected_idx = sorted(rng.sample(range(len(middle)), k=min(keep_count, len(middle))))
        kept_middle = [middle[idx] for idx in selected_idx]
        strategy_name = f"random_middle_{int(keep_ratio * 100)}%"
    elif policy_id == "boundary_first_60":
        left_count = (keep_count + 1) // 2
        right_count = keep_count - left_count
        left = list(range(min(left_count, len(middle))))
        right = list(range(max(left_count, len(middle) - right_count), len(middle))) if right_count > 0 else []
        selected_idx = sorted(set(left + right))
        kept_middle = [middle[idx] for idx in selected_idx]
        strategy_name = f"boundary_first_{int(keep_ratio * 100)}%"
    else:
        raise ValueError(f"Unsupported policy: {policy_id}")

    marker = compressor.omission_marker.format(strategy_name=strategy_name)
    final_text = "\n\n".join(prefix + [marker] + kept_middle + suffix)
    pruning_ms = (time.perf_counter_ns() - start_ns) / 1_000_000 - scoring_ms
    return final_text, {
        "original_chunks": total_chunks,
        "retained_chunks": len(prefix) + len(suffix) + len(kept_middle),
        "strategy": strategy_name,
        "scoring_ms": scoring_ms,
        "pruning_ms": pruning_ms,
    }


def generate_case(
    pipeline: MemoraRAGPipeline,
    case: Dict[str, Any],
    top_k: int,
    budget: Optional[int],
    keep_ratio: float,
    policy_id: str,
    seed: int,
) -> Dict[str, Any]:
    retrieval_start = time.perf_counter_ns()
    search_results, inner_retrieval_ms = pipeline.retriever.search(case["question"], top_k=top_k)
    retrieval_ms = (time.perf_counter_ns() - retrieval_start) / 1_000_000

    full_context = "\n\n".join(item.get("content", "") for item in search_results)
    compressed_context, comp_metrics = compress_with_policy(
        pipeline,
        query=case["question"],
        context=full_context,
        policy_id=policy_id,
        keep_ratio=keep_ratio,
        seed=seed,
        case_id=case["id"],
    )
    budgeted_context, budget_meta = apply_budget_cap(compressed_context, budget)
    final_prompt = pipeline._format_prompt(case["question"], budgeted_context)
    prompt_tokens = count_prompt_tokens(pipeline, final_prompt)

    llm_start = time.perf_counter_ns()
    response_stream = pipeline.llm(final_prompt, max_tokens=128, stream=True, stop=["<|eot_id|>"])
    answer_parts: List[str] = []
    ttft_ms: Optional[float] = None
    generated_tokens = 0
    for chunk in response_stream:
        text = chunk["choices"][0]["text"]
        if ttft_ms is None and text.strip():
            ttft_ms = (time.perf_counter_ns() - llm_start) / 1_000_000
        answer_parts.append(text)
        generated_tokens += 1
    llm_total_ms = (time.perf_counter_ns() - llm_start) / 1_000_000
    total_pipeline_ms = retrieval_ms + float(comp_metrics["scoring_ms"]) + float(comp_metrics["pruning_ms"]) + llm_total_ms

    retrieved_doc_paths = [
        normalize_doc_path(item.get("metadata", {}).get("path", ""))
        for item in search_results
    ]
    gold_docs = [doc.replace("\\", "/") for doc in case.get("source_docs", [])]
    overlap = sorted(set(gold_docs) & set(retrieved_doc_paths))
    recall_at_k = round(len(overlap) / len(gold_docs), 3) if gold_docs else 0.0
    return {
        "id": case["id"],
        "question": case["question"],
        "ground_truth": case["ground_truth"],
        "source_docs": gold_docs,
        "answer": "".join(answer_parts).strip(),
        "context": budgeted_context,
        "retrieved_doc_paths": retrieved_doc_paths,
        "retrieval_ms": round(retrieval_ms, 3),
        "retrieval_inner_ms": round(float(inner_retrieval_ms), 3),
        "scoring_ms": round(float(comp_metrics["scoring_ms"]), 3),
        "pruning_ms": round(float(comp_metrics["pruning_ms"]), 3),
        "ttft_ms": round(float(ttft_ms if ttft_ms is not None else llm_total_ms), 3),
        "total_latency_ms": round(float(total_pipeline_ms), 3),
        "prompt_tokens_final": prompt_tokens,
        "prompt_chars_final": len(final_prompt),
        "context_chars_final": len(budgeted_context),
        "generated_tokens": generated_tokens,
        "topn": top_k,
        "budget": budget,
        "keep_ratio": keep_ratio,
        "policy_id": policy_id,
        "strategy": comp_metrics.get("strategy", policy_id),
        "budget_meta": budget_meta,
        "original_chunks": comp_metrics.get("original_chunks"),
        "retained_chunks": comp_metrics.get("retained_chunks"),
        "recall_at_k": recall_at_k,
        "recall_hit_at_k": 1.0 if overlap else 0.0,
    }


def summarize_policy(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    def avg_numeric(key: str) -> float:
        vals = [float(row.get(key, 0.0)) for row in rows]
        return round(statistics.fmean(vals), 3) if vals else 0.0

    def avg_optional(key: str) -> Optional[float]:
        vals = [row.get(key) for row in rows if row.get(key) is not None]
        return round(statistics.fmean(float(v) for v in vals), 3) if vals else None

    failure_types: Dict[str, int] = {}
    for row in rows:
        tag = row.get("auto_error_category", "unjudged")
        failure_types[tag] = failure_types.get(tag, 0) + 1

    return {
        "n": len(rows),
        "retrieval_latency_mean_ms": avg_numeric("retrieval_ms"),
        "ttft_mean_ms": avg_numeric("ttft_ms"),
        "total_mean_ms": avg_numeric("total_latency_ms"),
        "faithfulness_mean_judge_a": avg_numeric("faith_a"),
        "relevance_mean_judge_a": avg_numeric("rel_a"),
        "faithfulness_mean_judge_b": avg_numeric("faith_b"),
        "relevance_mean_judge_b": avg_numeric("rel_b"),
        "faithfulness_mean_merged": avg_numeric("faith_m"),
        "relevance_mean_merged": avg_numeric("rel_m"),
        "judge_gap_faithfulness_mean": avg_numeric("gap_f"),
        "judge_gap_relevance_mean": avg_numeric("gap_r"),
        "answer_error_rate": round(
            statistics.fmean(1.0 if row.get("auto_error_category") != "ok" else 0.0 for row in rows), 3
        ) if rows else 0.0,
        "recall_at_k_mean": avg_numeric("recall_at_k"),
        "hit_rate_at_k_mean": avg_numeric("recall_hit_at_k"),
        "prompt_tokens_mean": avg_optional("prompt_tokens_final"),
        "context_chars_mean": avg_numeric("context_chars_final"),
        "retained_chunks_mean": avg_optional("retained_chunks"),
        "failure_count": int(sum(v for k, v in failure_types.items() if k != "ok")),
        "failure_types": failure_types,
        "strategies_used": sorted({row.get("strategy", "unknown") for row in rows}),
    }


def load_static_reference(grid_file: Path, point_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    payload = json.loads(grid_file.read_text("utf-8"))
    for point in payload.get("points", []):
        if point.get("point_id") == point_id:
            rows = point.get("rows", [])
            if not rows:
                raise ValueError(f"Point {point_id} has no rows in {grid_file}")
            return rows, point.get("summary", {})
    raise ValueError(f"Point {point_id} not found in {grid_file}")


def build_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    policies_out: List[Dict[str, Any]] = []
    static_summary = None
    for policy in state["policies"]:
        row = {
            "policy_id": policy["policy_id"],
            "label": policy["label"],
            "status": policy["status"],
            "source": policy.get("source", "generated"),
            "summary": policy.get("summary", {}),
        }
        policies_out.append(row)
        if policy["policy_id"] == "static_ratio_60":
            static_summary = policy.get("summary", {})

    completed = [p for p in policies_out if p.get("status") == "completed"]
    static_summary = static_summary or {}
    for row in completed:
        summary = row["summary"]
        row["comparison_vs_static"] = {
            "ttft_delta_ms": round(float(summary.get("ttft_mean_ms", 0.0)) - float(static_summary.get("ttft_mean_ms", 0.0)), 3),
            "faithfulness_delta": round(
                float(summary.get("faithfulness_mean_merged", 0.0)) - float(static_summary.get("faithfulness_mean_merged", 0.0)),
                3,
            ),
            "relevance_delta": round(
                float(summary.get("relevance_mean_merged", 0.0)) - float(static_summary.get("relevance_mean_merged", 0.0)),
                3,
            ),
            "error_rate_delta": round(
                float(summary.get("answer_error_rate", 0.0)) - float(static_summary.get("answer_error_rate", 0.0)),
                3,
            ),
        }

    completed.sort(
        key=lambda item: (
            float(item["summary"].get("ttft_mean_ms", 1e18)),
            float(item["summary"].get("total_mean_ms", 1e18)),
        )
    )
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/evaluation/paper_pruning_policy_ablation.py",
        "output_schema_version": "1.0",
        "cases_file": state["cases_file"],
        "sample_size": state["sample_size"],
        "top_k": state["top_k"],
        "budget": state["budget"],
        "keep_ratio": state["keep_ratio"],
        "quality_threshold": state["quality_threshold"],
        "static_reference_point_id": state["static_reference_point_id"],
        "static_reference_file": state["static_reference_file"],
        "policies": policies_out,
        "latency_ranking": [row["policy_id"] for row in completed],
    }


def write_payload(state: Dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(build_payload(state), ensure_ascii=False, indent=2), "utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a current paper-track pruning policy ablation.")
    parser.add_argument("--cases-file", default=str(DEFAULT_CASES))
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--model-path", default=DEFAULT_MODEL)
    parser.add_argument("--index-path", default=DEFAULT_INDEX)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--budget", type=int, default=1500)
    parser.add_argument("--keep-ratio", type=float, default=0.6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--judge-a-model", default="qwen3:8b")
    parser.add_argument("--judge-b-model", default="deepseek-r1:8b")
    parser.add_argument("--judge-timeout-sec", type=float, default=180.0)
    parser.add_argument("--judge-max-retries", type=int, default=2)
    parser.add_argument("--judge-max-tokens", type=int, default=96)
    parser.add_argument("--quality-threshold", type=float, default=5.0)
    parser.add_argument("--grid-file", default=str(DEFAULT_GRID))
    parser.add_argument("--static-reference-point-id", default="t5_b1500")
    parser.add_argument("--out-file", default=str(DEFAULT_OUT))
    parser.add_argument("--checkpoint-file", default="")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    cases = load_cases(Path(args.cases_file), args.sample_size)
    out_path = Path(args.out_file)
    checkpoint_path = Path(args.checkpoint_file) if args.checkpoint_file else out_path.with_suffix(".checkpoint.json")
    static_rows, _static_summary = load_static_reference(Path(args.grid_file), args.static_reference_point_id)

    new_state: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cases_file": str(Path(args.cases_file)),
        "sample_size": len(cases),
        "top_k": args.top_k,
        "budget": args.budget,
        "keep_ratio": args.keep_ratio,
        "quality_threshold": args.quality_threshold,
        "static_reference_point_id": args.static_reference_point_id,
        "static_reference_file": str(Path(args.grid_file)),
        "policies": [
            {
                "policy_id": "static_ratio_60",
                "label": "static_ratio_60",
                "source": "reused_from_topn_budget_grid",
                "status": "completed",
                "rows": static_rows,
                "summary": summarize_policy(static_rows),
            },
            {"policy_id": "dynamic_cliff", "label": "dynamic_cliff", "source": "generated", "status": "pending", "rows": [], "summary": {}},
            {"policy_id": "random_middle_60", "label": "random_middle_60", "source": "generated", "status": "pending", "rows": [], "summary": {}},
            {"policy_id": "boundary_first_60", "label": "boundary_first_60", "source": "generated", "status": "pending", "rows": [], "summary": {}},
        ],
    }

    if checkpoint_path.exists():
        if not args.resume:
            raise SystemExit(f"Checkpoint exists at {checkpoint_path}. Re-run with --resume to continue.")
        loaded = json.loads(checkpoint_path.read_text("utf-8"))
        if (
            loaded.get("cases_file") != new_state["cases_file"]
            or loaded.get("sample_size") != new_state["sample_size"]
            or loaded.get("top_k") != new_state["top_k"]
            or loaded.get("budget") != new_state["budget"]
            or loaded.get("keep_ratio") != new_state["keep_ratio"]
        ):
            raise SystemExit("Existing checkpoint does not match the requested ablation configuration.")
        state = loaded
        print(f"RESUME: {checkpoint_path}")
    else:
        state = new_state

    def save_checkpoint() -> None:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(json.dumps(state, ensure_ascii=False, separators=(",", ":")), "utf-8")

    pipeline = MemoraRAGPipeline(model_path=args.model_path, index_path=args.index_path, n_ctx=4096)
    judge_a = OllamaLLM(
        model=args.judge_a_model,
        temperature=0.0,
        base_url=OLLAMA_HOST,
        format="json",
        num_predict=args.judge_max_tokens,
        sync_client_kwargs={"timeout": args.judge_timeout_sec},
    )
    judge_b = OllamaLLM(
        model=args.judge_b_model,
        temperature=0.0,
        base_url=OLLAMA_HOST,
        format="json",
        num_predict=args.judge_max_tokens,
        sync_client_kwargs={"timeout": args.judge_timeout_sec},
    )

    write_payload(state, out_path)

    for policy in state["policies"]:
        if policy["status"] == "completed":
            continue
        rows = policy.get("rows", [])
        for idx in range(len(rows), len(cases)):
            case = cases[idx]
            print(f"[{policy['policy_id']}] generate {idx + 1}/{len(cases)} {case['id']}")
            rows.append(
                generate_case(
                    pipeline,
                    case,
                    top_k=args.top_k,
                    budget=args.budget,
                    keep_ratio=args.keep_ratio,
                    policy_id=policy["policy_id"],
                    seed=args.seed,
                )
            )
            policy["rows"] = rows
            policy["status"] = "generated_partial"
            save_checkpoint()
            write_payload(state, out_path)

        for idx, row in enumerate(rows, start=1):
            if "judge_a" not in row:
                print(f"[judge_a] {policy['policy_id']} {idx}/{len(rows)} {row['id']}")
                row["judge_a"] = judge_answer(
                    judge=judge_a,
                    question=row["question"],
                    answer=row["answer"],
                    context=row["context"],
                    ground_truth=row["ground_truth"],
                    strict_mode=True,
                    max_retries=args.judge_max_retries,
                    trace_label=f"judge_a:{policy['policy_id']}:{row['id']}",
                    stop_model_name=args.judge_a_model,
                )
            if "judge_b" not in row:
                print(f"[judge_b] {policy['policy_id']} {idx}/{len(rows)} {row['id']}")
                row["judge_b"] = judge_answer(
                    judge=judge_b,
                    question=row["question"],
                    answer=row["answer"],
                    context=row["context"],
                    ground_truth=row["ground_truth"],
                    strict_mode=False,
                    max_retries=args.judge_max_retries,
                    trace_label=f"judge_b:{policy['policy_id']}:{row['id']}",
                    stop_model_name=args.judge_b_model,
                )
            row["faith_a"] = round(row["judge_a"]["faithfulness"], 3)
            row["rel_a"] = round(row["judge_a"]["relevance"], 3)
            row["faith_b"] = round(row["judge_b"]["faithfulness"], 3)
            row["rel_b"] = round(row["judge_b"]["relevance"], 3)
            row["faith_m"] = round((row["faith_a"] + row["faith_b"]) / 2.0, 3)
            row["rel_m"] = round((row["rel_a"] + row["rel_b"]) / 2.0, 3)
            row["gap_f"] = round(abs(row["faith_a"] - row["faith_b"]), 3)
            row["gap_r"] = round(abs(row["rel_a"] - row["rel_b"]), 3)
            row["auto_error_category"] = classify_error(row, args.quality_threshold)
            policy["rows"] = rows
            policy["status"] = "judged_partial"
            save_checkpoint()
            write_payload(state, out_path)

        policy["summary"] = summarize_policy(rows)
        policy["status"] = "completed"
        save_checkpoint()
        write_payload(state, out_path)

    if checkpoint_path.exists():
        checkpoint_path.unlink()
    print(f"SAVED: {out_path}")


if __name__ == "__main__":
    main()

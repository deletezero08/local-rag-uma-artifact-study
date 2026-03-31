#!/usr/bin/env python3
"""Current paper-track topn x budget grid search with checkpointing."""

from __future__ import annotations

import argparse
import json
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
DEFAULT_OUT = ROOT_DIR / "results" / "tuning" / "topn_budget_grid.json"
DEFAULT_SUMMARY = ROOT_DIR / "results" / "evaluation" / "topn_budget_grid_summary.json"
DEFAULT_FAILURES = ROOT_DIR / "results" / "evaluation" / "topn_budget_failure_cases.md"
DEFAULT_BASELINE = ROOT_DIR / "results" / "evaluation" / "dual_judge_expanded_eval.json"
DOCS_ROOT = ROOT_DIR / "docs"


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


def try_stop_model(model_name: str) -> None:
    if not model_name:
        return
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
        start = time.time()
        try:
            raw = judge.invoke(prompt)
            text = raw.content if hasattr(raw, "content") else str(raw)
            scores = extract_scores(text)
            elapsed = round(time.time() - start, 2)
            print(f"✅ {trace_label} 完成，用时 {elapsed}s")
            return scores
        except Exception as exc:
            elapsed = round(time.time() - start, 2)
            print(f"⚠️ {trace_label} 失败({attempt}/{max_retries})，{elapsed}s，错误: {type(exc).__name__}")
            try_stop_model(stop_model_name)
            if attempt < max_retries:
                time.sleep(min(2 * attempt, 5))
    print(f"❌ {trace_label} 达到最大重试，回落为 0 分")
    return {"faithfulness": 0.0, "relevance": 0.0}


def parse_int_list(raw: str) -> List[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def parse_budget_values(raw: str) -> List[Optional[int]]:
    values: List[Optional[int]] = []
    for item in raw.split(","):
        token = item.strip().lower()
        if not token:
            continue
        if token in {"none", "null", "no", "off"}:
            values.append(None)
        else:
            values.append(int(token))
    return values


def budget_label(value: Optional[int]) -> str:
    return "none" if value is None else str(value)


def point_id(topn: int, budget: Optional[int]) -> str:
    return f"t{topn}_b{budget_label(budget)}"


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

    marker = f"\n...[paper-grid budget cap: {budget} chars]...\n"
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
    attempts = [
        {},
        {"add_bos": False},
        {"special": True},
        {"add_bos": False, "special": True},
    ]
    for kwargs in attempts:
        try:
            return len(pipeline.llm.tokenize(raw, **kwargs))
        except TypeError:
            continue
        except Exception:
            return None
    return None


def classify_error(row: Dict[str, Any], threshold: float) -> str:
    if row.get("recall_hit_at_k", 0.0) < 1.0:
        return "retrieval_miss"
    if row.get("faith_m", 0.0) < threshold:
        return "factual_drift"
    if row.get("rel_m", 0.0) < threshold:
        return "low_relevance"
    return "ok"


def load_baseline_reference(path: Path, threshold: float) -> Dict[str, Any]:
    payload = json.loads(path.read_text("utf-8"))
    baseline = dict(payload.get("baseline", {}))
    optimized = dict(payload.get("optimized", {}))
    baseline_rows = payload.get("baseline_rows", [])
    optimized_rows = payload.get("optimized_rows", [])

    def proxy_error_rate(rows: List[Dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        return round(
            statistics.fmean(
                1.0
                if float(row.get("faith_m", 0.0)) < threshold or float(row.get("rel_m", 0.0)) < threshold
                else 0.0
                for row in rows
            ),
            3,
        )

    baseline["answer_error_rate_proxy"] = proxy_error_rate(baseline_rows)
    optimized["answer_error_rate_proxy"] = proxy_error_rate(optimized_rows)
    return {
        "source_file": str(path),
        "quality_threshold": threshold,
        "baseline": baseline,
        "optimized": optimized,
    }


def generate_case(
    pipeline: MemoraRAGPipeline,
    case: Dict[str, Any],
    topn: int,
    budget: Optional[int],
    keep_ratio: float,
) -> Dict[str, Any]:
    pipeline.compressor.keep_ratio = keep_ratio

    retrieval_start = time.perf_counter_ns()
    search_results, inner_retrieval_ms = pipeline.retriever.search(case["question"], top_k=topn)
    retrieval_ms = (time.perf_counter_ns() - retrieval_start) / 1_000_000

    full_context = "\n\n".join(item.get("content", "") for item in search_results)
    compressed_context, comp_metrics = pipeline.compressor.compress(case["question"], full_context, use_dynamic=False)
    budgeted_context, budget_meta = apply_budget_cap(compressed_context, budget)
    final_prompt = pipeline._format_prompt(case["question"], budgeted_context)
    prompt_tokens = count_prompt_tokens(pipeline, final_prompt)

    llm_start = time.perf_counter_ns()
    response_stream = pipeline.llm(
        final_prompt,
        max_tokens=128,
        stream=True,
        stop=["<|eot_id|>"],
    )

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
        "topn": topn,
        "budget": budget,
        "keep_ratio": keep_ratio,
        "strategy": comp_metrics.get("strategy", "unknown"),
        "budget_meta": budget_meta,
        "recall_at_k": recall_at_k,
        "recall_hit_at_k": 1.0 if overlap else 0.0,
    }


def summarize_point(rows: List[Dict[str, Any]], topn: int, budget: Optional[int]) -> Dict[str, Any]:
    def avg_numeric(key: str) -> float:
        vals = [float(row.get(key, 0.0)) for row in rows]
        return round(statistics.fmean(vals), 3) if vals else 0.0

    def avg_optional(key: str) -> Optional[float]:
        vals = [row.get(key) for row in rows if row.get(key) is not None]
        if not vals:
            return None
        return round(statistics.fmean(float(v) for v in vals), 3)

    failure_counts: Dict[str, int] = {}
    for row in rows:
        category = row.get("auto_error_category", "unjudged")
        failure_counts[category] = failure_counts.get(category, 0) + 1

    return {
        "topn": topn,
        "budget": budget,
        "budget_label": budget_label(budget),
        "n": len(rows),
        "retrieval_latency_ms": avg_numeric("retrieval_ms"),
        "ttft_ms": avg_numeric("ttft_ms"),
        "total_latency_ms": avg_numeric("total_latency_ms"),
        "merged_faithfulness": avg_numeric("faith_m"),
        "merged_relevance": avg_numeric("rel_m"),
        "answer_error_rate": round(
            statistics.fmean(1.0 if row.get("auto_error_category") != "ok" else 0.0 for row in rows),
            3,
        )
        if rows
        else 0.0,
        "prompt_tokens_final": avg_optional("prompt_tokens_final"),
        "prompt_chars_final": avg_numeric("prompt_chars_final"),
        "context_chars_final": avg_numeric("context_chars_final"),
        "judge_gap_faithfulness": avg_numeric("gap_f"),
        "judge_gap_relevance": avg_numeric("gap_r"),
        "recall_at_k": avg_numeric("recall_at_k"),
        "failure_count": int(sum(count for name, count in failure_counts.items() if name != "ok")),
        "failure_types": failure_counts,
        "strategies_used": sorted({row.get("strategy", "unknown") for row in rows}),
    }


def evaluate_candidate(
    point_summary: Dict[str, Any],
    baseline_reference: Dict[str, Any],
    max_faithfulness_drop: float,
    max_relevance_drop: float,
    max_error_rate_increase: float,
    max_judge_gap_mean: float,
) -> Dict[str, Any]:
    baseline = baseline_reference["baseline"]
    faith_drop = round(float(baseline["faithfulness_mean_merged"]) - float(point_summary["merged_faithfulness"]), 3)
    relevance_drop = round(float(baseline["relevance_mean_merged"]) - float(point_summary["merged_relevance"]), 3)
    baseline_error_proxy = float(baseline.get("answer_error_rate_proxy", 0.0))
    error_rate_delta = round(float(point_summary["answer_error_rate"]) - baseline_error_proxy, 3)

    notes: List[str] = []
    is_candidate = True
    if faith_drop > max_faithfulness_drop:
        is_candidate = False
        notes.append(f"faithfulness_drop={faith_drop:.3f}>threshold")
    if relevance_drop > max_relevance_drop:
        is_candidate = False
        notes.append(f"relevance_drop={relevance_drop:.3f}>threshold")
    if error_rate_delta > max_error_rate_increase:
        is_candidate = False
        notes.append(f"error_rate_delta={error_rate_delta:.3f}>threshold")
    if float(point_summary["judge_gap_faithfulness"]) > max_judge_gap_mean:
        is_candidate = False
        notes.append(
            f"judge_gap_f={float(point_summary['judge_gap_faithfulness']):.3f}>threshold"
        )
    if float(point_summary["judge_gap_relevance"]) > max_judge_gap_mean:
        is_candidate = False
        notes.append(
            f"judge_gap_r={float(point_summary['judge_gap_relevance']):.3f}>threshold"
        )

    if not notes:
        notes.append("within bounded operating region under current thresholds")

    return {
        "faithfulness_drop_vs_baseline": faith_drop,
        "relevance_drop_vs_baseline": relevance_drop,
        "answer_error_rate_delta_vs_baseline_proxy": error_rate_delta,
        "baseline_answer_error_rate_proxy": baseline_error_proxy,
        "is_candidate": is_candidate,
        "selection_note": "; ".join(notes),
    }


def build_summary_payload(
    state: Dict[str, Any],
    baseline_reference: Dict[str, Any],
    thresholds: Dict[str, float],
) -> Dict[str, Any]:
    summary_rows: List[Dict[str, Any]] = []
    for point in state["points"]:
        compact = {
            "point_id": point["point_id"],
            "topn": point["topn"],
            "budget": point["budget"],
            "budget_label": point["budget_label"],
            "status": point["status"],
        }
        compact.update(point.get("summary", {}))
        compact.update(point.get("selection", {}))
        summary_rows.append(compact)

    completed = [row for row in summary_rows if row.get("status") == "completed"]
    candidates = [row for row in completed if row.get("is_candidate")]
    candidates.sort(
        key=lambda row: (
            float(row.get("ttft_ms", 1e18)),
            float(row.get("total_latency_ms", 1e18)),
            -float(row.get("merged_faithfulness", -1e18)),
            float(row.get("answer_error_rate", 1e18)),
        )
    )

    selected_point = candidates[0] if candidates else None
    if selected_point is None and completed:
        fallback = sorted(
            completed,
            key=lambda row: (
                float(row.get("ttft_ms", 1e18)),
                float(row.get("total_latency_ms", 1e18)),
            ),
        )[0]
        fallback = dict(fallback)
        fallback["selection_note"] = (
            fallback.get("selection_note", "") + "; selected as latency-first fallback because no point passed the candidate filter"
        ).strip("; ")
        selected_point = fallback

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/evaluation/paper_topn_budget_grid.py",
        "output_schema_version": "1.0",
        "source_grid_file": state["out_file"],
        "cases_file": state["cases_file"],
        "sample_size": state["sample_size"],
        "keep_ratio": state["keep_ratio"],
        "topn_values": state["topn_values"],
        "budget_values": state["budget_values"],
        "baseline_reference": baseline_reference,
        "selection_thresholds": thresholds,
        "completed_points": len(completed),
        "total_points": len(summary_rows),
        "summary_rows": summary_rows,
        "candidate_points": candidates[:3],
        "selected_point": selected_point,
    }


def build_failure_markdown(summary_payload: Dict[str, Any], state: Dict[str, Any]) -> str:
    lines = ["# Topn x Budget Failure Cases", ""]
    baseline = summary_payload["baseline_reference"]["baseline"]
    lines.append("## Baseline Reference")
    lines.append(
        f"- Faithfulness / relevance: `{baseline.get('faithfulness_mean_merged', 0.0)}` / `{baseline.get('relevance_mean_merged', 0.0)}`"
    )
    lines.append(
        f"- Error-rate proxy: `{baseline.get('answer_error_rate_proxy', 0.0)}`"
    )
    lines.append("")

    selected = summary_payload.get("selected_point")
    if selected:
        lines.append("## Selected Point")
        lines.append(
            f"- `{selected['point_id']}`: `topn={selected['topn']}`, `budget={selected['budget_label']}`, "
            f"`TTFT={selected.get('ttft_ms')}`, `faith={selected.get('merged_faithfulness')}`, "
            f"`rel={selected.get('merged_relevance')}`, `error_rate={selected.get('answer_error_rate')}`"
        )
        lines.append(f"- Note: {selected.get('selection_note', '')}")
        lines.append("")

    candidate_points = summary_payload.get("candidate_points", [])
    if candidate_points:
        lines.append("## Candidate Points")
        for row in candidate_points:
            lines.append(
                f"- `{row['point_id']}`: `TTFT={row.get('ttft_ms')}`, `total={row.get('total_latency_ms')}`, "
                f"`faith={row.get('merged_faithfulness')}`, `rel={row.get('merged_relevance')}`, "
                f"`error_rate={row.get('answer_error_rate')}`"
            )
        lines.append("")

    if selected:
        target_point = next((p for p in state["points"] if p["point_id"] == selected["point_id"]), None)
        if target_point:
            failed_rows = [
                row for row in target_point.get("rows", []) if row.get("auto_error_category") not in {None, "ok"}
            ][:5]
            lines.append("## Representative Failures Under Selected Point")
            if failed_rows:
                for row in failed_rows:
                    lines.append(
                        f"- `{row['id']}` `{row['auto_error_category']}` faith `{row.get('faith_m')}` rel `{row.get('rel_m')}`: {row['question']}"
                    )
            else:
                lines.append("- No failed rows under the selected point.")
            lines.append("")

    non_candidates = [
        row for row in summary_payload.get("summary_rows", []) if row.get("status") == "completed" and not row.get("is_candidate")
    ]
    non_candidates.sort(key=lambda row: float(row.get("ttft_ms", 1e18)))
    if non_candidates:
        lines.append("## Fast But Rejected Points")
        for row in non_candidates[:3]:
            lines.append(
                f"- `{row['point_id']}`: `TTFT={row.get('ttft_ms')}`, `faith={row.get('merged_faithfulness')}`, "
                f"`rel={row.get('merged_relevance')}`, `error_rate={row.get('answer_error_rate')}`; note: {row.get('selection_note', '')}"
            )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_payloads(
    state: Dict[str, Any],
    baseline_reference: Dict[str, Any],
    thresholds: Dict[str, float],
    out_path: Path,
    summary_path: Path,
    failure_path: Path,
) -> None:
    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "scripts/evaluation/paper_topn_budget_grid.py",
        "output_schema_version": "1.0",
        "experiment": "E7_topn_budget_grid",
        "cases_file": state["cases_file"],
        "sample_size": state["sample_size"],
        "keep_ratio": state["keep_ratio"],
        "topn_values": state["topn_values"],
        "budget_values": state["budget_values"],
        "baseline_reference": baseline_reference,
        "selection_thresholds": thresholds,
        "points": state["points"],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")

    summary_payload = build_summary_payload(state, baseline_reference, thresholds)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), "utf-8")

    failure_path.parent.mkdir(parents=True, exist_ok=True)
    failure_path.write_text(build_failure_markdown(summary_payload, state), "utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Current paper-track topn x budget grid search.")
    parser.add_argument("--cases-file", default=str(DEFAULT_CASES))
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--model-path", default=DEFAULT_MODEL)
    parser.add_argument("--index-path", default=DEFAULT_INDEX)
    parser.add_argument("--topn-values", default="5,7,8,10")
    parser.add_argument("--budget-values", default="none,1500,2000,2500")
    parser.add_argument("--keep-ratio", type=float, default=0.6)
    parser.add_argument("--judge-a-model", default="qwen3:8b")
    parser.add_argument("--judge-b-model", default="deepseek-r1:8b")
    parser.add_argument("--judge-timeout-sec", type=float, default=180.0)
    parser.add_argument("--judge-max-retries", type=int, default=2)
    parser.add_argument("--judge-max-tokens", type=int, default=96)
    parser.add_argument("--quality-threshold", type=float, default=5.0)
    parser.add_argument("--max-faithfulness-drop", type=float, default=0.2)
    parser.add_argument("--max-relevance-drop", type=float, default=0.2)
    parser.add_argument("--max-error-rate-increase", type=float, default=0.1)
    parser.add_argument("--max-judge-gap-mean", type=float, default=3.0)
    parser.add_argument("--baseline-reference-file", default=str(DEFAULT_BASELINE))
    parser.add_argument("--out-file", default=str(DEFAULT_OUT))
    parser.add_argument("--summary-file", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--failure-file", default=str(DEFAULT_FAILURES))
    parser.add_argument("--checkpoint-file", default="")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    topn_values = parse_int_list(args.topn_values)
    budget_values = parse_budget_values(args.budget_values)
    cases = load_cases(Path(args.cases_file), args.sample_size)
    out_path = Path(args.out_file)
    summary_path = Path(args.summary_file)
    failure_path = Path(args.failure_file)
    checkpoint_path = Path(args.checkpoint_file) if args.checkpoint_file else out_path.with_suffix(".checkpoint.json")

    baseline_reference = load_baseline_reference(Path(args.baseline_reference_file), args.quality_threshold)
    thresholds = {
        "max_faithfulness_drop": args.max_faithfulness_drop,
        "max_relevance_drop": args.max_relevance_drop,
        "max_error_rate_increase": args.max_error_rate_increase,
        "max_judge_gap_mean": args.max_judge_gap_mean,
        "quality_threshold": args.quality_threshold,
    }

    new_state: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cases_file": str(Path(args.cases_file)),
        "sample_size": len(cases),
        "keep_ratio": args.keep_ratio,
        "topn_values": topn_values,
        "budget_values": [budget_label(v) for v in budget_values],
        "out_file": str(out_path),
        "points": [
            {
                "point_id": point_id(topn, budget),
                "topn": topn,
                "budget": budget,
                "budget_label": budget_label(budget),
                "status": "pending",
                "rows": [],
                "summary": {},
                "selection": {},
            }
            for topn in topn_values
            for budget in budget_values
        ],
    }

    if checkpoint_path.exists():
        if not args.resume:
            raise SystemExit(f"Checkpoint exists at {checkpoint_path}. Re-run with --resume to continue.")
        loaded = json.loads(checkpoint_path.read_text("utf-8"))
        if (
            loaded.get("cases_file") != new_state["cases_file"]
            or loaded.get("sample_size") != new_state["sample_size"]
            or loaded.get("keep_ratio") != new_state["keep_ratio"]
            or loaded.get("topn_values") != new_state["topn_values"]
            or loaded.get("budget_values") != new_state["budget_values"]
        ):
            raise SystemExit("Existing checkpoint does not match the requested grid configuration.")
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

    for point in state["points"]:
        if point.get("status") == "completed":
            continue

        topn = int(point["topn"])
        budget = point.get("budget")
        rows = point.get("rows", [])

        for idx in range(len(rows), len(cases)):
            case = cases[idx]
            print(f"[{point['point_id']}] generate {idx + 1}/{len(cases)} {case['id']}")
            rows.append(generate_case(pipeline, case, topn=topn, budget=budget, keep_ratio=args.keep_ratio))
            point["rows"] = rows
            point["status"] = "generated_partial"
            save_checkpoint()
            write_payloads(state, baseline_reference, thresholds, out_path, summary_path, failure_path)

        for idx, row in enumerate(rows, start=1):
            if "judge_a" not in row:
                print(f"[judge_a] {point['point_id']} {idx}/{len(rows)} {row['id']}")
                row["judge_a"] = judge_answer(
                    judge=judge_a,
                    question=row["question"],
                    answer=row["answer"],
                    context=row["context"],
                    ground_truth=row["ground_truth"],
                    strict_mode=True,
                    max_retries=args.judge_max_retries,
                    trace_label=f"judge_a:{point['point_id']}:{row['id']}",
                    stop_model_name=args.judge_a_model,
                )
            if "judge_b" not in row:
                print(f"[judge_b] {point['point_id']} {idx}/{len(rows)} {row['id']}")
                row["judge_b"] = judge_answer(
                    judge=judge_b,
                    question=row["question"],
                    answer=row["answer"],
                    context=row["context"],
                    ground_truth=row["ground_truth"],
                    strict_mode=False,
                    max_retries=args.judge_max_retries,
                    trace_label=f"judge_b:{point['point_id']}:{row['id']}",
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
            point["rows"] = rows
            point["status"] = "judged_partial"
            save_checkpoint()
            write_payloads(state, baseline_reference, thresholds, out_path, summary_path, failure_path)

        point_summary = summarize_point(rows, topn=topn, budget=budget)
        selection = evaluate_candidate(
            point_summary,
            baseline_reference=baseline_reference,
            max_faithfulness_drop=args.max_faithfulness_drop,
            max_relevance_drop=args.max_relevance_drop,
            max_error_rate_increase=args.max_error_rate_increase,
            max_judge_gap_mean=args.max_judge_gap_mean,
        )
        point["summary"] = point_summary
        point["selection"] = selection
        point["status"] = "completed"
        save_checkpoint()
        write_payloads(state, baseline_reference, thresholds, out_path, summary_path, failure_path)

    if checkpoint_path.exists():
        checkpoint_path.unlink()
    print(f"SAVED: {out_path}")
    print(f"SUMMARY: {summary_path}")
    print(f"FAILURES: {failure_path}")


if __name__ == "__main__":
    main()

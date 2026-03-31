#!/usr/bin/env python3
import argparse
import json
import subprocess
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Callable

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.evaluate import RAGEvaluator
from src.config import OLLAMA_HOST, settings

from langchain_ollama import OllamaLLM


def clip_text(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...(truncated)"


def _extract_json_scores(raw_text: str) -> Dict[str, float]:
    raw_text = (raw_text or "").strip()
    if "```" in raw_text:
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    import re
    m = re.search(r"\{.*\}", raw_text, re.DOTALL)
    payload = json.loads(m.group() if m else raw_text)
    return {
        "faithfulness": float(payload.get("faithfulness", 0.0)),
        "relevance": float(payload.get("relevance", 0.0)),
    }


def _build_grade_prompt(
    question: str,
    answer: str,
    context: str,
    ground_truth: str = "",
    strict_mode: bool = True,
) -> str:
    max_context_chars = int(settings.get("evaluation", {}).get("max_grade_context_chars", 3600))
    max_answer_chars = int(settings.get("evaluation", {}).get("max_grade_answer_chars", 2200))
    max_truth_chars = int(settings.get("evaluation", {}).get("max_grade_truth_chars", 1400))
    context = clip_text(context, max_context_chars)
    answer = clip_text(answer, max_answer_chars)
    ground_truth = clip_text(ground_truth, max_truth_chars)
    style_rule = "只输出 JSON，不要解释。" if strict_mode else "输出 JSON。"
    return f"""你是严格的评估裁判。请根据参考资料评估回答质量。
参考资料: {context}
问题: {question}
标准答案: {ground_truth}
系统回答: {answer}
请给出 0-10 分的 JSON：{{"faithfulness": x, "relevance": y}}
{style_rule}"""


def _grade_with_ollama(judge: Any, prompt: str) -> Dict[str, float]:
    raw = judge.invoke(prompt)
    raw_text = raw.content if hasattr(raw, "content") else str(raw)
    return _extract_json_scores(raw_text)


def grade_with_judge(
    judge: Any,
    question: str,
    answer: str,
    context: str,
    ground_truth: str = "",
    strict_mode: bool = True,
    max_retries: int = 1,
    trace_label: str = "",
) -> Dict[str, float]:
    prompt = _build_grade_prompt(question, answer, context, ground_truth, strict_mode)
    for attempt in range(1, max_retries + 1):
        start = time.time()
        try:
            scores = _grade_with_ollama(judge, prompt)
            cost = round(time.time() - start, 2)
            if trace_label:
                print(f"✅ {trace_label} 完成，用时 {cost}s")
            return scores
        except Exception as exc:
            cost = round(time.time() - start, 2)
            if trace_label:
                print(f"⚠️ {trace_label} 失败({attempt}/{max_retries})，{cost}s，错误: {type(exc).__name__}")
            continue
    if trace_label:
        print(f"❌ {trace_label} 达到最大重试，回落为 0 分")
    return {"faithfulness": 0.0, "relevance": 0.0}


def run_config(
    evaluator: RAGEvaluator,
    cases: List[Dict[str, Any]],
    top_n: int,
    budget: int,
    existing_rows: List[Dict[str, Any]],
    iterations: int,
    checkpoint_save: Callable[[], None],
    mode: str = "ensemble",
) -> List[Dict[str, Any]]:
    retrieval_cfg = settings.setdefault("retrieval", {})
    eval_cfg = settings.setdefault("evaluation", {})
    backup_ret = dict(retrieval_cfg)
    backup_eval = dict(eval_cfg)
    retrieval_cfg["top_n"] = top_n
    eval_cfg["context_char_budget"] = budget
    evaluator.rag.retrieval_mode = mode
    evaluator.rag._build_qa_chain()
    rows: List[Dict[str, Any]] = list(existing_rows)
    total = len(cases) * iterations
    try:
        for idx in range(len(rows), total):
            c = cases[idx % len(cases)]
            iter_idx = idx // len(cases) + 1
            start = time.time()
            response = evaluator.rag.query(c["question"], category="all")
            elapsed = time.time() - start
            source_docs = response.get("source_docs") or []
            context_text = "\n".join([d.page_content[:1000] for d in source_docs[:6]])
            rows.append(
                {
                    "id": c["id"],
                    "iter": iter_idx,
                    "question": c["question"],
                    "answer": str(response.get("answer", "")),
                    "ground_truth": c.get("ground_truth", ""),
                    "context": context_text,
                    "latency": elapsed,
                    "sources_count": len(response.get("sources", [])),
                }
            )
            checkpoint_save()
        return rows
    finally:
        settings["retrieval"] = backup_ret
        settings["evaluation"] = backup_eval
        evaluator.rag._build_qa_chain()


def summarize(rows: List[Dict[str, Any]], metric_key: str) -> float:
    vals = [float(x.get(metric_key, 0.0)) for x in rows]
    return round(statistics.fmean(vals), 3) if vals else 0.0


def try_stop_model(model_name: str) -> None:
    if not model_name:
        return
    try:
        subprocess.run(["ollama", "stop", model_name], check=False, capture_output=True, text=True)
    except Exception:
        pass


def run_judge_pass(
    rows: List[Dict[str, Any]],
    model_name: str,
    output_key: str,
    strict_mode: bool,
    unload_after: bool,
    checkpoint_save: Callable[[], None],
    timeout_sec: float,
    max_retries: int,
) -> None:
    judge = OllamaLLM(
        model=model_name,
        temperature=0.0,
        base_url=OLLAMA_HOST,
        sync_client_kwargs={"timeout": timeout_sec},
    )
    total = len(rows)
    pending = sum(1 for row in rows if output_key not in row)
    print(f"🚦 开始 {output_key} 打分：待处理 {pending}/{total}，超时 {timeout_sec}s，重试 {max_retries} 次")
    for idx, row in enumerate(rows, start=1):
        if output_key in row:
            continue
        print(f"🧪 {output_key} 评分进度: {idx}/{total} ({row.get('id', '-')})")
        row[output_key] = grade_with_judge(
            judge=judge,
            question=row["question"],
            answer=row["answer"],
            context=row["context"],
            ground_truth=row["ground_truth"],
            strict_mode=strict_mode,
            max_retries=max_retries,
            trace_label=f"{output_key}:{row.get('id', '-')}",
        )
        checkpoint_save()
    if unload_after:
        try_stop_model(model_name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--baseline-top-n", type=int, default=10)
    parser.add_argument("--baseline-budget", type=int, default=0)
    parser.add_argument("--optimized-top-n", type=int, default=8)
    parser.add_argument("--optimized-budget", type=int, default=1500)
    parser.add_argument("--judge-a-model", default=settings.get("llm", {}).get("judge_model", "qwen3:8b"))
    parser.add_argument("--judge-b-model", default=settings.get("llm", {}).get("secondary_judge_model", "qwen3:8b"))
    parser.add_argument("--serial-judge", action="store_true")
    parser.add_argument("--unload-between-judges", action="store_true")
    parser.add_argument("--run-id", default=time.strftime("%Y%m%d%H%M%S"))
    parser.add_argument("--out-file", default="step1_dual_judge_check.json")
    parser.add_argument("--checkpoint-file", default="")
    parser.add_argument("--judge-timeout-sec", type=float, default=180.0)
    parser.add_argument("--judge-max-retries", type=int, default=2)
    args = parser.parse_args()

    results_dir = ROOT_DIR / "experiments" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out = results_dir / args.out_file
    checkpoint_name = args.checkpoint_file.strip() if args.checkpoint_file.strip() else f"temp_dual_judge_{out.stem}_checkpoint.json"
    checkpoint_path = results_dir / checkpoint_name

    state = {
        "meta": {
            "sample_size": args.sample_size,
            "iterations": args.iterations,
            "baseline_top_n": args.baseline_top_n,
            "baseline_budget": args.baseline_budget,
            "optimized_top_n": args.optimized_top_n,
            "optimized_budget": args.optimized_budget,
            "judge_a_model": args.judge_a_model,
            "judge_b_model": args.judge_b_model,
            "serial_judge": args.serial_judge,
            "run_id": args.run_id,
            "out_file": args.out_file,
        },
        "baseline_rows_all": [],
        "optimized_rows_all": [],
    }
    if checkpoint_path.exists():
        loaded = json.loads(checkpoint_path.read_text("utf-8"))
        if loaded.get("meta") == state["meta"]:
            state = loaded
            print(f"♻️ 检测到断点，继续续跑: {checkpoint_path}")
        else:
            print(f"⚠️ 断点参数不一致，忽略旧断点: {checkpoint_path}")

    def save_checkpoint() -> None:
        checkpoint_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")

    evaluator = RAGEvaluator()
    cases = evaluator._load_question_set()[: args.sample_size]
    if len(cases) < args.sample_size:
        raise RuntimeError(f"question_set 不足 {args.sample_size} 条，当前 {len(cases)}")

    baseline_rows_all: List[Dict[str, Any]] = run_config(
        evaluator=evaluator,
        cases=cases,
        top_n=args.baseline_top_n,
        budget=args.baseline_budget,
        existing_rows=state.get("baseline_rows_all", []),
        iterations=args.iterations,
        checkpoint_save=save_checkpoint,
    )
    state["baseline_rows_all"] = baseline_rows_all
    save_checkpoint()

    optimized_rows_all: List[Dict[str, Any]] = run_config(
        evaluator=evaluator,
        cases=cases,
        top_n=args.optimized_top_n,
        budget=args.optimized_budget,
        existing_rows=state.get("optimized_rows_all", []),
        iterations=args.iterations,
        checkpoint_save=save_checkpoint,
    )
    state["optimized_rows_all"] = optimized_rows_all
    save_checkpoint()

    all_rows = baseline_rows_all + optimized_rows_all
    if args.serial_judge:
        run_judge_pass(
            rows=all_rows,
            model_name=args.judge_a_model,
            output_key="judge_a",
            strict_mode=True,
            unload_after=args.unload_between_judges,
            checkpoint_save=save_checkpoint,
            timeout_sec=args.judge_timeout_sec,
            max_retries=args.judge_max_retries,
        )
        run_judge_pass(
            rows=all_rows,
            model_name=args.judge_b_model,
            output_key="judge_b",
            strict_mode=False,
            unload_after=args.unload_between_judges,
            checkpoint_save=save_checkpoint,
            timeout_sec=args.judge_timeout_sec,
            max_retries=args.judge_max_retries,
        )
    else:
        judge_a = OllamaLLM(
            model=args.judge_a_model,
            temperature=0.0,
            base_url=OLLAMA_HOST,
            sync_client_kwargs={"timeout": args.judge_timeout_sec},
        )
        judge_b = OllamaLLM(
            model=args.judge_b_model,
            temperature=0.0,
            base_url=OLLAMA_HOST,
            sync_client_kwargs={"timeout": args.judge_timeout_sec},
        )
        total = len(all_rows)
        for idx, row in enumerate(all_rows, start=1):
            if "judge_a" not in row:
                print(f"🧪 judge_a 评分进度: {idx}/{total} ({row.get('id', '-')})")
                row["judge_a"] = grade_with_judge(
                    judge=judge_a,
                    question=row["question"],
                    answer=row["answer"],
                    context=row["context"],
                    ground_truth=row["ground_truth"],
                    strict_mode=True,
                    max_retries=args.judge_max_retries,
                    trace_label=f"judge_a:{row.get('id', '-')}",
                )
                save_checkpoint()
            if "judge_b" not in row:
                print(f"🧪 judge_b 评分进度: {idx}/{total} ({row.get('id', '-')})")
                row["judge_b"] = grade_with_judge(
                    judge=judge_b,
                    question=row["question"],
                    answer=row["answer"],
                    context=row["context"],
                    ground_truth=row["ground_truth"],
                    strict_mode=False,
                    max_retries=args.judge_max_retries,
                    trace_label=f"judge_b:{row.get('id', '-')}",
                )
                save_checkpoint()
        if args.unload_between_judges:
            try_stop_model(args.judge_a_model)
            if args.judge_b_model != args.judge_a_model:
                try_stop_model(args.judge_b_model)

    for row in all_rows:
        row["judge_merge"] = {
            "faithfulness": round((row["judge_a"]["faithfulness"] + row["judge_b"]["faithfulness"]) / 2.0, 3),
            "relevance": round((row["judge_a"]["relevance"] + row["judge_b"]["relevance"]) / 2.0, 3),
        }
        row["judge_gap"] = {
            "faithfulness": round(abs(row["judge_a"]["faithfulness"] - row["judge_b"]["faithfulness"]), 3),
            "relevance": round(abs(row["judge_a"]["relevance"] - row["judge_b"]["relevance"]), 3),
        }

    def agg(rows: List[Dict[str, Any]], name: str, top_n: int, budget: int) -> Dict[str, Any]:
        table = []
        for r in rows:
            table.append(
                {
                    "latency": r["latency"],
                    "faith_a": r["judge_a"]["faithfulness"],
                    "rel_a": r["judge_a"]["relevance"],
                    "faith_b": r["judge_b"]["faithfulness"],
                    "rel_b": r["judge_b"]["relevance"],
                    "faith_m": r["judge_merge"]["faithfulness"],
                    "rel_m": r["judge_merge"]["relevance"],
                    "gap_f": r["judge_gap"]["faithfulness"],
                    "gap_r": r["judge_gap"]["relevance"],
                }
            )
        return {
            "name": name,
            "top_n": top_n,
            "context_char_budget": budget,
            "latency_mean": summarize(table, "latency"),
            "faithfulness_mean_judge_a": summarize(table, "faith_a"),
            "relevance_mean_judge_a": summarize(table, "rel_a"),
            "faithfulness_mean_judge_b": summarize(table, "faith_b"),
            "relevance_mean_judge_b": summarize(table, "rel_b"),
            "faithfulness_mean_merged": summarize(table, "faith_m"),
            "relevance_mean_merged": summarize(table, "rel_m"),
            "judge_gap_faithfulness_mean": summarize(table, "gap_f"),
            "judge_gap_relevance_mean": summarize(table, "gap_r"),
            "judge_agreement_rate_gap_le_1": round(
                statistics.fmean(
                    [1.0 if t["gap_f"] <= 1.0 and t["gap_r"] <= 1.0 else 0.0 for t in table]
                ),
                3,
            )
            if table
            else 0.0,
            "n": len(rows),
        }

    baseline = agg(baseline_rows_all, "baseline", args.baseline_top_n, args.baseline_budget)
    optimized = agg(optimized_rows_all, "optimized", args.optimized_top_n, args.optimized_budget)
    faith_drop = round(baseline["faithfulness_mean_merged"] - optimized["faithfulness_mean_merged"], 3)
    latency_drop = round((baseline["latency_mean"] - optimized["latency_mean"]) / baseline["latency_mean"] * 100.0, 2) if baseline["latency_mean"] else 0.0

    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_id": args.run_id,
        "judge_a_provider": "ollama",
        "judge_a_model": args.judge_a_model,
        "judge_b_provider": "ollama",
        "judge_b_model": args.judge_b_model,
        "sample_size": args.sample_size,
        "iterations": args.iterations,
        "baseline": baseline,
        "optimized": optimized,
        "acceptance_by_merged_judge": {
            "faithfulness_drop_le_0_2": faith_drop <= 0.2,
            "latency_drop_ge_10_percent": latency_drop >= 10.0,
            "faithfulness_drop": faith_drop,
            "latency_drop_percent": latency_drop,
        },
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    if checkpoint_path.exists():
        checkpoint_path.unlink()
    print(f"SAVED: {out}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

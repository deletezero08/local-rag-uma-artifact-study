#!/usr/bin/env python3
import json
import time
import sys
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.evaluate import RAGEvaluator
from src.config import settings


def mean_metric(iter_rows, key, nested=None):
    flat = [x for it in iter_rows for x in it]
    if not flat:
        return 0.0
    if nested:
        vals = [x.get(nested, {}).get(key, 0.0) for x in flat]
    else:
        vals = [x.get(key, 0.0) for x in flat]
    return sum(vals) / len(vals)


def run_case(evaluator, cases, name, top_n, budget, iterations, run_id):
    settings.setdefault("retrieval", {})["top_n"] = top_n
    settings.setdefault("evaluation", {})["context_char_budget"] = budget
    tag = f"accept_{name}_{run_id}"
    rows = evaluator.evaluate_mode(
        "ensemble",
        cases,
        iterations=iterations,
        checkpoint_tag=tag,
        custom_params={"retrieval": {"top_n": top_n}},
    )
    return {
        "name": name,
        "top_n": top_n,
        "context_char_budget": budget,
        "faithfulness_mean": round(mean_metric(rows, "faithfulness", "scores"), 3),
        "relevance_mean": round(mean_metric(rows, "relevance", "scores"), 3),
        "latency_mean": round(mean_metric(rows, "latency"), 3),
        "n": len([x for it in rows for x in it]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--run-id", type=str, default=time.strftime("%Y%m%d%H%M%S"))
    parser.add_argument("--only", choices=["all", "baseline", "optimized"], default="all")
    parser.add_argument("--baseline-top-n", type=int, default=10)
    parser.add_argument("--baseline-budget", type=int, default=0)
    parser.add_argument("--optimized-top-n", type=int, default=8)
    parser.add_argument("--optimized-budget", type=int, default=3000)
    parser.add_argument("--baseline-file", type=str, default="step1_acceptance_baseline.json")
    parser.add_argument("--optimized-file", type=str, default="step1_acceptance_optimized.json")
    parser.add_argument("--check-file", type=str, default="step1_acceptance_check.json")
    args = parser.parse_args()

    results_dir = Path("results/evaluation")
    results_dir.mkdir(parents=True, exist_ok=True)
    evaluator = RAGEvaluator()
    cases = evaluator._load_question_set()[:args.sample_size]
    if len(cases) < args.sample_size:
        raise RuntimeError(f"question_set 不足 {args.sample_size} 条，当前 {len(cases)}")

    baseline = None
    optimized = None
    if args.only in ("all", "baseline"):
        baseline = run_case(
            evaluator,
            cases,
            "baseline_no_clip",
            args.baseline_top_n,
            args.baseline_budget,
            args.iterations,
            args.run_id,
        )
        Path("results/evaluation").joinpath(args.baseline_file).write_text(json.dumps(baseline, ensure_ascii=False, indent=2), "utf-8")
        if args.only == "baseline":
            print(f"SAVED: results/evaluation/{args.baseline_file}")
            return
    if args.only in ("all", "optimized"):
        opt_name = f"optimized_t{args.optimized_top_n}_b{args.optimized_budget}"
        optimized = run_case(
            evaluator,
            cases,
            "optimized_clip",
            args.optimized_top_n,
            args.optimized_budget,
            args.iterations,
            args.run_id,
        )
        optimized["name"] = opt_name
        optimized["top_n"] = args.optimized_top_n
        optimized["context_char_budget"] = args.optimized_budget
        Path("results/evaluation").joinpath(args.optimized_file).write_text(json.dumps(optimized, ensure_ascii=False, indent=2), "utf-8")
        if args.only == "optimized":
            print(f"SAVED: results/evaluation/{args.optimized_file}")
            return

    if baseline is None:
        baseline_file = Path("results/evaluation").joinpath(args.baseline_file)
        if not baseline_file.exists():
            raise RuntimeError("baseline 缺失，请先运行 --only baseline 或 --only all")
        baseline = json.loads(baseline_file.read_text("utf-8"))
    if optimized is None:
        optimized_file = Path("results/evaluation").joinpath(args.optimized_file)
        if not optimized_file.exists():
            raise RuntimeError("optimized 缺失，请先运行 --only optimized 或 --only all")
        optimized = json.loads(optimized_file.read_text("utf-8"))

    Path("results/evaluation").joinpath(args.baseline_file).write_text(json.dumps(baseline, ensure_ascii=False, indent=2), "utf-8")
    Path("results/evaluation").joinpath(args.optimized_file).write_text(json.dumps(optimized, ensure_ascii=False, indent=2), "utf-8")

    faith_drop = round(baseline["faithfulness_mean"] - optimized["faithfulness_mean"], 3)
    latency_drop_pct = (
        round((baseline["latency_mean"] - optimized["latency_mean"]) / baseline["latency_mean"] * 100.0, 2)
        if baseline["latency_mean"]
        else 0.0
    )

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "ensemble",
        "sample_size": args.sample_size,
        "iterations": args.iterations,
        "baseline": baseline,
        "optimized": optimized,
        "acceptance": {
            "faithfulness_drop_le_0_2": faith_drop <= 0.2,
            "latency_drop_ge_10_percent": latency_drop_pct >= 10.0,
            "faithfulness_drop": faith_drop,
            "latency_drop_percent": latency_drop_pct,
        },
    }
    out = results_dir / args.check_file
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"SAVED: {out}")


if __name__ == "__main__":
    main()

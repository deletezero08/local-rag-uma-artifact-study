#!/usr/bin/env python3
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.evaluate import RAGEvaluator
from src.config import settings

RESULTS_DIR = ROOT_DIR / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def parse_float_list(value: str) -> List[float]:
    return [float(x.strip()) for x in value.split(",") if x.strip()]


def parse_int_list(value: str) -> List[int]:
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def summarize(iterations: List[List[Dict[str, Any]]]) -> Dict[str, float]:
    items = [i for it in iterations for i in it]
    faith = [x.get("scores", {}).get("faithfulness", 0.0) for x in items]
    rel = [x.get("scores", {}).get("relevance", 0.0) for x in items]
    lat = sorted([x.get("latency", 0.0) for x in items])
    ttft_values = [x.get("ttft") for x in items if x.get("ttft") is not None]
    tps_values = [x.get("tokens_per_sec", 0.0) for x in items if x.get("tokens_per_sec") is not None]
    rss_peak_values = [x.get("rss_peak_mb", 0.0) for x in items if x.get("rss_peak_mb") is not None]
    rss_jitter_values = [x.get("rss_peak_delta_mb", 0.0) for x in items if x.get("rss_peak_delta_mb") is not None]
    if not items:
        return {
            "faithfulness": 0.0,
            "relevance": 0.0,
            "latency_mean": 0.0,
            "latency_p90": 0.0,
            "latency_max": 0.0,
            "ttft_mean": 0.0,
            "tokens_per_sec_mean": 0.0,
            "rss_peak_mb_mean": 0.0,
            "rss_peak_delta_mb_mean": 0.0,
            "n": 0
        }
    p90 = lat[int((len(lat) - 1) * 0.9)]
    return {
        "faithfulness": round(sum(faith) / len(faith), 3),
        "relevance": round(sum(rel) / len(rel), 3),
        "latency_mean": round(sum(lat) / len(lat), 3),
        "latency_p90": round(p90, 3),
        "latency_max": round(lat[-1], 3),
        "ttft_mean": round(sum(ttft_values) / len(ttft_values), 3) if ttft_values else 0.0,
        "tokens_per_sec_mean": round(sum(tps_values) / len(tps_values), 3) if tps_values else 0.0,
        "rss_peak_mb_mean": round(sum(rss_peak_values) / len(rss_peak_values), 3) if rss_peak_values else 0.0,
        "rss_peak_delta_mb_mean": round(sum(rss_jitter_values) / len(rss_jitter_values), 3) if rss_jitter_values else 0.0,
        "n": len(items),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", default="ensemble,rrf")
    parser.add_argument("--vector-weights", default="0.5,0.6,0.7,0.8")
    parser.add_argument("--rrf-ks", default="30,45,60")
    parser.add_argument("--iterations", type=int, default=settings.get("evaluation", {}).get("iterations", 1))
    parser.add_argument("--max-combos", type=int, default=0)
    parser.add_argument("--sample-size", type=int, default=0)
    parser.add_argument("--phase-a", action="store_true")
    parser.add_argument("--vector-k", type=int, default=0)
    parser.add_argument("--bm25-k", type=int, default=0)
    parser.add_argument("--fetch-k", type=int, default=0)
    parser.add_argument("--top-n", type=int, default=0)
    parser.add_argument("--context-doc-limit", type=int, default=0)
    parser.add_argument("--context-chars-per-doc", type=int, default=0)
    parser.add_argument("--collect-ttft", action="store_true")
    args = parser.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    vector_weights = parse_float_list(args.vector_weights)
    rrf_ks = parse_int_list(args.rrf_ks)
    combos: List[Dict[str, Any]] = []
    for wv in vector_weights:
        for rk in rrf_ks:
            combos.append({"w_vec": wv, "w_bm25": round(1 - wv, 3), "rrf_k": rk})
    if args.max_combos > 0:
        combos = combos[:args.max_combos]

    run_state_path = RESULTS_DIR / "sweep_run_state.json"
    run_state = load_json(run_state_path, {"done": {}, "rows": []})
    done = run_state.get("done", {})
    rows = run_state.get("rows", [])

    evaluator = RAGEvaluator()
    cases = evaluator._load_question_set()
    if not cases:
        raise RuntimeError("question_set.md 为空，无法执行扫描。")
    if args.sample_size and args.sample_size > 0:
        cases = cases[:args.sample_size]

    for combo in combos:
        for mode in modes:
            phase_tag = "phaseA" if args.phase_a else "base"
            sample_tag = f"n{len(cases)}"
            combo_key = f"{mode}|w{combo['w_vec']:.1f}_b{combo['w_bm25']:.1f}_k{combo['rrf_k']}|{phase_tag}|{sample_tag}"
            if done.get(combo_key):
                continue
            checkpoint_tag = f"w{combo['w_vec']:.1f}_b{combo['w_bm25']:.1f}_k{combo['rrf_k']}_{phase_tag}_{sample_tag}"
            print(f"🚀 Running {combo_key}")
            retrieval_overrides = {
                "weights": {"vector": combo["w_vec"], "bm25": combo["w_bm25"]},
                "rrf_k": combo["rrf_k"]
            }
            if args.vector_k > 0:
                retrieval_overrides["vector_k"] = args.vector_k
            if args.bm25_k > 0:
                retrieval_overrides["bm25_k"] = args.bm25_k
            if args.fetch_k > 0:
                retrieval_overrides["fetch_k"] = args.fetch_k
            if args.top_n > 0:
                retrieval_overrides["top_n"] = args.top_n

            eval_overrides: Dict[str, Any] = {}
            if args.collect_ttft:
                eval_overrides["collect_ttft"] = True
            if args.phase_a:
                eval_overrides["phase_a_context_doc_limit"] = args.context_doc_limit if args.context_doc_limit > 0 else 4
                eval_overrides["phase_a_context_chars_per_doc"] = args.context_chars_per_doc if args.context_chars_per_doc > 0 else 700
                if "vector_k" not in retrieval_overrides:
                    retrieval_overrides["vector_k"] = 8
                if "bm25_k" not in retrieval_overrides:
                    retrieval_overrides["bm25_k"] = 8
                if "fetch_k" not in retrieval_overrides:
                    retrieval_overrides["fetch_k"] = 24
                if "top_n" not in retrieval_overrides:
                    retrieval_overrides["top_n"] = 8

            custom_params = {
                "retrieval": retrieval_overrides,
                "evaluation": eval_overrides
            }
            iter_results = evaluator.evaluate_mode(
                mode,
                cases,
                iterations=args.iterations,
                checkpoint_tag=checkpoint_tag,
                custom_params=custom_params
            )
            ts = int(time.time())
            out = {
                "metadata": {
                    "mode": mode,
                    "config_id": settings.get("config_id", "ablation_study_locked"),
                    "config_version": settings.get("version", "1.2.0"),
                    "n": len(cases),
                    "iterations": args.iterations,
                    "weights": {"vector": combo["w_vec"], "bm25": combo["w_bm25"]},
                    "rrf_k": combo["rrf_k"],
                    "runtime_overrides": custom_params,
                    "phase_a_enabled": args.phase_a,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "iterations": iter_results
            }
            out_name = f"sweep_evaluation_{mode}_w{combo['w_vec']:.1f}_b{combo['w_bm25']:.1f}_k{combo['rrf_k']}_{ts}.json"
            save_json(RESULTS_DIR / out_name, out)
            stat = summarize(iter_results)
            rows.append({
                "mode": mode,
                "weights": {"vector": combo["w_vec"], "bm25": combo["w_bm25"]},
                "rrf_k": combo["rrf_k"],
                "phase_a_enabled": args.phase_a,
                "file": out_name,
                **stat
            })
            done[combo_key] = out_name
            run_state["done"] = done
            run_state["rows"] = rows
            save_json(run_state_path, run_state)

    rows_sorted = sorted(rows, key=lambda x: (-x["faithfulness"], -x["relevance"], x["latency_mean"]))
    summary_name = f"sweep_summary_{int(time.time())}.json"
    summary_payload = {
        "rows": rows_sorted,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_json(RESULTS_DIR / summary_name, summary_payload)
    save_json(RESULTS_DIR / "sweep_summary.json", summary_payload)
    print(f"✅ sweep summary saved: {summary_name}")


if __name__ == "__main__":
    main()

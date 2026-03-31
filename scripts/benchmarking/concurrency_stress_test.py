import time
import json
import os
import sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Note: We must import and initialize pipeline INSIDE the worker process 
# because Llama instances cannot be pickled/shared across processes.
from src.rag_pipeline import MemoraRAGPipeline

# Configuration
MODEL_PATH = "Llama-3-8B-Instruct.Q4_K_M.gguf"
NUM_ROUNDS = 3
CONCURRENCY_LEVELS = [2, 4]
OUTPUT_FILE = "results/evaluation/support_runtime/stress_test_report_v2.json"

def worker_task(query, mock_docs, use_dynamic):
    """
    Worker process entry point.
    Initializes its own pipeline to ensure true UMA bandwidth competition.
    """
    try:
        # Each process loads the 5GB model. 4 processes = 20GB RAM.
        # This will TRULY test the memory bandwidth wall.
        pipeline = MemoraRAGPipeline(model_path=MODEL_PATH, n_ctx=2048) # Reduced ctx per worker
        
        if not use_dynamic:
            pipeline.compressor.keep_ratio = 1.0
            
        result = pipeline.run(query, mock_docs=mock_docs, use_dynamic=use_dynamic)
        
        return {
            "success": True,
            "ttft_ms": result["waterfall"]["llm_prefill_ms"],
            "tokens_generated": result["generated_tokens"],
            "total_ms": result["waterfall"]["total_pipeline_ms"],
            "strategy": result["pruning_strategy"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_concurrent_benchmark(mode_name, use_dynamic, num_users=4):
    print(f"\n{'='*50}")
    print(f"🔥 Starting Multi-Process Stress Test | Mode: [{mode_name}] | N={num_users}")
    print(f"{'='*50}")
    
    query = "Explain the hardware bandwidth limitations when processing large contexts in LLMs."
    mock_docs = [
        f"Context Chunk {i}: UMA on Apple Silicon allows high-bandwidth sharing but is prone to contention. "
        f"Memory bandwidth (roughly 120GB/s to 400GB/s) is the ultimate wall for LLM throughput. "
        for i in range(25) # High volume to ensure significant prefill
    ]
    
    start_wall_clock = time.perf_counter()
    results = []
    
    # Use ProcessPool to ensure true isolation and bandwidth pressure
    with ProcessPoolExecutor(max_workers=num_users) as executor:
        futures = {executor.submit(worker_task, query, mock_docs, use_dynamic): i for i in range(num_users)}
        
        for future in as_completed(futures):
            res = future.result()
            if res["success"]:
                results.append(res)
            else:
                print(f"❌ Worker Failed: {res['error']}")
            
    end_wall_clock = time.perf_counter()
    
    if not results:
        print("🛑 All workers failed. Aborting mode.")
        return None

    # Aggregate Statistics
    total_wall_time = end_wall_clock - start_wall_clock
    ttfts = [r["ttft_ms"] for r in results]
    total_tokens = sum([r["tokens_generated"] for r in results])
    
    p95_ttft = np.percentile(ttfts, 95)
    aggregate_tps = total_tokens / total_wall_time
    
    print(f"⏱️  Total Wall-clock Time: {total_wall_time:.2f} s")
    print(f"📉 P95 Tail Latency (P95 TTFT): {p95_ttft:.2f} ms")
    print(f"🚀 System Aggregate TPS: {aggregate_tps:.2f} tokens/sec")
    
    return {
        "mode": mode_name,
        "wall_time_sec": round(total_wall_time, 2),
        "p95_ttft_ms": round(p95_ttft, 2),
        "aggregate_tps": round(aggregate_tps, 2),
        "strategies_used": list(set([r["strategy"] for r in results]))
    }

if __name__ == "__main__":
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found: {MODEL_PATH}")
        sys.exit(1)

    full_report = {}
    
    for n_users in CONCURRENCY_LEVELS:
        case_id = f"N={n_users}"
        case_results = []
        
        for round_id in range(1, NUM_ROUNDS + 1):
            print(f"\n🌀 Starting Stress Round {round_id} of {NUM_ROUNDS} for {case_id}")
            
            # 1. Baseline: 100% Context
            res_base = run_concurrent_benchmark(f"Baseline (100% Context) - R{round_id}", use_dynamic=False, num_users=n_users)
            
            # 2. SOTA: Gradient-Aware Dynamic Pruning
            res_sota = run_concurrent_benchmark(f"MemoraRAG (Gradient Pruned) - R{round_id}", use_dynamic=True, num_users=n_users)
            
            if res_base and res_sota:
                improvement = (res_base["p95_ttft_ms"] - res_sota["p95_ttft_ms"]) / res_base["p95_ttft_ms"]
                case_results.append({
                    "round": round_id,
                    "baseline_ttft": res_base["p95_ttft_ms"],
                    "sota_ttft": res_sota["p95_ttft_ms"],
                    "reduction_pct": round(improvement * 100, 2)
                })
        
        # Aggregate stats for this N
        baselines = [c["baseline_ttft"] for c in case_results]
        sotas = [c["sota_ttft"] for c in case_results]
        
        full_report[case_id] = {
            "baseline_ttft_mean": round(float(np.mean(baselines)), 2),
            "baseline_ttft_std": round(float(np.std(baselines)), 2),
            "sota_ttft_mean": round(float(np.mean(sotas)), 2),
            "sota_ttft_std": round(float(np.std(sotas)), 2),
            "avg_reduction_pct": round(float(np.mean([c["reduction_pct"] for c in case_results])), 2),
            "raw_rounds": case_results
        }

    print("\n📊 [Final Research Stress Test Consolidated Report]")
    print(json.dumps(full_report, indent=4))
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=4)
    
    print(f"\n✅ Consolidated stress test data saved to: {OUTPUT_FILE}")

#!/usr/bin/env python3
"""
Latex Table 4 Generator (Concurrency Mean ± Std)
Automates N=4 concurrency stress tests on an Ollama-compatible backend.
Must be executed over the local GGUF server to mimic real constraints.
"""
import time
import requests
import numpy as np
import concurrent.futures

# Target Endpoint
OLLAMA_URL = "http://localhost:11434/api/generate"
# You might need to change this backend to llama.cpp's server port depending on your setup
MODEL = "Llama-3-8B-Instruct.Q4_K_M"
PROMPT = "Read the context carefully. What are the core bottlenecks of UMA architecture on Apple Silicon?"

NUM_ROUNDS = 5
CONCURRENCY = 4

def make_request():
    start_time = time.time()
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": PROMPT, "stream": False},
            timeout=180
        )
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            
            # Using prompt_eval_duration in Ollama as TTFT proxy
            ttft_ms = data.get('prompt_eval_duration', 0) / 1e6
            wall_time = end_time - start_time
            eval_count = data.get('eval_count', 0)
            eval_duration_sec = data.get('eval_duration', 1) / 1e9
            tps = eval_count / eval_duration_sec if eval_duration_sec > 0 else 0
            
            return True, wall_time, ttft_ms, tps
        else:
            return False, 0, 0, 0
    except Exception as e:
        return False, 0, 0, 0

def run_round():
    wall_times, ttfts, tpss = [], [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(make_request) for _ in range(CONCURRENCY)]
        for f in concurrent.futures.as_completed(futures):
            success, wt, ttft, tps = f.result()
            if success:
                wall_times.append(wt)
                ttfts.append(ttft)
                tpss.append(tps)
    
    if wall_times:
        # We need P95 TTFT, Wall time (mean of max/batch), Aggregate TPS (sum)
        return np.mean(wall_times), np.percentile(ttfts, 95), np.sum(tpss)
    return 0, 0, 0

def main():
    print(f"🚀 Starting Target Concurrency Benchmarks (Threads={CONCURRENCY}, Rounds={NUM_ROUNDS})")
    print(f"Model target: {MODEL}\n")
    
    round_wall, round_ttft, round_tps = [], [], []
    
    for i in range(NUM_ROUNDS):
        print(f"Firing Round {i+1}/{NUM_ROUNDS}...")
        wt, ttft, tps = run_round()
        if wt > 0:
            round_wall.append(wt)
            round_ttft.append(ttft)
            round_tps.append(tps)
            print(f"  -> Round {i+1} completed. Agg TPS: {tps:.2f}")
        else:
            print("  -> Connection failed or model crashed.")
        time.sleep(3) # Hardware thermal cooldown between concurrent blasts
        
    print("\n\n" + "-"*40)
    print("📊 LATEX READY METRICS (Copy to Table 4)")
    print("-" * 40)
    print(f"Wall Time (s) : ${np.mean(round_wall):.2f} \\pm {np.std(round_wall):.2f}$")
    print(f"P95 TTFT (ms) : ${np.mean(round_ttft):.2f} \\pm {np.std(round_ttft):.2f}$")
    print(f"Aggregate TPS : ${np.mean(round_tps):.2f} \\pm {np.std(round_tps):.2f}$")
    print("-" * 40)

if __name__ == "__main__":
    main()

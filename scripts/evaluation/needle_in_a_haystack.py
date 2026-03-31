import os
import time
import json
import random
import string
import numpy as np
from typing import List, Dict
from src.rag_pipeline import MemoraRAGPipeline

# Configuration
NEEDLE = "反重力引擎的绝密激活码是：NEBULA-VAULT-2026-SOTA-PRO。"
RETRIEVAL_TOP_K = 15
TARGET_CONTEXTS_CHARS = 120000 
OUTPUT_FILE = "results/evaluation/support_runtime/niah_report.json"

def generate_noise_haystack(num_chars: int) -> List[str]:
    """Generate a high-entropy haystack of randomized Chinese text to ensure semantic separation."""
    # Diverse topics to prevent score overcrowding
    topics = [
        "今天的天气预报显示局部地区有阵雨。",
        "这是一个关于量子纠缠的科普片段。",
        "如何在家制作出一碗正宗的担担面？",
        "股市波动受到全球供应链不确定性的影响。",
        "在深海中发现了一种全新的多细胞生物。",
        "足球比赛的最后时刻进球改变了小组排名。"
    ]
    haystack = []
    current_chars = 0
    while current_chars < num_chars:
        # Add random salt to each chunk to maximize semantic entropy
        chunk = random.choice(topics) + "".join(random.choices(string.ascii_letters, k=5))
        haystack.append(chunk)
        current_chars += len(chunk)
    return haystack

def run_niah_test(pipeline: MemoraRAGPipeline, depth_percent: float):
    """Run a single NIAH test with high-entropy haystack."""
    print(f"\n🧵 Testing NIAH (Semantic Separation) at Depth: {depth_percent*100}% | 120k Chars")
    
    # 1. Prepare Haystack
    haystack = generate_noise_haystack(TARGET_CONTEXT_S_CHARS) if 'TARGET_CONTEXT_S_CHARS' in globals() else generate_noise_haystack(120000)
    
    # 2. Insert Needle
    insert_idx = int(len(haystack) * depth_percent)
    haystack.insert(insert_idx, NEEDLE)
    
    query = "反重力引擎的绝密激活码是什么？"
    
    # 3. Execute RAG
    start_time = time.perf_counter()
    result = pipeline.run(query, mock_docs=haystack, use_dynamic=True)
    end_time = time.perf_counter()
    
    total_latency = end_time - start_time
    
    # 4. Success Criteria
    success = "NEBULA-VAULT-2026" in result["answer"]
    
    print(f"⏱️  Latency: {total_latency:.2f} s")
    print(f"✅ Success: {success}")
    print(f"📉 Strategy: {result['pruning_strategy']}")
    
    return {
        "depth": depth_percent,
        "success": success,
        "latency_sec": round(total_latency, 2),
        "strategy": result["pruning_strategy"],
        "answer": result["answer"]
    }

if __name__ == "__main__":
    MODEL_PATH = "Llama-3-8B-Instruct.Q4_K_M.gguf"
    pipeline = MemoraRAGPipeline(model_path=MODEL_PATH)
    
    # Run tests
    depths = [0.0, 0.5, 0.95] # Top, Middle, Bottom-most
    report = []
    
    print(f"{'='*50}")
    print(f"🚀 SOTA NIAH (V3 - Semantic Separation Mode)")
    print(f"{'='*50}")
    
    for d in depths:
        report.append(run_niah_test(pipeline, d))
        
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    
    print(f"\n🏁 SOTA NIAH V3 Complete. Data saved to: {OUTPUT_FILE}")

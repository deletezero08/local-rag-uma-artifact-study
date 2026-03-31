#!/usr/bin/env python3
"""
Latex Figure 5 / Table 2 Generator (Dual-Judge Faithfulness Check)
Uses Qwen3-8B and DeepSeek-R1-8B via Ollama to evaluate the faithfulness of 
answers on the test40 dataset. Outputs Pareto coordinates.
"""
import json
import logging
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
# Standard SCI-grade dual judge pair
JUDGES = ["qwen3:8b", "deepseek-r1:8b"]

def evaluate_faithfulness(model, question, retrieved_context, generated_answer):
    prompt = f"""You are an objective and strict academic judge. 
Your task is to evaluate if the Generated Answer is strictly faithful to the Retrieved Context. 
It must not hallucinate information outside the context.

Question: {question}
Context: {retrieved_context}
Generated Answer: {generated_answer}

Output strictly '1' if the answer is faithful to the context, or '0' if it hallucinates or contradicts.
Do not output any other text or reasoning. ONLY 1 or 0."""
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.0}},
            timeout=120
        )
        if response.status_code == 200:
            text = response.json().get('response', '').strip()
            # Parse the strict 0 or 1
            if '1' in text: return 1.0
            if '0' in text: return 0.0
    except Exception as e:
        print(f"Error querying {model}: {e}")
    return 0.5 # Baseline ambiguous penalty if model fails to parse

def main():
    print("⚖️ Starting Dual-Judge Faithfulness Benchmarking")
    print(f"Judges configured: {JUDGES[0]} [CROSS-CHECK] {JUDGES[1]}\n")
    
    # In a real run, you would load the 40 generations from your `/benchmarks` output:
    # with open('../results/evaluation/run_v2_results.json') as f: data = json.load(f)
    print("Generating mock template data for demonstration (Please point to real run outputs)...\n")
    sample_data = [
        {
            "id": i,
            "question": "What is the primary bottleneck on Apple Silicon UMA?",
            "context": "The unified memory architecture shares bandwidth between CPU and GPU, causing massive contention during heavy decoding and vector retrieval.",
            "answer": "The primary bottleneck is memory bandwidth contention because the unified memory is shared between compute units."
        } for i in range(1, 11) # Dummy 10 items for quick test
    ]
    
    scores = []
    
    for idx, item in enumerate(sample_data):
        j1_score = evaluate_faithfulness(JUDGES[0], item['question'], item['context'], item['answer'])
        j2_score = evaluate_faithfulness(JUDGES[1], item['question'], item['context'], item['answer'])
        
        # Dual-judge merge logic (Average)
        merged_score = (j1_score + j2_score) / 2.0
        scores.append(merged_score)
        print(f"[{idx+1}/{len(sample_data)}] {JUDGES[0]}: {j1_score} | {JUDGES[1]}: {j2_score}  =>  Merged: {merged_score}")
        
    avg_score = (sum(scores) / len(scores)) * 10.0 # Scaling to 10 for table formatting
    
    print("\n\n" + "-"*40)
    print("📊 LATEX READY METRICS (Copy to Table 2 / Fig 5 Pareto)")
    print("-" * 40)
    print(f"Faithfulness Score (Dual/test40) : {avg_score:.3f} / 10.0")
    print("-" * 40)
    print("Note: To run the real test40 benchmark, replace `sample_data` with your actual benchmark JSON loader.")

if __name__ == "__main__":
    main()

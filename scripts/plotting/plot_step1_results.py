#!/usr/bin/env python3
import json
import matplotlib.pyplot as plt
from pathlib import Path

# 环境适配
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS'] 
plt.rcParams['axes.unicode_minus'] = False

ROOT = Path(__file__).resolve().parent.parent.parent
RES_DIR = ROOT / "results" / "evaluation" / "legacy_step1"
OUT_DIR = ROOT / "results" / "figures" / "legacy_step1"

def load_data(file_name):
    p = RES_DIR / file_name
    if not p.exists(): return None
    return json.loads(p.read_text())

def plot_step1_comparison():
    data_a = load_data("step1_dual_judge_test40_t8_b1500.json")
    data_b = load_data("step1_dual_judge_test40_t7_b0.json")
    
    if not data_a or not data_b:
        print("❌ Missing Step 1 data files")
        return

    # 提取指标 (Merged 口径)
    names = ['Baseline', '候选 A (Top-8, Budget=1500)', '候选 B (Top-7, No Clip)']
    
    # 时延
    latencies = [
        (data_a['baseline']['latency_mean'] + data_b['baseline']['latency_mean']) / 2,
        data_a['optimized']['latency_mean'],
        data_b['optimized']['latency_mean']
    ]
    
    # 忠实度
    faithfulness = [
        (data_a['baseline']['faithfulness_mean_merged'] + data_b['baseline']['faithfulness_mean_merged']) / 2,
        data_a['optimized']['faithfulness_mean_merged'],
        data_b['optimized']['faithfulness_mean_merged']
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # 1. 忠实度对比
    bars1 = ax1.bar(names, faithfulness, color=['#cccccc', '#66b3ff', '#99ff99'], alpha=0.8)
    ax1.set_title("回答忠实度对比 (n=40, 双裁判均值)", fontsize=13)
    ax1.set_ylabel("Faithfulness Score (0-10)")
    ax1.set_ylim(7.5, 8.5)
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height, f'{height:.2f}', ha='center', va='bottom')

    # 2. 时延对比
    bars2 = ax2.bar(names, latencies, color=['#cccccc', '#ff9999', '#ffcc99'], alpha=0.8)
    ax2.set_title("端到端时延对比 (n=40)", fontsize=13)
    ax2.set_ylabel("Latency (Seconds)")
    ax2.set_ylim(85, 95)
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height, f'{height:.2f}s', ha='center', va='bottom')

    plt.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "step1_comparison.png", dpi=300)
    print(f"✅ Step 1 comparison saved to: {OUT_DIR}/step1_comparison.png")

if __name__ == "__main__":
    plot_step1_comparison()

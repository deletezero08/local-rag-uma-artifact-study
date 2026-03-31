# Key Results Summary

This file turns the main result JSON files into a compact narrative for a web chat assistant.

## Paper Track Results

### 4-mode ablation summary (`results/evaluation/legacy_misc/ablation_summary.json`)

- `ensemble` has the highest mean faithfulness at `7.333` and the highest mean relevance at `7.817` across `n = 60`.
- `vector_only` is close behind with faithfulness `7.167` and relevance `7.700`.
- `bm25_only` is the fastest of the classic paper-era modes with mean latency `73.549 s`, but has lower quality metrics.
- `rrf` remains usable in quality terms, but its latency is highly unstable with mean `157.174 s` and very large variance.
- Pairwise significance tests among `vector_only`, `ensemble`, and `rrf` are not strong in this summary file; the p-values are all high, so the paper story should not rely on overclaiming quality gaps here.

### Dual-judge test40 results

Candidate A: `results/evaluation/legacy_step1/step1_dual_judge_test40_t8_b1500.json`

- Baseline merged faithfulness: `8.275`
- Optimized merged faithfulness: `8.100`
- Faithfulness drop: `0.175`, which passes the `<= 0.2` acceptance rule
- Latency drop: `1.73%`, which fails the `>= 10%` target

Candidate B: `results/evaluation/legacy_step1/step1_dual_judge_test40_t7_b0.json`

- Baseline merged faithfulness: `8.150`
- Optimized merged faithfulness: `8.162`
- Faithfulness drop: `-0.012`, which passes the acceptance rule
- Latency drop: `3.24%`, which still fails the `>= 10%` target

Paper-side interpretation:

- retrieval-side compression can preserve quality,
- but under strong quality constraints it does not produce a large end-to-end latency win,
- which supports the claim that the dominant bottleneck has shifted to generation.

## Engineering Track Results

### Current paper-track operating point (`results/evaluation/topn_budget_grid_summary.json`)

- `t5_b1500` is the selected operating point from the bounded topn x budget search.
- It is the most balanced current paper-track point among the surviving candidates.
- Nearby alternatives such as `t10_b2000` and `t10_b2500` improve answer-level quality further, but at clearly higher TTFT.

### GGUF model comparison (`results/evaluation/support_runtime/model_comparison.json`)

- `Falcon-7B-Quant`: TTFT `123.7 ms`, TPS `18.09`
- `Llama-3-8B-Quant`: TTFT `51.2 ms`, TPS `19.27`

Interpretation:

- the optimized GGUF route is viable,
- and the Llama-3 GGUF baseline currently has the stronger TTFT profile.

### V1 vs V2 pipeline comparison (`results/evaluation/support_runtime/v2_bench_comparison.json`)

- Representative latency moves from `16.8 s` down to `5.3 s`
- Reported speedup is `3.17x`

Interpretation:

- the engineering line has a clear systems-speed story,
- but this is an engineering benchmark result and should be kept separate from the formal paper evidence track.

### Concurrency stress result (`results/evaluation/support_runtime/stress_test_report.json`)

- Baseline wall time: `134.09 s`
- Optimized wall time: `55.29 s`
- Baseline P95 TTFT: `17435.46 ms`
- Optimized P95 TTFT: `8979.26 ms`
- Aggregate TPS: `3.85 -> 4.67`

Interpretation:

- pruning and runtime optimization materially improve concurrency behavior on constrained hardware.

### NIAH long-context check (`results/evaluation/support_runtime/niah_report.json`)

- `3 / 3` probes succeed
- depths tested: `0.0`, `0.5`, `0.95`
- latency range: `36.85 s` to `39.38 s`

Interpretation:

- the engineering line has retained a basic long-context retrieval signal under the tested setting.

### Keep-ratio tradeoff (`results/tuning/keep_ratio_dense_scan.json`)

- `keep_ratio = 1.0`: TTFT `5828.5 ms`, total E2E `20270.8 ms`
- `keep_ratio = 0.6`: TTFT `874.3 ms`, total E2E `14612.6 ms`
- `keep_ratio = 0.2`: TTFT `2258.0 ms`, total E2E `15760.1 ms`

Interpretation:

- `0.6` is the most important operating point in the current sweep,
- because it remains the more balanced pruning setting under the current protocol.

## One-Sentence Global Takeaway

The paper line shows that quality-preserving retrieval compression has limited end-to-end gains because generation dominates, while the engineering line shows that backend choice, GGUF deployment, and prompt-side compression create the larger practical performance wins.

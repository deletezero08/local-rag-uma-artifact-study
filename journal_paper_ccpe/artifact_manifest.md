# Artifact Manifest

## Scope

This manifest maps the final manuscript claims to the concrete files included in the compact review artifact bundle. It is written for claim tracing rather than for full end-to-end rerun automation.

## Runtime Record

- Device: Mac mini M4
- Memory: 16 GB unified memory
- OS family: macOS on Apple Silicon
- `torch`: 2.10.0
- `transformers`: 4.57.6
- `llama-cpp-python`: 0.3.19
- `llama.cpp`: exercised through `llama-cpp-python`; a separate standalone commit hash was not recorded in the paper-track artifacts

## Model / Backend Records

| Label | Backend | Quant / format | Evidence class | Repeat count | Raw file |
| --- | --- | --- | --- | ---: | --- |
| Falcon-7B on MPS | `transformers + MPS` | imported fp-style baseline | cautionary single-run import | 1 | `results/evaluation/model_comparison_repeated.json` |
| Falcon-7B-Q + GGUF | `GGUF / llama.cpp` | `Q4_K_M` GGUF | repeated measurement | 5 | `results/evaluation/model_comparison_repeated.json` |
| Llama-3-8B-Q + GGUF | `GGUF / llama.cpp` | `Q4_K_M` GGUF | repeated measurement | 5 | `results/evaluation/model_comparison_repeated.json` |

## Search / Probe Settings Used by the Final Paper Track

- bounded `topn x budget` search:
  - `keep_ratio = 0.6`
  - `topn ∈ {5, 7, 8, 10}`
  - `budget ∈ {none, 1500, 2000, 2500}`
  - sample size = 40
- pruning-policy ablation:
  - static reference point = `t5_b1500`
  - `top_k = 5`
  - `budget = 1500`
  - `keep_ratio = 0.6`
  - sample size = 40
- long-context robustness sweep:
  - depths = `0, 25, 50, 75, 90, 95, 99`
  - rounds per depth = 3
  - `n_ctx = 8192`
  - haystack length = `120000` characters

## Manuscript Claim -> Evidence Mapping

| Manuscript location | Claim supported | Primary evidence files | Supporting generation files | Notes |
| --- | --- | --- | --- | --- |
| Section 5.1 / Figure 2 / backend comparison table | GGUF routes remain practically deployable under repeated measurement; MPS remains a cautionary negative baseline | `results/evaluation/model_comparison_repeated.json` | `figures/peerj_submission/figure2_backend_migration.pdf`, `tables/peerj_submission/table1_backend_comparison.tex` | The MPS row is not a repeated benchmark condition. |
| Section 5.2 / Figure 3 | paging / memory-pressure evidence complements wall-time evidence | `results/hardware/swap_mps_real.csv`, `results/hardware/swap_sota_real.csv`, `results/hardware/bandwidth_mps_real.csv` | `figures/peerj_submission/figure3_swap_profile.pdf` | Used as hardware-side evidence rather than PMU-grade proof. |
| Section 5.3 / TurboQuant trade-off tables | TurboQuant lowers footprint and retrieval latency while exposing bounded answer-level trade-offs | `results/evaluation/turboquant_e2e_quality_ablation.json`, `results/evaluation/support_runtime/quantization_quality.json` | `tables/peerj_submission/table3_turboquant_tradeoff.tex`, `tables/peerj_submission/table3b_turboquant_e2e_ablation.tex` | `quantization_quality.json` is included as support-runtime input for the plotting / table layer. |
| Section 5.4 / Figure 4 / component ablation table | `keep_ratio = 0.6` is the current-setting operating point, not a universal optimum | `results/tuning/keep_ratio_dense_scan.json`, `results/evaluation/support_runtime/tradeoff_curve.json` | `figures/peerj_submission/figure4_keep_ratio_tradeoff.pdf`, `tables/peerj_submission/table5_component_ablation.tex` | Dense scan strengthens the operating-point interpretation while retaining the high-variance caveat. |
| Section 5.5 / concurrency stability table | collaborative optimization improves tail latency and throughput under contention, while higher concurrency still exposes backend fragility | `results/evaluation/concurrency_repeat_summary.json`, `results/evaluation/concurrency_tail_latency_report.json`, `results/hardware/concurrency_vmstat_trace.csv` | `tables/peerj_submission/table4_concurrency_stability.tex` | The paper treats this as success-aware concurrency evidence, not as a blanket stability claim. |
| Section 5.6 / long-context robustness table | long-context retrieval remains boundedly robust rather than uniformly solved | `results/evaluation/niah_depth_expanded.json` | `tables/peerj_submission/table7_long_context_robustness.tex` | Failure categories are normalized to `missed` / `partial` in the final manuscript. |
| Section 5.7 / Figure 5 / quality preservation table | the final selected operating point is `t5_b1500`, chosen from a bounded search region rather than ad hoc | `results/evaluation/topn_budget_grid_summary.json`, `results/tuning/topn_budget_grid.json` | `figures/peerj_submission/figure5_quality_latency_frontier.pdf`, `tables/peerj_submission/table2_quality_preservation.tex` | Read `selected_point` in `topn_budget_grid_summary.json`; older baseline/optimized comparison fields are retained only as historical support data. |
| Discussion / E8 pruning-policy ablation | faster pruning variants exist, but `static_ratio_60` remains the more balanced paper-track operating point | `results/evaluation/pruning_policy_ablation.json`, `results/evaluation/failure_casebook.md` | `logs/RESEARCH_LOG.md` | E8 is complete; checkpoint files are intentionally excluded. |
| Section 5.8 / Figure 6 / latency breakdown table | stage-wise decomposition shows that decode remains the dominant residual bottleneck | `results/evaluation/support_runtime/v2_bench_comparison.json`, `results/tuning/keep_ratio_dense_scan.json` | `figures/peerj_submission/figure6_e2e_breakdown.pdf`, `tables/peerj_submission/table6_latency_breakdown.tex` | `v2_bench_comparison.json` is included as a support-runtime artifact. |

## Included Support-Runtime Files

The compact bundle also retains a small set of support-runtime JSON files used by the plotting and table layer:

- `results/evaluation/support_runtime/model_comparison.json`
- `results/evaluation/support_runtime/v2_performance_final.json`
- `results/evaluation/support_runtime/v2_bench_comparison.json`
- `results/evaluation/support_runtime/quantization_quality.json`
- `results/evaluation/support_runtime/tradeoff_curve.json`

These are not the primary paper-track evidence files, but they are kept so that the included plotting helper can regenerate the bundled figure set.

## Rebuild Materials

- manuscript source:
  - `manuscript/main.tex`
  - `manuscript/references.bib`
- final manuscript PDF:
  - `manuscript/main.pdf`
- final figure exports:
  - `figures/peerj_submission/*.pdf`
- final table sources:
  - `tables/peerj_submission/*.tex`
- bundled plotting helper:
  - `scripts/generate_plots.py`

## Exclusions

The following classes of files are intentionally excluded from this bundle:

- model weights
- vector index payloads
- environment directories
- git history
- checkpoints
- LaTeX intermediates
- temporary or abandoned JSON outputs

## Review-Oriented Interpretation Policy

This bundle supports four different evidence classes used by the paper:

- cautionary evidence:
  - `Falcon-7B on MPS`
- repeated deployability evidence:
  - repeated GGUF backend measurements
- trend / operating-point evidence:
  - dense keep-ratio scan and bounded `topn x budget` search
- bounded robustness evidence:
  - expanded NIAH depth sweep

The manuscript's conclusions are intended to be read in that layered sense rather than as universal guarantees.

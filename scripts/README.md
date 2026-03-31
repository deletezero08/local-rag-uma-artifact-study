# Scripts Index

This directory contains the runnable entrypoints for benchmarking, evaluation, plotting, and result maintenance.

## Current Paper-Track Runners

Benchmarking:

- `benchmarking/paper_model_comparison_repeat.py`
- `benchmarking/paper_keep_ratio_repeat.py`
- `benchmarking/paper_concurrency_suite.py`

Evaluation:

- `evaluation/paper_dual_judge_memorarag.py`
- `evaluation/paper_turboquant_e2e_ablation.py`
- `evaluation/paper_niah_depth_expanded.py`
- `evaluation/paper_topn_budget_grid.py`
- `evaluation/paper_pruning_policy_ablation.py`

These are the main current-paper-track scripts that produced the latest evidence under `results/`.

Subdirectory guides:

- [`benchmarking/`](/Users/delete/Desktop/rag_system_副本/scripts/benchmarking/README.md)
- [`evaluation/`](/Users/delete/Desktop/rag_system_副本/scripts/evaluation/README.md)
- [`utils/`](/Users/delete/Desktop/rag_system_副本/scripts/utils/README.md)

## Current Support Scripts

Plotting:

- `plotting/generate_submission_figures.py`
- `plotting/plot_ablation.py`
- `plotting/plot_step1_results.py`

Utilities:

- `utils/paper_p0_manifest.py`
- `utils/aggregate_concurrency_vmstat.py`
- `utils/generate_concurrency_repeat_summary.py`
- `utils/generate_quality_failure_cases.py`
- `utils/generate_failure_casebook.py`
- `utils/select_pareto.py`

## Engineering / Runtime Helpers

- `demo_v2.py`
- `v2_benchmark_orchestrator.py`
- `gui.py`

## Historical Or Compatibility Scripts

- `archive/`
  - old one-off cleanup, patch, and sweep scripts
  - retired plotting helpers tied to old `experiments/results` paths and legacy figure names
- `evaluation/check_step1_acceptance.py`
- `evaluation/dual_judge_acceptance.py`

These are still useful for historical context, but they are not the preferred entrypoints for the latest paper-track evidence.

## Practical Rule

If the task is about the latest manuscript evidence:

1. Start in `benchmarking/paper_*` or `evaluation/paper_*`.
2. Check the matching JSON or CSV under `results/`.
3. Use `utils/` only to aggregate, summarize, or regenerate support material.

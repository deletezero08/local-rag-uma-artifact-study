# Results Index

This directory is the canonical evidence layer for the repository.

## Use These First

Current paper-track evidence:

- `evaluation/model_comparison_repeated.json`
- `evaluation/concurrency_tail_latency_report.json`
- `evaluation/dual_judge_expanded_eval.json`
- `evaluation/turboquant_e2e_quality_ablation.json`
- `evaluation/niah_depth_expanded.json`
- `evaluation/pruning_policy_ablation.json`
- `evaluation/topn_budget_grid_summary.json`
- `evaluation/quality_failure_cases.md`
- `evaluation/topn_budget_failure_cases.md`
- `evaluation/failure_casebook.md`

Current tuning and search outputs:

- `tuning/keep_ratio_repeat_scan.json`
- `tuning/keep_ratio_dense_scan.json`
- `tuning/topn_budget_grid.json`

Current telemetry:

- `hardware/concurrency_vmstat_trace.csv`
- `hardware/concurrency_vmstat/`

## Directory Meanings

- [`evaluation/`](/Users/delete/Desktop/rag_system_副本/results/evaluation/README.md)
  - result files meant to support claims, comparisons, or failure analysis
  - includes physically separated `smoke/`, `legacy_step1/`, `legacy_misc/`, `support_runtime/`, and `support_checks/` subfolders
- [`tuning/`](/Users/delete/Desktop/rag_system_副本/results/tuning/README.md)
  - sweeps, dense scans, and bounded search outputs
  - includes a `smoke/` subfolder for tuning-run validation outputs
- [`hardware/`](/Users/delete/Desktop/rag_system_副本/results/hardware/README.md)
  - vm_stat, swap, and bandwidth telemetry
- `figures/`
  - rendered figures derived from results
- `archive/`
  - historical raw outputs, checkpoints, and old sweep material

## Canonical Vs Support Material

Prefer these:

- non-`smoke` JSON and CSV files
- non-checkpoint summaries
- failure-case markdown files that summarize completed runs

Treat these as support material:

- `evaluation/smoke/*_smoke.json`
- `evaluation/smoke/*_smoke.csv`
- `tuning/smoke/*_smoke.json`
- checkpoint files
- compatibility artifacts from older `step1_*` evaluation lines

## Legacy / Compatibility Files

These are still useful for historical context, but they are not the current paper-track first choice:

- `evaluation/legacy_step1/step1_acceptance_*`
- `evaluation/legacy_step1/step1_dual_judge_*`
- `evaluation/legacy_misc/ablation_summary.json`
- `evaluation/legacy_misc/formal_intent_verification*.json`
- `evaluation/legacy_misc/referential_intent_audit.json`

## Practical Rule

If a task is about the latest manuscript, start with:

1. `evaluation/model_comparison_repeated.json`
2. `evaluation/concurrency_tail_latency_report.json`
3. `evaluation/dual_judge_expanded_eval.json`
4. `evaluation/turboquant_e2e_quality_ablation.json`
5. `evaluation/pruning_policy_ablation.json`
6. `evaluation/topn_budget_grid_summary.json`
7. `tuning/keep_ratio_dense_scan.json`

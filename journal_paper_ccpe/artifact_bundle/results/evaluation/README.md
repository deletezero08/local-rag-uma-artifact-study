# Evaluation Results

This bundle-local folder contains the evaluation outputs retained for manuscript review.

## Primary Paper-Track Evidence

Use these first when validating the current manuscript claims:

- `model_comparison_repeated.json`
- `concurrency_tail_latency_report.json`
- `dual_judge_expanded_eval.json`
- `turboquant_e2e_quality_ablation.json`
- `niah_depth_expanded.json`
- `pruning_policy_ablation.json`
- `topn_budget_grid_summary.json`

Supporting analyses retained in the compact bundle:

- `failure_casebook.md`
- `concurrency_repeat_summary.json`

## Flattened Support Inputs

The bundle also retains a small flat set of support JSON files used by the plotting and table layer:

- `model_comparison.json`
- `v2_performance_final.json`
- `v2_bench_comparison.json`
- `quantization_quality.json`
- `tradeoff_curve.json`

These are useful for traceability and figure regeneration, but they are not the primary
claim-bearing artifacts.

## Bundle Scope

Unlike the full repository, this compact bundle does not preserve separate `support_runtime/`,
`support_checks/`, `legacy_step1/`, `legacy_misc/`, or `smoke/` subtrees. Those categories are
either flattened into the files above or omitted from the compact bundle.

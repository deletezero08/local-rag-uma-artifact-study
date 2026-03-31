# Evaluation Results

This folder contains machine-readable experiment outputs and failure-analysis artifacts.

## Current Paper-Track Evidence

Use these first when validating manuscript claims:

- `model_comparison_repeated.json`
- `concurrency_tail_latency_report.json`
- `dual_judge_expanded_eval.json`
- `turboquant_e2e_quality_ablation.json`
- `niah_depth_expanded.json`
- `pruning_policy_ablation.json`
- `topn_budget_grid_summary.json`

Supporting analyses:

- `quality_failure_cases.md`
- `topn_budget_failure_cases.md`
- `failure_casebook.md`
- `concurrency_repeat_summary.json`
- `cross_device_replication.json`

## Support Material

These are useful, but they are not the current main claim-bearing files:

- `support_runtime/model_comparison.json`
- `support_runtime/niah_report.json`
- `support_runtime/v2_performance_final.json`
- `support_runtime/v2_bench_comparison.json`
- `support_runtime/stress_test_report*.json`
- `support_runtime/turboquant_comparison.json`
- `support_runtime/compression_comparison.json`

These files are stored under `support_runtime/`.

Related runtime-check artifacts such as:

- `support_checks/branded_memory_check.json`
- `support_checks/memory_cross_session_check.json`
- `support_checks/memory_decay_check.json`

are stored under `support_checks/`.

## Legacy / Compatibility Files

These come from older paper-side or acceptance-style evaluation lines:

- `legacy_step1/step1_acceptance_*`
- `legacy_step1/step1_dual_judge_*`
- `legacy_misc/ablation_summary.json`
- `legacy_misc/formal_intent_verification*.json`
- `legacy_misc/referential_intent_audit.json`

Keep them for traceability, but do not treat them as the latest manuscript source of truth by default.
The `step1_*` result files are stored under `legacy_step1/`.
Other legacy paper-side artifacts such as `ablation_summary.json`, `formal_intent_verification*.json`, and `referential_intent_audit.json` are stored under `legacy_misc/`.

## Smoke Outputs

These exist to validate runner wiring and checkpoint behavior:

- `smoke/*_smoke.json`
- `smoke/*_smoke.csv`
- `smoke/*_smoke.md`

They are useful for debugging, not for final paper claims.
Smoke files are stored under `smoke/`.

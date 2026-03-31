# Evaluation Scripts

This folder contains paper-track evaluators, ablations, and legacy evaluation helpers.

## Current Paper-Track Runners

- `paper_dual_judge_memorarag.py`
- `paper_turboquant_e2e_ablation.py`
- `paper_niah_depth_expanded.py`
- `paper_topn_budget_grid.py`
- `paper_pruning_policy_ablation.py`

## Verification And Regression Helpers

- `regression_smoke.py`
- `regression_real_ollama.py`
- `verify_mac_sota.py`
- `verify_v2_sota.py`
- `verify_memory_cross_session.py`
- `verify_memory_decay.py`
- `verify_branded_memory.py`

## Historical / Compatibility Scripts

- `check_step1_acceptance.py`
- `dual_judge_acceptance.py`
- `journal_run_dual_judge.py`

Use these only when a task explicitly needs the older `step1` evaluation line.

# Tuning Results

This folder contains sweeps, dense scans, and bounded-search outputs.

## Current Paper-Track Files

- `keep_ratio_repeat_scan.json`
- `keep_ratio_dense_scan.json`
- `topn_budget_grid.json`

## Historical Or Support Files

- `pareto_selection.json`
- `cliff_sensitivity.json`
- `sweep_summary.json`
- `sweep_run_state.json`
- `step1_tuning_grid_devsplit_pass_v1.json`
- `smoke/topn_budget_grid_smoke.json`

The smoke validation output is stored under `smoke/`.

## Practical Rule

Use `keep_ratio_dense_scan.json` and `topn_budget_grid.json` first when the task is about the latest selected operating point.

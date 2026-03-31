# Scripts Index

This directory contains the reduced script set retained inside the compact review bundle.

## Included Experiment Runners

- `benchmarking/paper_model_comparison_repeat.py`
- `evaluation/journal_run_dual_judge.py`
- `evaluation/paper_turboquant_e2e_ablation.py`
- `evaluation/paper_niah_depth_expanded.py`
- `evaluation/paper_topn_budget_grid.py`
- `evaluation/paper_pruning_policy_ablation.py`

## Included Plotting / Packaging Helpers

- `generate_plots.py`
- `plotting/generate_submission_figures.py`
- `utils/generate_concurrency_repeat_summary.py`
- `utils/generate_failure_casebook.py`

## Practical Rule

- Use `generate_plots.py` first if the goal is to regenerate the bundled figure set.
- Treat the other scripts as retained traceability artifacts rather than as a complete rerun
  environment for the full repository.

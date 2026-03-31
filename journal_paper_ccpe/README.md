# CCPE / PeerJ Paper Workspace

This directory contains the journal-paper working set for the local RAG systems study.

## What lives here

- `main.tex`: primary manuscript source.
- `main.pdf`: latest compiled manuscript output.
- `references.bib`: bibliography source.
- `figures/peerj_submission/`: final figure assets used by `main.tex`.
- `tables/peerj_submission/`: final table fragments included by `main.tex`.
- `submission_bundle/`: packaged copy prepared for submission handoff.
- `generate_plots.py`: plot regeneration entrypoint for the paper figures.
- `figure_style_guide.md` and `artifact_bundle_README.md`: figure and artifact packaging notes.

## Current sources of truth

- Edit `main.tex`, `figures/peerj_submission/`, and `tables/peerj_submission/`.
- Treat `submission_bundle/` as a frozen snapshot that may lag behind the active working set.
- Cross-check manuscript claims against the current paper-track artifacts under `../results/`, especially:
  - `evaluation/model_comparison_repeated.json`
  - `evaluation/concurrency_tail_latency_report.json`
  - `evaluation/dual_judge_expanded_eval.json`
  - `evaluation/turboquant_e2e_quality_ablation.json`
  - `evaluation/topn_budget_grid_summary.json`
  - `evaluation/pruning_policy_ablation.json`
  - `tuning/keep_ratio_dense_scan.json`

## Working conventions

- Edit `main.tex`, figure sources, and table fragments in this directory.
- Treat `submission_bundle/` as a release snapshot, not the primary editing location.
- Keep temporary PDF render checks under `tmp/` only.
- LaTeX auxiliary files such as `*.aux`, `*.log`, and `*.fdb_latexmk` are build artifacts.

## Suggested workflow

1. Update manuscript text in `main.tex`.
2. Regenerate figures if needed.
3. Compile `main.pdf`.
4. Refresh `submission_bundle/` only after the main manuscript is confirmed.

# Project Handoff

This is the best single-file entry point to upload into a web chat assistant before asking for help on this repository.

## What This Repository Is

MemoraRAG is a local RAG research workspace focused on constrained-hardware execution, especially Apple Silicon / UMA settings. The repository currently contains:

- a paper track centered on a journal manuscript and artifact-linked systems evidence,
- an engineering track centered on local runtime, GGUF deployment, and app/API behavior,
- and archived material that still explains how the repository evolved.

Do not treat the repository as one flat storyline.

## The Two Main Tracks

### Paper Track

Purpose:
- support the journal-paper and thesis narrative,
- preserve interpretable evaluation evidence,
- keep claims tied to stable result files.

Primary files and areas:
- `journal_paper_ccpe/`
- `journal_paper_ccpe/main.tex`
- `journal_paper_ccpe/main.pdf`
- `results/evaluation/model_comparison_repeated.json`
- `results/evaluation/concurrency_tail_latency_report.json`
- `results/evaluation/dual_judge_expanded_eval.json`
- `results/evaluation/turboquant_e2e_quality_ablation.json`
- `results/evaluation/niah_depth_expanded.json`
- `results/evaluation/pruning_policy_ablation.json`
- `results/evaluation/topn_budget_grid_summary.json`
- `results/tuning/keep_ratio_dense_scan.json`
- `results/evaluation/failure_casebook.md`

Current paper-side conclusion:
- backend selection, pruning, retrieval compression, and concurrency all matter under a shared UMA budget,
- the final selected operating point is a bounded-search result rather than an ad hoc pick,
- and the residual dominant bottleneck remains decode-side generation after retrieval and prefill are controlled.

### Engineering Track

Purpose:
- improve the local RAG runtime on constrained hardware,
- test GGUF backends, TurboQuant, context compression, long-context robustness, and concurrency behavior,
- keep the practical systems line separate from formal paper claims unless a task explicitly asks to bridge them.

Primary files and areas:
- `main.py`
- `src/rag_pipeline.py`
- `src/turbo_quant.py`
- `src/context_compressor.py`
- `src/retriever.py`
- `scripts/demo_v2.py`
- `scripts/v2_benchmark_orchestrator.py`
- `results/evaluation/model_comparison_repeated.json`
- `results/evaluation/support_runtime/v2_performance_final.json`
- `results/evaluation/support_runtime/v2_bench_comparison.json`
- `results/evaluation/support_runtime/stress_test_report.json`
- `results/evaluation/support_runtime/niah_report.json`
- `results/evaluation/support_runtime/tradeoff_curve.json`

Current engineering-side conclusion:
- `transformers + Falcon-7B + MPS` is an important negative result, not the preferred deployment route,
- the optimized GGUF path is the viable engineering direction,
- the backend and frontend now communicate correctly through the app/API path,
- and the engineering line is useful for runtime and systems analysis, but should not be mixed directly into paper claims unless explicitly requested.

## Important Repository Reality

The repository has been reorganized. Some older logs and archived notes still mention paths like `experiments/results/...`, but those are historical only. The active result files now live under `results/evaluation/`, `results/tuning/`, and their separated subfolders.

When in doubt:
- trust current directories before archived references,
- treat old path mentions as historical breadcrumbs,
- verify whether the same artifact now exists under `results/`.

## Best Files To Read First

1. `README.md`
2. `PROJECT_MAP.md`
3. `results/README.md`
4. `scripts/README.md`
5. `RESEARCH_LOG.md`
6. `journal_paper_ccpe/README.md`

Then branch by task:

- For paper help:
  - `journal_paper_ccpe/main.tex`
  - `journal_paper_ccpe/main.pdf`
  - `thesis/thesis.tex`
  - `results/evaluation/model_comparison_repeated.json`
  - `results/evaluation/concurrency_tail_latency_report.json`
  - `results/evaluation/dual_judge_expanded_eval.json`
  - `results/evaluation/turboquant_e2e_quality_ablation.json`
  - `results/evaluation/topn_budget_grid_summary.json`
  - `results/evaluation/pruning_policy_ablation.json`

- For engineering help:
  - `main.py`
  - `src/rag_pipeline.py`
  - `src/turbo_quant.py`
  - `src/context_compressor.py`
  - `scripts/demo_v2.py`
  - `scripts/v2_benchmark_orchestrator.py`
  - `results/evaluation/model_comparison_repeated.json`
  - `results/evaluation/support_runtime/v2_bench_comparison.json`
  - `results/evaluation/support_runtime/stress_test_report.json`

## Instructions For A Web Chat Assistant

Please follow these rules when helping on this repository:

1. Ask which track the task belongs to if it is ambiguous: paper track or engineering track.
2. Treat `experiments/results/...` as a retired historical path. Use the current `results/` tree directly.
3. Do not mix engineering showcase results into formal paper claims unless explicitly asked.
4. When making suggestions, reference concrete file paths.
5. Treat `submission_bundle/` directories as release snapshots, not the main editing location.
6. Ignore caches, model weights, LaTeX auxiliary files, and temporary render folders unless the task is specifically about them.

## Recommended Upload Sets For Web Chat

### Minimal 3-file set

- `PROJECT_HANDOFF.md`
- `README.md`
- `docs/PROJECT_MAP.md`

### Recommended 8-file set

- `PROJECT_HANDOFF.md`
- `README.md`
- `PROJECT_MAP.md`
- `results/README.md`
- `RESEARCH_LOG.md`
- `src/rag_pipeline.py`
- `main.py`
- `results/evaluation/topn_budget_grid_summary.json`
- `results/evaluation/model_comparison_repeated.json`

### Add these for paper collaboration

- `journal_paper_ccpe/README.md`
- `journal_paper_ccpe/main.tex`
- `journal_paper_ccpe/main.pdf`
- `results/evaluation/dual_judge_expanded_eval.json`
- `results/evaluation/pruning_policy_ablation.json`

## What Not To Upload First

- `.git/`
- `.venv*/`
- `models/`
- `__pycache__/`
- `journal_paper_ccpe/tmp/`
- `.cache/`
- `.mplconfig/`
- `.playwright/`
- LaTeX build files such as `*.aux`, `*.bbl`, `*.blg`, `*.fdb_latexmk`, `*.fls`, `*.log`, `*.out`

## Suggested Prompt To Send With These Files

Use something like this after uploading the recommended files:

`Read PROJECT_HANDOFF.md first. Then explain the current structure of the repository, separate the paper track from the engineering track, identify the canonical files for my current task, and avoid treating smoke outputs, checkpoints, or submission snapshots as the main source of truth unless I explicitly ask for them.`

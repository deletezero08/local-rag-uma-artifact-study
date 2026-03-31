# Project Map

This file explains what is current, what is canonical, and what is mostly historical.

## Read In This Order

1. [README.md](/Users/delete/Desktop/rag_system_副本/README.md)
2. [PROJECT_HANDOFF.md](/Users/delete/Desktop/rag_system_副本/PROJECT_HANDOFF.md)
3. [results/README.md](/Users/delete/Desktop/rag_system_副本/results/README.md)
4. [scripts/README.md](/Users/delete/Desktop/rag_system_副本/scripts/README.md)
5. [RESEARCH_LOG.md](/Users/delete/Desktop/rag_system_副本/RESEARCH_LOG.md)
6. [journal_paper_ccpe/README.md](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/README.md)

## Top-Level Working Sets

- `main.py`
  - current FastAPI app entry
  - serves the frontend from `dist/` when available, with `static/` fallback
  - exposes authenticated `/api/*` routes and health/status endpoints
- `src/`
  - core retrieval, pruning, compression, and runtime logic
- `scripts/`
  - active benchmark, evaluation, plotting, and utility scripts
- `results/`
  - canonical outputs for paper-track evidence and tuning
- `journal_paper_ccpe/`
  - active manuscript workspace
- `docs/`
  - design, deployment, troubleshooting, and reference material
- `thesis/`
  - thesis workspace

## Current Paper Track

Primary manuscript files:

- [journal_paper_ccpe/main.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/main.tex)
- [journal_paper_ccpe/main.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/main.pdf)
- [journal_paper_ccpe/figures/peerj_submission](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission)
- [journal_paper_ccpe/tables/peerj_submission](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/tables/peerj_submission)

Primary evidence files:

- [results/evaluation/model_comparison_repeated.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/model_comparison_repeated.json)
- [results/evaluation/concurrency_tail_latency_report.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/concurrency_tail_latency_report.json)
- [results/evaluation/dual_judge_expanded_eval.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/dual_judge_expanded_eval.json)
- [results/evaluation/turboquant_e2e_quality_ablation.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/turboquant_e2e_quality_ablation.json)
- [results/evaluation/niah_depth_expanded.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/niah_depth_expanded.json)
- [results/evaluation/pruning_policy_ablation.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/pruning_policy_ablation.json)
- [results/evaluation/topn_budget_grid_summary.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/topn_budget_grid_summary.json)
- [results/tuning/keep_ratio_dense_scan.json](/Users/delete/Desktop/rag_system_副本/results/tuning/keep_ratio_dense_scan.json)

Important rule:

- `journal_paper_ccpe/submission_bundle/` is a frozen snapshot, not the preferred editing location.

## Current Engineering Track

Primary runtime files:

- [main.py](/Users/delete/Desktop/rag_system_副本/main.py)
- [src/rag_pipeline.py](/Users/delete/Desktop/rag_system_副本/src/rag_pipeline.py)
- [src/retriever.py](/Users/delete/Desktop/rag_system_副本/src/retriever.py)
- [src/context_compressor.py](/Users/delete/Desktop/rag_system_副本/src/context_compressor.py)
- [src/turbo_quant.py](/Users/delete/Desktop/rag_system_副本/src/turbo_quant.py)
- [src/baselines/](/Users/delete/Desktop/rag_system_副本/src/baselines)

Primary app/frontend areas:

- `dist/`
  - current built frontend
- `public/`
  - static frontend assets used by the build
- `static/`
  - legacy-compatible static assets still mounted by the backend

## Scripts

- [scripts/README.md](/Users/delete/Desktop/rag_system_副本/scripts/README.md)
  - start here before opening individual runners
- `scripts/benchmarking/`
  - backend repeat, keep-ratio repeat, concurrency, swap, and bandwidth scripts
- `scripts/evaluation/`
  - current paper-track evaluators and ablations
- `scripts/plotting/`
  - result plotting helpers
- `scripts/utils/`
  - aggregation, failure-case generation, and manifest helpers
- `scripts/archive/`
  - historical one-off scripts; do not treat as first-choice context

## Results

- [results/README.md](/Users/delete/Desktop/rag_system_副本/results/README.md)
  - current evidence index
- `results/evaluation/`
  - canonical paper-track outputs, plus legacy compatibility artifacts
- `results/tuning/`
  - sweeps and bounded-search outputs
- `results/hardware/`
  - telemetry CSVs such as vm_stat traces
- `results/figures/`
  - rendered figures
- `results/archive/`
  - historical raw outputs and checkpoints

## Historical / Local State

- `.ignore_archive/`
  - archived notes and backups
- `memory/`, `sessions/`, `logs/`, `output/`, `tmp/`
  - local runtime state or temporary output
- `.venv313/`, `node_modules/`, `models/`, `chroma_db/`
  - heavy local dependencies or assets

## Interpretation Rules

1. Prefer current files under `results/`, `scripts/`, and `journal_paper_ccpe/` over archived references.
2. Separate paper-track claims from engineering-track demos unless a task explicitly asks to bridge them.
3. Treat smoke outputs, checkpoints, and archive folders as support material, not canonical evidence.
4. Use `RESEARCH_LOG.md` as the execution trail, but verify the latest canonical artifact before citing a claim.

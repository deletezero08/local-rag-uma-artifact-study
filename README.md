# MemoraRAG

MemoraRAG is a local RAG research workspace with two active lines:

- a paper track centered on reproducible Apple Silicon / UMA systems evidence, and
- an engineering track centered on local runtime, UI/API wiring, and constrained-hardware deployment.

## Start Here

- [PROJECT_HANDOFF.md](/Users/delete/Desktop/rag_system_副本/PROJECT_HANDOFF.md) for the shortest accurate repository handoff.
- [PROJECT_MAP.md](/Users/delete/Desktop/rag_system_副本/PROJECT_MAP.md) for the current top-level map.
- [docs/README.md](/Users/delete/Desktop/rag_system_副本/docs/README.md) for the docs landing page.
- [results/README.md](/Users/delete/Desktop/rag_system_副本/results/README.md) for the current evidence index.
- [scripts/README.md](/Users/delete/Desktop/rag_system_副本/scripts/README.md) for the runnable entrypoints.
- [RESEARCH_LOG.md](/Users/delete/Desktop/rag_system_副本/RESEARCH_LOG.md) for the experiment trail.
- [journal_paper_ccpe/README.md](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/README.md) for the manuscript workspace.

## Current Canonical Areas

```text
main.py              FastAPI app entry, frontend serving, and protected API routes
src/                 runtime pipeline, retriever, compression, and baseline code
scripts/             benchmarking, evaluation, plotting, and utilities
results/             paper-track evidence, tuning outputs, telemetry, and figures
docs/                architecture, deployment, troubleshooting, and reference notes
journal_paper_ccpe/  active journal manuscript, figure assets, and table fragments
thesis/              thesis manuscript workspace
models/              local GGUF models and vector-index assets
```

## Paper Track Sources Of Truth

- Manuscript: [journal_paper_ccpe/main.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/main.tex)
- Latest PDF: [journal_paper_ccpe/main.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/main.pdf)
- Backend repeat: [results/evaluation/model_comparison_repeated.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/model_comparison_repeated.json)
- Concurrency tails: [results/evaluation/concurrency_tail_latency_report.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/concurrency_tail_latency_report.json)
- Quality expansion: [results/evaluation/dual_judge_expanded_eval.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/dual_judge_expanded_eval.json)
- TurboQuant E2E ablation: [results/evaluation/turboquant_e2e_quality_ablation.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/turboquant_e2e_quality_ablation.json)
- Pruning-policy ablation: [results/evaluation/pruning_policy_ablation.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/pruning_policy_ablation.json)
- Bounded topn x budget search: [results/evaluation/topn_budget_grid_summary.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/topn_budget_grid_summary.json)
- Keep-ratio scan: [results/tuning/keep_ratio_dense_scan.json](/Users/delete/Desktop/rag_system_副本/results/tuning/keep_ratio_dense_scan.json)

## Engineering Track Sources Of Truth

- App/API entry: [main.py](/Users/delete/Desktop/rag_system_副本/main.py)
- Current RAG controller: [src/rag_pipeline.py](/Users/delete/Desktop/rag_system_副本/src/rag_pipeline.py)
- Runtime demos and orchestration: [scripts/demo_v2.py](/Users/delete/Desktop/rag_system_副本/scripts/demo_v2.py), [scripts/v2_benchmark_orchestrator.py](/Users/delete/Desktop/rag_system_副本/scripts/v2_benchmark_orchestrator.py)

## Working Rules

- Edit active paper files in `journal_paper_ccpe/`, not in `journal_paper_ccpe/submission_bundle/`.
- Treat `results/` as evidence, not scratch space.
- Treat `results/archive/` and `scripts/archive/` as historical context.
- Prefer `dist/` for the frontend build output; `static/` remains as legacy-compatible assets.
- Keep temporary output in `tmp/`, `output/`, or other clearly non-canonical folders.

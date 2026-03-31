# Project Map

This file is the quickest way to orient a new contributor or a chat assistant.

## 1. What This Repository Is

MemoraRAG is a local RAG workspace with two related tracks:

- The paper track, which preserves the experimental evidence used in the journal and thesis writing.
- The engineering track, which explores backend choice, retrieval compression, and context pruning on constrained hardware.

## 2. Read This In Order

1. [README.md](/Users/delete/Desktop/rag_system_副本/README.md)
2. [PROJECT_HANDOFF.md](/Users/delete/Desktop/rag_system_副本/PROJECT_HANDOFF.md)
3. [results/README.md](/Users/delete/Desktop/rag_system_副本/results/README.md)
4. [scripts/README.md](/Users/delete/Desktop/rag_system_副本/scripts/README.md)
5. [RESEARCH_LOG.md](/Users/delete/Desktop/rag_system_副本/RESEARCH_LOG.md)
6. [journal_paper_ccpe/README.md](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/README.md)

## 3. Core Areas

- `src/`: main Python implementation.
- `scripts/`: evaluation, benchmarking, plotting, and maintenance scripts.
- `data/eval/`: datasets and question sets.
- `results/`: saved experiment outputs and figures.
- `docs/`: design notes, deployment specs, archived summaries.
- `journal_paper_ccpe/`: journal manuscript workspace.
- `thesis/`: thesis manuscript workspace.
- `models/`: local model and vector-index assets.

## 4. Where To Look For Specific Work

- For runtime behavior, inspect `src/rag_pipeline.py`, `src/retriever.py`, and `src/context_compressor.py`.
- For app behavior, inspect `main.py`, `dist/`, and `public/`.
- For evaluation evidence, inspect `results/evaluation/` and `results/tuning/`.
- For result triage, inspect `results/README.md`.
- For runnable entrypoints, inspect `scripts/README.md`.
- For paper assets, inspect `journal_paper_ccpe/main.tex`, `journal_paper_ccpe/figures/`, and `journal_paper_ccpe/tables/`.
- For thesis flow, inspect `thesis/THESIS_WORKFLOW.md` and `thesis/thesis.tex`.
- For API and deployment notes, inspect `docs/A_api/`, `docs/B_deploy/`, and `docs/E_config/`.
- For architecture and design notes, inspect `docs/D_design/` and `docs/specs/`.
- For troubleshooting, inspect `docs/C_troubleshoot/`.

## 5. Maintenance Rules

- Treat `results/` and `benchmarks/` as evidence, not scratch space.
- Treat `submission_bundle/` as a packaged snapshot.
- Keep temporary renders and build artifacts in ignored `tmp/` directories.
- Prefer adding notes and maps over moving source files unless a move is clearly necessary.
- Keep the project story split into "paper track" and "engineering track" when writing summaries.
- Treat smoke outputs and checkpoints as support material unless a task explicitly asks for them.

## 6. If You Need To Export Context For Chat

Use the following hierarchy:

1. `PROJECT_HANDOFF.md` for the shortest accurate export.
2. `README.md` for the high-level repository story.
3. `results/README.md` for the evidence path.
4. `scripts/README.md` for the execution path.
5. `RESEARCH_LOG.md` plus the relevant JSON result file for the exact evidence trail.

If you need to send a small handoff to chat, include:

1. The current goal in one sentence.
2. The exact track you are working on, paper or engineering.
3. The single most relevant source file or result file.
4. Any file paths that must not be edited.

# Chat Context Handoff

This folder is a curated export package for handing the repository to a web chat assistant.

## Repository Identity

MemoraRAG is a local RAG research workspace focused on constrained-hardware execution, especially Apple Silicon / UMA settings. The repository currently contains two active tracks that must be kept separate:

- Paper track: thesis and journal evidence, manuscript drafting, and formal evaluation interpretation.
- Engineering track: GGUF-based runtime optimization, TurboQuant, context compression, and systems benchmarking.

## What A Chat Assistant Must Understand First

1. This repository is not one flat storyline.
2. Old logs may still reference `experiments/results/...`, but that path is retired. Active results now live under `results/evaluation/`, `results/tuning/`, and their separated subfolders.
3. Engineering showcase results should not be mixed directly into formal paper claims unless explicitly requested.

## Best First Files To Upload

- `PROJECT_HANDOFF.md`
- `README.md`
- `docs/PROJECT_MAP.md`

If the task is paper-focused, also upload:

- `journal_paper_ccpe/README.md`
- `journal_paper_ccpe/main.tex`
- `journal_paper_ccpe/main.pdf`

If the task is engineering-focused, also upload:

- `main.py`
- `src/rag_pipeline.py`
- `src/turbo_quant.py`
- `src/context_compressor.py`
- `scripts/demo_v2.py`
- `results/evaluation/support_runtime/model_comparison.json`
- `results/evaluation/support_runtime/stress_test_report.json`

## Rules For The Assistant

1. Ask whether the task belongs to the paper track or the engineering track if that is unclear.
2. Treat `experiments/results/...` as historical only and use the current `results/` tree directly.
3. Cite concrete file paths when making recommendations.
4. Ignore caches, model weights, LaTeX auxiliary files, and temporary render folders unless the task is specifically about them.

## Suggested Prompt

Use this together with the uploaded files:

`Read the handoff and map first. Separate the paper track from the engineering track, summarize what this repository currently does, identify the most relevant files for my task, and ask only the minimum clarifying questions before helping.`

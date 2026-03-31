# Chat Runbook

## Purpose

Use this file when preparing a web chat assistant to help on this repository.

## Step 1: Decide The Track

Before asking for help, state one of these clearly:

- `paper track`
- `engineering track`
- `repo organization`

If you do not do this, the assistant may mix manuscript evidence with engineering benchmark results.

## Step 2: Upload The Smallest Useful Context

For orientation only:

- `PROJECT_HANDOFF.md`
- `README.md`
- `docs/PROJECT_MAP.md`

For paper help:

- the orientation set above
- `journal_paper_ccpe/README.md`
- `journal_paper_ccpe/main.tex`
- `journal_paper_ccpe/main.pdf`
- one or two relevant result JSON files from `results/evaluation/`

For engineering help:

- the orientation set above
- `src/rag_pipeline.py`
- `src/turbo_quant.py`
- `src/context_compressor.py`
- `scripts/demo_v2.py`
- one or two relevant result JSON files from `results/evaluation/`

## Step 3: What To Mention In Plain Language

Include these facts in your prompt if they matter:

- the repository was reorganized and `experiments/results/...` is now only a historical reference, not a live path
- current active results mostly live under `results/evaluation/` and `results/tuning/`
- `main.py` is the current app/API entry and still uses the older `src.engine` runtime stack
- `scripts/demo_v2.py` and `src/rag_pipeline.py` belong to the newer engineering path
- `config.yaml` is a thesis-era locked experiment config and should not automatically be assumed to drive the engineering path

## Step 4: Good Task Framing

Good examples:

- `Help me revise the paper narrative around the bottleneck shift claim using the uploaded result files.`
- `Help me understand the engineering path around src/rag_pipeline.py and suggest what to optimize next.`
- `Help me reorganize the docs without changing the runtime code.`

Less good:

- `Understand my whole project and fix everything.`

## Step 5: Files To Avoid Uploading Early

- `models/`
- `.git/`
- `.venv*/`
- caches and temp folders
- LaTeX auxiliary files
- large raw artifacts that do not explain the project structure

## Optional Local Entry Points

These are useful when the assistant asks what to run:

- `python main.py`
  - current app/API path using the older runtime stack

- `PYTHONPATH=. python scripts/demo_v2.py`
  - simple engineering-path demo entry

- `PYTHONPATH=. python scripts/evaluation/verify_mac_sota.py`
  - engineering-path verification entry mentioned in project docs

## Recommended Prompt Template

`Read the uploaded handoff files first. Separate the paper track from the engineering track. Tell me which files matter most for my task, what parts of the repository are current versus historical, and what the next concrete step should be.`

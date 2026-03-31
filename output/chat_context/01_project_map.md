# Project Map For Chat

## Reading Order

1. `PROJECT_HANDOFF.md`
2. `README.md`
3. `results/README.md`
4. `scripts/README.md`
5. `RESEARCH_LOG.md`
6. `journal_paper_ccpe/README.md`

## Main Areas

- `src/`
  - Core implementation.
  - `rag_pipeline.py` is the main engineering-path runtime entry.
  - Some older files in the repository belong to legacy or paper-era flows.

- `scripts/`
  - Benchmarking, evaluation, plotting, and utility scripts.
  - `demo_v2.py` is the simplest engineering entry for interactive runs.
  - `v2_benchmark_orchestrator.py` is a heavier benchmark script for the engineering line.

- `results/evaluation/`
  - Main location for active JSON result artifacts.
  - Use this as the first evidence layer before reading older logs.
  - Legacy, smoke, and support artifacts are physically separated into subfolders such as `legacy_step1/`, `legacy_misc/`, `smoke/`, `support_runtime/`, and `support_checks/`.

- `results/tuning/`
  - Tuning sweeps, Pareto selections, and threshold scans.

- `docs/`
  - Design, deployment, troubleshooting, and archived project summaries.
  - Use `docs/archive/项目现状摘要.md` when you need historical context about the repository split.

- `journal_paper_ccpe/`
  - Journal manuscript workspace.
  - `main.tex` is the main paper source.
  - `submission_bundle/` is a release snapshot, not the preferred edit target.

- `thesis/`
  - Thesis manuscript workspace and thesis-specific assets.

- `models/`
  - Large local artifacts and vector indices.
  - Usually do not upload these to web chat.

## Path Drift Warning

Some older notes still mention retired paths such as:

- `experiments/results/...`
- `benchmarks/...`
- older thesis-writing folders

Do not expect compatibility links at those old locations. Check whether the active equivalent now lives under:

- `results/evaluation/`
- `results/tuning/`
- `journal_paper_ccpe/`
- `thesis/`

## Quick Routing

- For paper questions:
  - start from `journal_paper_ccpe/main.tex`
  - then use `results/evaluation/topn_budget_grid_summary.json`
  - then use `results/evaluation/pruning_policy_ablation.json`
  - use `results/evaluation/legacy_misc/ablation_summary.json` and `results/evaluation/legacy_step1/` only when thesis-era legacy evidence is explicitly needed

- For engineering questions:
  - start from `main.py` for the app/API path
  - or `src/rag_pipeline.py` for the newer engineering path
  - then `src/turbo_quant.py`
  - then `src/context_compressor.py`
  - then `results/evaluation/support_runtime/model_comparison.json`, `support_runtime/v2_bench_comparison.json`, and `support_runtime/stress_test_report.json`

# Artifact Bundle README

This directory is the compact review artifact bundle for the manuscript:

**An Artifact-Backed Empirical Study of Collaborative Local RAG Execution on Constrained Unified-Memory Devices**

The bundle is organized around the three layers described in Section 8 of the manuscript:

- evidence layer: final result files that support the paper's claims
- generation layer: manuscript source, figure exports, table sources, and key scripts
- metadata layer: this README, the artifact manifest, and the research log

## Start Here

For a fast review pass, open these files in order:

1. `manuscript/main.pdf`
2. `artifact_manifest.md`
3. `results/evaluation/topn_budget_grid_summary.json`
4. `results/evaluation/pruning_policy_ablation.json`
5. `results/evaluation/failure_casebook.md`

This sequence covers the main paper-track operating point, the final pruning-policy comparison, and the final qualitative failure inventory.

## Directory Layout

- `README.md`
  Review-oriented entry point for the bundle.
- `artifact_manifest.md`
  Section / table / figure to evidence-file mapping.
- `manuscript/`
  Final manuscript source and compiled PDF.
- `results/evaluation/`
  Final paper-track evaluation outputs.
- `results/tuning/`
  Tuning and bounded-search outputs used by the final operating-point analysis.
- `results/hardware/`
  Paging and memory-pressure traces used by the hardware-side evidence.
- `figures/`
  Final figure exports.
- `tables/`
  Final table source files.
- `scripts/`
  Key figure-generation and evaluation scripts retained for traceability.
- `logs/`
  Research log with final E7/E8 completion entries.

## What Is Included

The bundle includes the final result files referenced by the current manuscript, including:

- repeated backend comparison results
- success-aware concurrency summaries
- dual-judge answer-quality outputs
- bounded `topn x budget` search summaries
- long-context robustness sweep results
- pruning-policy ablation results
- final failure casebook

It also includes the final figure PDFs, table sources, and a bundle-local copy of `scripts/generate_plots.py`.

## What Is Not Included

The bundle deliberately excludes:

- model weights and vector index payloads
- `.git`, virtual environments, caches, and node modules
- LaTeX intermediate build files
- old checkpoints and abandoned temporary outputs

As a result, the bundle is intended to support **review, inspection, and claim tracing**, not a full from-scratch rerun of every experiment.

## Rebuilding the Manuscript

The manuscript copy under `manuscript/` is self-contained with local figure and table assets. To rebuild the PDF:

```bash
cd manuscript
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

## Rebuilding the Included Figure Set

The bundle-local plotting helper is:

- `scripts/generate_plots.py`

This copy has been adjusted to read bundled result files and write to:

- `manuscript/figures/peerj_submission/`

Example:

```bash
cd artifact_bundle
/Users/delete/Desktop/rag_system_副本/.venv313/bin/python scripts/generate_plots.py
```

This recreates the included manuscript figure set from the bundled result files and support-runtime JSON inputs.

## Review Notes

- The backend comparison preserves the `Falcon-7B on MPS` row as **cautionary evidence** rather than as a repeated benchmark condition.
- The final paper-track operating point is `t5_b1500`.
- The pruning-policy ablation confirms that faster policies exist, but `static_ratio_60` remains the more balanced paper-track operating point under the current protocol.
- The long-context sweep is intentionally framed as a **bounded robustness signal**, not a universal scaling guarantee.

## Final Consistency Checks Already Reflected Here

- E7 final operating-point wording is aligned across Section 5.7, Figure 5, the quality-preservation table, and Discussion.
- E8 is complete and reflected in both `pruning_policy_ablation.json` and `logs/RESEARCH_LOG.md`.
- The bundle contains final artifacts only; checkpoint files are excluded.

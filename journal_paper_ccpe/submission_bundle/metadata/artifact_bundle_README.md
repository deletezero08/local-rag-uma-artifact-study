# Artifact Bundle README

## Overview

This artifact bundle supports the manuscript:

**Collaborative Optimization of Local RAG Execution on Constrained Unified Memory Devices**

The manuscript studies local RAG execution on constrained Apple Silicon hardware and evaluates a collaborative optimization path spanning:

- quantized deployment with GGUF,
- lightweight local inference backends,
- retrieval-side compression with TurboQuant,
- and keep-ratio-based context pruning.

The bundle is organized so that the main numerical claims in the paper can be traced back to benchmark outputs, figure-generation scripts, table sources, and the manuscript source itself.

## Directory Structure

- [main.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/main.tex): manuscript source
- [main.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/main.pdf): compiled anonymous manuscript
- [references.bib](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/references.bib): bibliography source
- [figures/peerj_submission](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission): submission figures
- [tables/peerj_submission](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/tables/peerj_submission): submission tables
- [peerj_submission_preflight_checklist.md](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/peerj_submission_preflight_checklist.md): final submission checklist

Primary benchmark sources live outside this subdirectory:

- [model_comparison.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/model_comparison.json)
- [v2_performance_final.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/v2_performance_final.json)
- [tradeoff_curve.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/tradeoff_curve.json)
- [stress_test_report.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/stress_test_report.json)
- [stress_test_report_v2.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/stress_test_report_v2.json)
- [quantization_quality.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/quantization_quality.json)
- [RESEARCH_LOG.md](/Users/delete/Desktop/rag_system_副本/RESEARCH_LOG.md)

## Mapping from Evidence to Manuscript Claims

### Backend comparison

- Manuscript location: `Results -> Backend and quantized deployment comparison`
- Figure: [figure2_backend_migration.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission/figure2_backend_migration.pdf)
- Table: [table1_backend_comparison.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/tables/peerj_submission/table1_backend_comparison.tex)
- Source benchmarks:
  - [model_comparison.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/model_comparison.json)
  - [v2_performance_final.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/v2_performance_final.json)

### TurboQuant trade-off

- Manuscript location: `Results -> Retrieval compression trade-off`
- Table: [table3_turboquant_tradeoff.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/tables/peerj_submission/table3_turboquant_tradeoff.tex)
- Source benchmark:
  - [quantization_quality.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/quantization_quality.json)

### Keep-ratio context pruning

- Manuscript location: `Results -> Context pruning and TTFT`
- Figure: [figure3_keep_ratio_tradeoff.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission/figure3_keep_ratio_tradeoff.pdf)
- Source benchmark:
  - [tradeoff_curve.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/tradeoff_curve.json)

### Concurrency stability

- Manuscript location: `Results -> System stability under concurrency`
- Table: [table4_concurrency_stability.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/tables/peerj_submission/table4_concurrency_stability.tex)
- Source benchmarks:
  - [stress_test_report.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/stress_test_report.json)
  - [stress_test_report_v2.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/stress_test_report_v2.json)

### Quality preservation

- Manuscript location: `Results -> Quality preservation under compression`
- Table: [table2_quality_preservation.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/tables/peerj_submission/table2_quality_preservation.tex)
- Source benchmarks:
  - [step1_dual_judge_test40_t8_b1500.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/step1_dual_judge_test40_t8_b1500.json)
  - [step1_dual_judge_test40_t7_b0.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/step1_dual_judge_test40_t7_b0.json)

### End-to-end breakdown

- Manuscript location: `Results -> End-to-end latency decomposition`
- Figure: [figure4_e2e_breakdown.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission/figure4_e2e_breakdown.pdf)
- Source benchmarks:
  - [v2_bench_comparison.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/v2_bench_comparison.json)
  - [tradeoff_curve.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/tradeoff_curve.json)

## Regenerating Figures

Figure generation is driven by:

- [generate_submission_figures.py](/Users/delete/Desktop/rag_system_副本/scripts/generate_submission_figures.py)

Example command:

```bash
MPLCONFIGDIR='/Users/delete/Desktop/rag_system_副本/.mplconfig' \
'/Users/delete/Desktop/rag_system_副本/.venv313/bin/python' \
'/Users/delete/Desktop/rag_system_副本/scripts/generate_submission_figures.py'
```

Outputs are written to:

- [figures/peerj_submission](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission)

## Regenerating the Manuscript PDF

From:

- [journal_paper_ccpe](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe)

Run:

```bash
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

The anonymous/non-anonymous title block is controlled in:

- [main.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/main.tex)

with:

```tex
\anonymizedtrue
% \anonymizedfalse
```

## Runtime Notes

- The current experiments are centered on a Mac mini M4 with 16GB unified memory.
- The manuscript contains both positive and negative deployment results.
- The `transformers + MPS` route is intentionally retained as negative-result evidence rather than discarded as a failed attempt.

## Intended Review-Period Packaging

For a review-period submission, the recommended compact artifact package should include:

- manuscript source and bibliography,
- final anonymous PDF,
- benchmark JSON files used by the main result sections,
- figure-generation script,
- table sources,
- a short environment note describing hardware, runtime, and Python/TeX dependencies.

Repository URL, DOI, or public artifact link can be inserted after anonymization is lifted.

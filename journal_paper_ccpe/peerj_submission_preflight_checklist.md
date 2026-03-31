# PeerJ CS Submission Preflight Checklist

## 1. Manuscript Metadata

- [ ] Replace the anonymous title-page block in [main.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/main.tex) with the non-anonymous version when submission mode no longer requires anonymity.
- [ ] Fill in author names, affiliations, and contact email.
- [ ] Confirm the final paper title.
- [ ] Verify keyword order and wording.

## 2. Abstract and Framing

- [ ] Ensure the abstract states the problem, hardware setting, method, and bounded conclusions.
- [ ] Keep the central framing consistent: this is a systems co-design paper for constrained local RAG execution.
- [ ] Avoid overstating quality preservation or implying universal superiority.

## 3. Figures and Tables

- [ ] Verify that all figures render sharply in the PDF version.
- [ ] Confirm that figure captions match the wording used in the Results section.
- [ ] Confirm that table captions and table notes use the same terminology as the text.
- [ ] Recheck whether the current single-column figure widths remain visually balanced after any future text edits.

Core assets:
- [figure1_system_architecture.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission/figure1_system_architecture.pdf)
- [figure2_backend_migration.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission/figure2_backend_migration.pdf)
- [figure3_swap_profile.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission/figure3_swap_profile.pdf)
- [figure4_keep_ratio_tradeoff.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission/figure4_keep_ratio_tradeoff.pdf)
- [figure5_quality_latency_frontier.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission/figure5_quality_latency_frontier.pdf)
- [figure6_e2e_breakdown.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/figures/peerj_submission/figure6_e2e_breakdown.pdf)
- [table1_backend_comparison.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/tables/peerj_submission/table1_backend_comparison.tex)
- [table2_quality_preservation.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/tables/peerj_submission/table2_quality_preservation.tex)
- [table3_turboquant_tradeoff.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/tables/peerj_submission/table3_turboquant_tradeoff.tex)
- [table4_concurrency_stability.tex](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/tables/peerj_submission/table4_concurrency_stability.tex)

## 4. Evidence and Reproducibility

- [ ] Verify that every key numerical claim in the manuscript can be traced to a benchmark artifact or log.
- [ ] Prepare a compact artifact bundle containing benchmark JSON files, plotting scripts, table sources, and the manuscript source.
- [ ] Create a short README for the artifact bundle describing runtime environment, scripts, and expected outputs.
- [ ] Decide whether review-period submission will provide a private artifact link, a blinded repository, or only a data-availability statement.

Key evidence files:
- [model_comparison.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/support_runtime/model_comparison.json)
- [v2_performance_final.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/support_runtime/v2_performance_final.json)
- [tradeoff_curve.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/support_runtime/tradeoff_curve.json)
- [stress_test_report.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/support_runtime/stress_test_report.json)
- [stress_test_report_v2.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/support_runtime/stress_test_report_v2.json)
- [quantization_quality.json](/Users/delete/Desktop/rag_system_副本/results/evaluation/support_runtime/quantization_quality.json)
- [RESEARCH_LOG.md](/Users/delete/Desktop/rag_system_副本/RESEARCH_LOG.md)

## 5. References

- [ ] Check whether 2--4 additional references on context pruning or efficient local inference should be added.
- [ ] Confirm consistent citation style throughout the manuscript.
- [ ] Make sure all bibliography entries are complete enough for submission.

## 6. Claims and Scope Control

- [ ] Keep the negative-result framing explicit: the MPS route is evidence, not rhetorical contrast.
- [ ] Preserve the distinction between engineering significance and statistical significance.
- [ ] Avoid turning this paper into a general RAG-method paper; keep the focus on constrained execution and generation-side bottlenecks.
- [ ] Ensure that quality-preservation language remains bounded to the current benchmark setting.

## 7. Final Output Checks

- [ ] Recompile [main.pdf](/Users/delete/Desktop/rag_system_副本/journal_paper_ccpe/main.pdf) after every substantial edit.
- [ ] Do a final page-by-page visual review for caption overflow, awkward page breaks, and figure/table placement.
- [ ] Export a final anonymous PDF and a final non-anonymous PDF.

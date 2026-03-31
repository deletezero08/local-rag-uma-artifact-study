# Figure Fix Log

## Purpose
This log is used to keep figure wording, axes, source files, and manuscript claims aligned during the PeerJ revision cycle.

## Active issues

### Figure 1
- Target role: four-stage system architecture figure.
- Current risk:
  - the graphic may still over-emphasize engineering structure over the paper's stage-wise logic.
- Planned fixes:
  - redraw as `Retrieval -> Compression -> Prompt Construction -> Inference / Telemetry`
  - move `shared unified-memory budget` into a dedicated bottom strip
  - keep contribution labels visible but not promotional

### Figure 3
- Target role: paging / telemetry evidence.
- Current risk:
  - the text claims the optimized path is nearly paging-free, but the trace still shows visible spikes.
- Planned fixes:
  - align phases temporally
  - or split into two panels
  - ensure the caption matches the exact plotted quantity

### Figure 4 / Figure 5
- Target role: stage-wise latency decomposition.
- Current risk:
  - captions and panel semantics can drift if the layout changes.
- Planned fixes:
  - if the plot only keeps TTFT/TPS-related panels, remove `total E2E dashed boundary` from the caption
  - keep stage colors semantically consistent
  - ensure panel titles and the caption use the same terminology

## Figure material checklist

| Figure | Source file | Metric definition | Included runs | Excluded runs | Axis scale | Caption checked | Matches main text | Notes |
|--------|-------------|------------------|---------------|---------------|------------|-----------------|------------------|-------|
| Fig1 | figures/peerj_submission/figure1_system_architecture.pdf | pipeline structure | current manuscript run | n/a | linear | NO | NO | redraw as 4-stage layout |
| Fig2 | figures/peerj_submission/figure2_backend_migration.pdf | TTFT/TPS/latency backend comparison | backend comparison set | failed plotting outliers unless stated | mixed | YES | PARTIAL | wording needs fairness clarification |
| Fig3 | figures/peerj_submission/figure3_keep_ratio_tradeoff.pdf or telemetry figure | keep-ratio or paging behavior | tuning scan | excluded failed runs if any | linear | NO | PARTIAL | redraw required |
| Fig4 | figures/peerj_submission/figure4_e2e_breakdown.pdf | stage-wise latency decomposition | V1 vs V2 representative runs | none unless stated | linear | PARTIAL | PARTIAL | caption must match final panel set |
| Fig5 | figures/peerj_submission/figure5_quality_latency_frontier.pdf | faithfulness-latency frontier | dual-judge test40 candidates | none unless stated | linear | YES | YES | keep dual-judge scale fixed |

## Update protocol
- When a figure changes, update:
  - the source file path
  - the caption status
  - the manuscript status
  - any inclusion/exclusion rule used to build the plot

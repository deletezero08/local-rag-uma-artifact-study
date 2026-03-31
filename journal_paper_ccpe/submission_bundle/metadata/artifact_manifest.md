# Artifact Manifest

## Scope
This manifest is the minimum reproducibility layer for the PeerJ submission package. It is intended to connect each reported result to a concrete execution path, parameter set, and raw artifact location.

## Device
- Device: Mac mini M4
- Memory: 16 GB unified memory
- OS: macOS on Apple Silicon

## Model and backend records

| Artifact ID | Model ID | Backend | Quant type | Runtime / version | Context length | Max tokens | Threads / GPU layers | Repeat count n | Prompt template | Raw result path | Notes |
|-------------|----------|---------|------------|-------------------|----------------|------------|----------------------|----------------|-----------------|-----------------|-------|
| M1 | Falcon-7B | transformers + MPS | baseline fp path | torch / transformers / MPS | to-be-filled | to-be-filled | to-be-filled | to-be-filled | to-be-filled | results/evaluation/model_comparison.json | impractical reference path |
| M2 | Falcon-7B-Quant | GGUF / llama.cpp | Q4_K_M | llama.cpp or llama-cpp-python | to-be-filled | to-be-filled | to-be-filled | to-be-filled | to-be-filled | results/evaluation/v2_performance_final.json | backend migration near-control |
| M3 | Llama-3-8B-Q | GGUF / llama.cpp | quantized GGUF | llama.cpp or llama-cpp-python | to-be-filled | to-be-filled | to-be-filled | to-be-filled | to-be-filled | results/evaluation/model_comparison.json | preferred practical configuration |

## Retrieval / compression records

| Artifact ID | Component | Key settings | Raw result path | Notes |
|-------------|-----------|--------------|-----------------|-------|
| R1 | TurboQuant retrieval comparison | to-be-filled | results/evaluation/turboquant_comparison.json | retrieval-side compression evidence |
| R2 | Keep-ratio scan | to-be-filled | results/evaluation/tradeoff_curve.json | prompt-budget / pruning sweep |
| R3 | Compression comparison | to-be-filled | results/evaluation/compression_comparison.json | end-to-end compression behavior |

## Quality records

| Artifact ID | Dataset / split | Judge setup | Metric scale | Raw result path | Notes |
|-------------|------------------|-------------|--------------|-----------------|-------|
| Q1 | test40 | dual-judge merged | choose one global scale and keep it fixed | results/evaluation/step1_dual_judge_test40_t7_b0.json | candidate B or low-budget reference |
| Q2 | test40 | dual-judge merged | choose one global scale and keep it fixed | results/evaluation/step1_dual_judge_test40_t8_b1500.json | candidate A or selected operating point |
| Q3 | verified set | dual-judge merged | choose one global scale and keep it fixed | results/evaluation/step1_dual_judge_verified_.json | calibration / verification slice |

## Concurrency and stress records

| Artifact ID | Workload | Metric focus | Raw result path | Notes |
|-------------|----------|--------------|-----------------|-------|
| C1 | stress test baseline | TTFT / aggregate TPS / failures | results/evaluation/stress_test_report.json | baseline contention behavior |
| C2 | stress test optimized | TTFT / aggregate TPS / failures | results/evaluation/stress_test_report_v2.json | optimized contention behavior |

## Plotting and manuscript generation
- Plot generation script:
  - `scripts/generate_submission_figures.py`
- Journal plotting helper:
  - `journal_paper_ccpe/generate_plots.py`
- Main manuscript:
  - `journal_paper_ccpe/main.tex`
- Submission bundle:
  - `journal_paper_ccpe/submission_bundle/`

## Software versions to fill before submission
- `llama.cpp` version: to-be-filled
- `llama-cpp-python` version: to-be-filled
- `torch` version: to-be-filled
- `transformers` version: to-be-filled
- macOS / MPS runtime details: to-be-filled

## Submission note
- The `Reproducibility Statement` in the manuscript should point to this manifest together with the raw JSON files under `results/evaluation/`.

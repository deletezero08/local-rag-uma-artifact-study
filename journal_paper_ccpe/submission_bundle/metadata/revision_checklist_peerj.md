# PeerJ Revision Checklist

## Must this week

### 1. Unify manuscript wording
- [ ] Unify backend-comparison wording in the abstract, Table 1, and Section 5.1.
- [ ] State explicitly that `Falcon-7B` vs. `Falcon-7B-Quant` is a near backend-migration comparison, while `Llama-3-8B-Q + GGUF` is a practical reference configuration rather than a pure backend-only control.
- [ ] Freeze the dual-judge metric scale to a single range across the full manuscript.
- [ ] Unify concurrency reporting:
  - [ ] If the table reports mean TTFT, the main text should also report mean TTFT.
  - [ ] If the main text retains `P95 TTFT ↓48.5%`, add a matching P95 table or appendix plot.

### 2. Retune title, abstract, and conclusion for PeerJ
- [ ] Reframe the title toward `Empirical Study`, `Case Study`, or `Artifact-Backed Study`.
- [ ] Remove or weaken over-assertive phrases:
  - [ ] `decisive structural optimization`
  - [ ] `zero-sum memory bandwidth game`
  - [ ] `I/O Death Spiral`
  - [ ] `must shift`
- [ ] Rewrite conclusion language toward:
  - [ ] `on the tested device`
  - [ ] `this case study suggests`
  - [ ] `artifact-backed evidence indicates`

### 3. Fix the three most important figures
- [ ] Figure 1: redraw as a four-stage pipeline
  - [ ] `Retrieval`
  - [ ] `Compression`
  - [ ] `Prompt Construction`
  - [ ] `Inference / Telemetry`
  - [ ] show `shared memory budget` as a separate bottom strip
- [ ] Figure 3: redraw the paging/telemetry plot
  - [ ] use phase-aligned traces
  - [ ] or split into two panels
  - [ ] remove the visual contradiction between “near-zero paging” wording and residual green spikes
- [ ] Figure 4/5 caption: keep caption and graphic semantics fully aligned
  - [ ] if only TTFT and TPS panels remain, remove any caption mention of a total-E2E dashed boundary

### 4. Add the minimum reproducibility artifact layer
- [ ] Create `artifact_manifest.md`
- [ ] Record at least:
  - [ ] model id
  - [ ] GGUF quant type
  - [ ] `llama.cpp` / `llama-cpp-python` version
  - [ ] `torch` / `transformers` / MPS version
  - [ ] prompt template
  - [ ] context length
  - [ ] `max_tokens`
  - [ ] threads / GPU layers
  - [ ] repeat count `n`
  - [ ] raw result file path
- [ ] Point the `Reproducibility Statement` at the manifest and the raw result files.

## Next week

### 5. Run a fair backend comparison
- [ ] Use the same model for:
  - [ ] MPS path
  - [ ] GGUF path
- [ ] Hold constant:
  - [ ] prompt
  - [ ] context length
  - [ ] generation parameters
  - [ ] `max_tokens`
  - [ ] repeat count `>= 5`
- [ ] Report:
  - [ ] TTFT mean/std
  - [ ] TPS mean/std
  - [ ] total latency mean/std
  - [ ] success/failure rate

### 6. Complete the ablation matrix
- [ ] Full path
- [ ] Without TurboQuant
- [ ] Without context pruning
- [ ] Only TurboQuant
- [ ] Only pruning
- [ ] Optional: no telemetry / no orchestration overhead check

### 7. Complete the quality-latency tradeoff
- [ ] Keep-ratio scan: `1.0 / 0.9 / 0.8 / 0.7 / 0.6 / 0.5`
- [ ] TopN scan: `6 / 7 / 8 / 10`
- [ ] Budget scan: `0 / 1000 / 1500 / 2000`
- [ ] Report:
  - [ ] TTFT
  - [ ] Total E2E
  - [ ] Recall@10
  - [ ] Faithfulness
  - [ ] Relevance
  - [ ] selected operating point

### 8. Run a concurrency ladder benchmark
- [ ] Concurrency levels: `1 / 2 / 4 / 8`
- [ ] For each level record:
  - [ ] mean TTFT
  - [ ] P95 TTFT
  - [ ] P99 TTFT
  - [ ] aggregate TPS
  - [ ] wall time
  - [ ] failure count
- [ ] Separate warm runs from cold runs.

## Working note
- Keep the manuscript framed as a constrained-device empirical case study rather than a broad algorithmic claim.
- Prefer definitions that can be matched one-to-one across abstract, tables, figures, and the artifact package.

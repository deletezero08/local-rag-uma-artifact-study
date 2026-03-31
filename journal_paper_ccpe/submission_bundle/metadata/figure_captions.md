# Figure Captions for PeerJ CS Submission

## Figure 2
**Backend comparison across constrained local deployment routes.**  
Panels A-C report time to first token, decode throughput, and total latency. The `Falcon-7B + MPS` route is impractical on the tested 16GB UMA device, whereas GGUF-based `llama.cpp` restores usable local inference.

## Figure 3
**Effect of keep ratio on latency and decoding throughput.**  
Panel A shows the latency response, and Panel B shows decode throughput. The strongest TTFT improvement is observed around `keep_ratio = 0.6`, while decode throughput remains comparatively stable across the tested ratios.

## Figure 4
**End-to-end latency decomposition before and after collaborative optimization.**  
Panel A compares V1 and V2, Panel B isolates the non-decode stages, and Panel C shows the full composition of a representative optimized path. Generation, especially decode, remains the dominant cost after retrieval- and context-side optimization.

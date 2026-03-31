# Table Notes for PeerJ CS Submission

## Table 1
**Backend and model comparison on a Mac mini M4 with 16GB unified memory.**  
The `transformers + MPS` route remains functionally executable but practically unusable for the tested 7B-class deployment. In contrast, GGUF-based `llama.cpp` restores usable local inference, and the `Llama-3-8B-Quant` configuration provides the best observed TTFT among deployable configurations.

## Table 2
**Quality preservation under compressed configurations using merged dual-judge faithfulness scores on the test40 split.**  
Both candidate configurations remain within the current `faithfulness drop <= 0.2` acceptance boundary. These results suggest that moderate context compression does not cause obvious faithfulness degradation under the current evaluation setting, although the corresponding latency reductions remain limited.

## Table 4
**Concurrency stability under baseline and collaboratively optimized execution paths.**  
Under the high-pressure benchmark setting, the optimized path reduces `P95 TTFT` from `17435.46 ms` to `8979.26 ms` and improves aggregate throughput from `3.85` to `4.67` tokens per second. These results indicate that collaborative generation-side optimization improves not only single-query responsiveness but also tail behavior under contention on constrained UMA hardware.

## Table 3
**TurboQuant retrieval compression trade-off under the current benchmark setting.**  
TurboQuant reduces retrieval latency from `128.4 ms` to `25.4 ms` and index size from `420.0 MB` to `110.0 MB`, but lowers `Recall@10` from `1.000` to `0.631`. The result should therefore be interpreted as an engineering trade-off rather than as lossless retrieval compression.

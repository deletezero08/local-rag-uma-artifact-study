March 28, 2026

Dear Editors of *PeerJ Computer Science*,

Please consider the manuscript **“Collaborative Optimization of Local RAG Execution on Constrained Unified Memory Devices”** for publication in *PeerJ Computer Science*.

The manuscript studies a practical systems problem in local retrieval-augmented generation (RAG): how to make local execution usable on constrained unified-memory hardware. It presents an artifact-linked empirical study of a collaborative optimization path that combines GGUF-based deployment, lightweight inference backends, retrieval compression, and context pruning. Experiments on a Mac mini M4 with 16GB unified memory show that `transformers + MPS` is impractical for the tested 7B-class deployment, while `GGUF + llama.cpp` restores usable local inference. The results further show that prompt-side pruning improves prefill latency, while end-to-end decomposition reveals that decode remains the dominant bottleneck after retrieval- and context-side optimization.

This work is well aligned with *PeerJ Computer Science* because it emphasizes methodological soundness, artifact-linked evidence, practical systems behavior, and clearly bounded claims. The submission is original, is not under consideration elsewhere, and has no competing interests. The reported study does not involve human subjects, protected personal data, or clinical decision-making.

Thank you for your consideration.

Sincerely,

Chaoran Wang  
College of Science and Information  
Qingdao Agricultural University  
Qingdao, China  
chaoranw47@gmail.com

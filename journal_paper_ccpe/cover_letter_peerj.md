March 28, 2026

Dear Editors of *PeerJ Computer Science*,

Please consider the enclosed manuscript, **“Collaborative Optimization of Local RAG Execution on Constrained Unified Memory Devices,”** for publication in *PeerJ Computer Science*.

This manuscript studies a practical systems problem that is becoming increasingly relevant as large language models move from cloud deployment to consumer hardware: how to make local retrieval-augmented generation (RAG) usable on constrained unified-memory devices. Rather than presenting another standalone retrieval method, the paper examines the execution path of local RAG as a coordinated systems problem spanning retrieval compression, prompt-budget control, and inference-backend selection. The study is grounded in artifact-linked experiments on a Mac mini M4 with 16GB unified memory and compares `transformers + MPS` with `GGUF + llama.cpp`, while further evaluating TurboQuant and keep-ratio-based context pruning.

The manuscript makes three main contributions. First, it frames local RAG execution on constrained unified-memory hardware as a collaborative optimization problem rather than a retrieval-only design problem. Second, it contributes an empirical study that retains both positive and negative evidence, including an impractical `Falcon-7B + MPS` route and multiple feasible GGUF-based alternatives. Third, it uses stage-wise latency decomposition to show that once retrieval- and context-side gains accumulate, the dominant optimization target shifts to generation, especially decode. This leads to a practical conclusion that local RAG performance should be designed and evaluated as a systems co-design problem.

The manuscript is well aligned with the scope of *PeerJ Computer Science* because it emphasizes methodological soundness, reproducible artifact-linked evidence, and practical insight into real-world computer systems behavior. The contribution is not framed as a claim of universal superiority for a single method; instead, it offers a carefully bounded systems study of constrained local deployment, negative-result interpretation, and performance-quality trade-offs. This positioning matches the journal’s interest in technically sound and practically meaningful computer science research.

This submission is original, has not been published previously, and is not under consideration elsewhere. The author declares no competing interests. The reported study does not involve human subjects, protected personal data, or clinical decision-making. An artifact bundle containing manuscript sources, table sources, figure-generation scripts, and benchmark evidence has been prepared, and the public archival version will include repository and artifact-release information.

Thank you for your time and consideration.

Sincerely,

Chaoran Wang  
College of Science and Information  
Qingdao Agricultural University  
Qingdao, China  
chaoranw47@gmail.com

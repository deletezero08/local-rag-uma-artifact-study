import time
import json
import os
import logging
from typing import List, Dict, Tuple, Optional
from llama_cpp import Llama

from src.retriever import TurboQuantRetriever
from src.context_compressor import ContextCompressor

logger = logging.getLogger("rag_core")

class MemoraRAGPipeline:
    """
    End-to-End RAG Controller (Battle 3 Upgrade).
    Bridges Retrieval, Pruning, and Inference with micro-level telemetry.
    Supports dynamic context pruning and mock document injection for stress testing.
    """
    def __init__(self, 
                 model_path: str = "Llama-3-8B-Instruct.Q4_K_M.gguf",
                 index_path: str = "models/vector_indices/turbo_index.json",
                 n_ctx: int = 8192):
        
        logger.info("🚢 Launching MemoraRAG Pipeline...")
        
        # 1. Initialize Components
        self.retriever = TurboQuantRetriever(index_path)
        self.compressor = ContextCompressor()
        
        # 2. Initialize LLM (with Metal support)
        logger.info(f"🔥 Loading LLM: {model_path} (Metal enabled)")
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1, # Max offload
            n_ctx=n_ctx,
            verbose=False
        )
        logger.info("✅ Pipeline Ready.")

    def _format_prompt(self, query: str, context: str) -> str:
        """Academic standard RAG prompt template."""
        return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
Use the following context to answer the user query honestly and precisely.
If the answer is not in the context, state that you do not know. 
Maintain academic rigor.

CONTEXT:
{context}
<|eot_id|><|start_header_id|>user<|end_header_id|>
{query}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    def run(self, 
            user_query: str, 
            top_k: int = 15, 
            mock_docs: Optional[List[str]] = None, 
            use_dynamic: bool = True) -> Dict:
        """
        Execute the full RAG pipeline with high-precision timing.
        """
        trace = {}
        
        # --- PHASE 1: Retrieval ---
        r_start = time.perf_counter_ns()
        if mock_docs:
            search_results = [{"content": doc} for doc in mock_docs]
            inner_ret_ms = 0.0
        else:
            search_results, inner_ret_ms = self.retriever.search(user_query, top_k=top_k)
            
        trace["retrieval_ms"] = (time.perf_counter_ns() - r_start) / 1_000_000
        
        full_context = "\n\n".join([r["content"] for r in search_results])
        
        # --- PHASE 2: Context Compression ---
        c_start = time.perf_counter_ns()
        compressed_context, comp_metrics = self.compressor.compress(user_query, full_context, use_dynamic=use_dynamic)
        trace["scoring_ms"] = comp_metrics["scoring_ms"]
        trace["pruning_ms"] = comp_metrics["pruning_ms"]
        
        # --- PHASE 3: LLM Inference ---
        final_prompt = self._format_prompt(user_query, compressed_context)
        
        # Start Timing TTFT
        llm_start = time.perf_counter_ns()
        response_stream = self.llm(
            final_prompt, 
            max_tokens=128, # Matching stress_test default
            stream=True, 
            stop=["<|eot_id|>"]
        )
        
        answer_parts = []
        ttft_ms = None
        generated_tokens = 0
        
        for chunk in response_stream:
            text = chunk["choices"][0]["text"]
            if ttft_ms is None and text.strip():
                ttft_ms = (time.perf_counter_ns() - llm_start) / 1_000_000
            
            answer_parts.append(text)
            # Count tokens (roughly by whitespace or chunks if not available from LLM)
            generated_tokens += 1
        
        full_answer = "".join(answer_parts).strip()
        
        # Finish Timing
        llm_total_ms = (time.perf_counter_ns() - llm_start) / 1_000_000
        trace["llm_prefill_ms"] = ttft_ms if ttft_ms else llm_total_ms
        trace["llm_decode_ms"] = llm_total_ms - (ttft_ms if ttft_ms else 0)
        
        trace["total_pipeline_ms"] = sum([v for k, v in trace.items() if "_ms" in k])
        
        return {
            "query": user_query,
            "answer": full_answer,
            "generated_tokens": generated_tokens,
            "waterfall": trace,
            "original_len": len(full_context),
            "compressed_len": len(compressed_context),
            "pruning_strategy": comp_metrics.get("strategy", "unknown"),
            "retrieved_results": search_results,
            "full_context": full_context,
            "compressed_context": compressed_context,
        }

if __name__ == "__main__":
    # Sample Run
    logging.basicConfig(level=logging.INFO)
    pipeline = MemoraRAGPipeline()
    sample_q = "What are the core innovations of MemoraRAG?"
    
    print("\n🧐 Running MemoraRAG SOTA...\n")
    result = pipeline.run(sample_q)
    
    print(f"🤖 Answer: {result['answer']}\n")
    print("📊 Waterfall (ms):")
    print(json.dumps(result["waterfall"], indent=2))

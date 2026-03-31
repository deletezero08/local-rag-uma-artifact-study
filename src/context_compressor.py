import time
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("rag_core")

class ContextCompressor:
    """
    SOTA Gradient-Aware Context Pruner (Adaptive Cliff Detection).
    Logic:
    - Protect Prefix (2 chunks)
    - Protect Suffix (2 chunks)
    - Detect "Cliff" in middle chunk scores (Gradient > 0.1)
    - Fallback to adaptive 70%/30% ratios if no cliff exists.
    """
    def __init__(self, 
                 model_name: str = "BAAI/bge-small-zh-v1.5", 
                 chunk_size_chars: int = 250, 
                 default_keep_ratio: float = 0.5,
                 cliff_threshold: float = 0.1):
        logger.info(f"🧠 Loading Gradient Scorer: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.chunk_size = chunk_size_chars
        self.keep_ratio = default_keep_ratio
        self.cliff_threshold = cliff_threshold
        self.omission_marker = "\n...[系统提示: 动态内存释放触发 | 策略: {strategy_name}]...\n"

    def chunk_text(self, text: str) -> List[str]:
        """Split text into fine-grained chunks."""
        chunks = []
        for i in range(0, len(text), self.chunk_size):
            chunks.append(text[i : i + self.chunk_size].strip())
        return [c for c in chunks if c]

    def score_chunks(self, query: str, chunks: List[str]) -> np.ndarray:
        """Calculate BGE scores."""
        if not chunks: return np.array([])
        q_emb = self.model.encode([query], normalize_embeddings=True)
        c_embs = self.model.encode(chunks, normalize_embeddings=True)
        return np.dot(c_embs, q_emb.T).flatten()

    def get_adaptive_cutoff(self, scores: List[float]) -> Tuple[int, str]:
        """Core Algorithm: Cliff detection via first-order gradients."""
        if len(scores) < 2:
            return len(scores), "fallback_too_short"

        # 1. First-order differences (Score Drop)
        gradients = [scores[i] - scores[i+1] for i in range(len(scores)-1)]
        max_gradient = max(gradients)
        max_idx = gradients.index(max_gradient)

        # 2. Significant Cliff Detection
        if max_gradient >= self.cliff_threshold:
            return max_idx + 1, f"cliff_detected_drop_{max_gradient:.2f}"

        # 3. Fallback: Adaptive Ratios based on Avg Relevance
        avg_score = sum(scores) / len(scores)
        if avg_score > 0.6:  # High context relevance
            return max(1, int(len(scores) * 0.7)), "adaptive_high_70%"
        else:                # Low context relevance
            return max(1, int(len(scores) * 0.3)), "adaptive_low_30%"

    def compress(self, query: str, context: str, use_dynamic: bool = True) -> Tuple[str, Dict[str, Any]]:
        """
        Compress context using dynamic gradient logic or static ratio.
        """
        start_ns = time.perf_counter_ns()
        
        all_chunks = self.chunk_text(context)
        total_chunks = len(all_chunks)
        
        if total_chunks <= 4:
            return context, {
                "original_chunks": total_chunks,
                "retained_chunks": total_chunks,
                "strategy": "passthrough",
                "scoring_ms": 0.0,
                "pruning_ms": (time.perf_counter_ns() - start_ns) / 1_000_000
            }

        # 1. Sliding Anchor Protection (Top 2% + Bottom 2%)
        # For 120k context (~6000 chunks), 2% = 120 chunks. We cap at 10.
        anchor_count = max(2, min(10, int(total_chunks * 0.02)))
        prefix = all_chunks[:anchor_count]
        suffix = all_chunks[-anchor_count:]
        middle = all_chunks[anchor_count:-anchor_count]
        
        # 2. Score Middle with Position Boost
        score_start = time.perf_counter_ns()
        middle_scores = self.score_chunks(query, middle)
        
        # 2.5. Apply Position Boost to prioritize boundary proximity (Top/Bottom of Middle)
        if len(middle_scores) > 0:
            n_mid = len(middle_scores)
            edge = max(1, int(n_mid * 0.1))
            middle_scores[:edge] += 0.05
            middle_scores[-edge:] += 0.05
            
        scoring_ms = (time.perf_counter_ns() - score_start) / 1_000_000
        
        # 3. Decision Phase
        paired = [(i, chunk, score) for i, (chunk, score) in enumerate(zip(middle, middle_scores))]
        paired.sort(key=lambda x: x[2], reverse=True)
        sorted_scores = [x[2] for x in paired]

        if use_dynamic:
            keep_count, strategy_name = self.get_adaptive_cutoff(sorted_scores)
        else:
            keep_count = max(1, int(len(middle) * self.keep_ratio))
            strategy_name = f"static_ratio_{self.keep_ratio*100}%"

        # 3.5. [SOTA CRITICAL] Hard Cap for Hardware Context Window (e.g. 8192 tokens)
        # 10 chunks * 250 chars (~1k-4k tokens in Chinese Llama-3)
        max_retained = 10 
        if keep_count > max_retained:
            keep_count = max_retained
            strategy_name += f" (capped_at_{max_retained})"

        # 4. Filter and Maintain Sequence order
        survivors = paired[:keep_count]
        survivors.sort(key=lambda x: x[0])
        kept_middle = [chunk for _, chunk, _ in survivors]
        
        # 5. Assembly with Omission Markers
        marker = self.omission_marker.format(strategy_name=strategy_name)
        final_context = prefix + [marker] + kept_middle + suffix
        final_text = "\n\n".join(final_context)
        
        pruning_ms = (time.perf_counter_ns() - start_ns) / 1_000_000 - scoring_ms
        
        metrics = {
            "original_chunks": total_chunks,
            "retained_chunks": len(prefix) + len(suffix) + len(kept_middle),
            "strategy": strategy_name,
            "scoring_ms": scoring_ms,
            "pruning_ms": pruning_ms
        }
        
        logger.info(f"✂️  Adaptive Pruning [{strategy_name}]: {total_chunks} -> {metrics['retained_chunks']} in {metrics['scoring_ms'] + metrics['pruning_ms']:.2f}ms")
        
        return final_text, metrics

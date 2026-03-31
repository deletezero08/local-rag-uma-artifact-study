import os
import json
import logging
import time
import numpy as np
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from src.turbo_quant import TurboQuantizer

logger = logging.getLogger("rag_core")

class TurboQuantRetriever:
    """
    SOTA Retriever using TurboQuant for 100x+ index compression.
    Implements Asymmetric Distance Computation (ADC) with FP32 query path.
    """
    def __init__(self, 
                 index_path: str, 
                 model_name: str = "BAAI/bge-small-zh-v1.5"):
        self.index_path = index_path
        self.model_name = model_name
        
        logger.info(f"🧬 Initializing TurboQuantRetriever with {model_name}...")
        self.model = SentenceTransformer(model_name)
        
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"Index not found: {index_path}. Please run scripts/build_quant_index.py first.")
        
        with open(index_path, "r", encoding="utf-8") as f:
            self.index_data = json.load(f)
            
        self.dim = self.index_data["dim"]
        self.outlier_indices = self.index_data.get("outlier_indices", [])
        
        # Initialize TQ with indices (for logic setup)
        self.tq = TurboQuantizer(dim=self.dim)
        self.tq.outlier_indices = self.outlier_indices
        
        # Restore TurboQuant state (Sign flips and QJL projections)
        self.tq.D = np.array(self.index_data["D"], dtype=np.float32)
        self.tq.W_qjl = np.array(self.index_data["W_qjl"], dtype=np.float32)
        
        # Prepare dequantization dict
        self.encoded = {
            "codes": np.array(self.index_data["codes"], dtype=np.int8),
            "qjl": np.array(self.index_data["qjl"], dtype=np.int8),
            "params": self.index_data["params"],
            "scale_qjl": np.array(self.index_data["scale_qjl"], dtype=np.float32),
            "norms": np.array(self.index_data["norms"], dtype=np.float32)
        }
        
        self.chunks = self.index_data["chunks"]
        self.metadatas = self.index_data["metadatas"]
        logger.info(f"✅ Loaded index with {len(self.chunks)} chunks.")

    def embed_query(self, query: str) -> np.ndarray:
        """Encode query to high-precision embedding (FP32)."""
        return self.model.encode([query], normalize_embeddings=True)[0]

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Search for relevant chunks using TurboQuant ADC.
        Returns: List of {"content": str, "metadata": dict, "score": float}
        """
        start_time = time.perf_counter_ns()
        
        # 1. High-precision FP32 embedding
        q_emb = self.embed_query(query)
        
        # 2. Fast ADC Retrieval
        # inner_product handles normalization and FWHT rotation of the query
        scores = self.tq.inner_product(q_emb, self.encoded)[0]
        
        # 3. Rank and Format
        top_indices = np.argsort(scores)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            results.append({
                "content": self.chunks[idx],
                "metadata": self.metadatas[idx],
                "score": float(scores[idx])
            })
            
        latency_ms = (time.perf_counter_ns() - start_time) / 1_000_000
        logger.debug(f"🔍 Retrieval latency: {latency_ms:.2f}ms")
        
        return results, latency_ms

if __name__ == "__main__":
    # Quick debug run
    logging.basicConfig(level=logging.INFO)
    INDEX_PATH = "/Users/delete/Desktop/rag_system_副本/models/vector_indices/turbo_index.json"
    retriever = TurboQuantRetriever(INDEX_PATH)
    res, t = retriever.search("What is TurboQuant?", top_k=3)
    for r in res:
        print(f"Score: {r['score']:.4f} | Content: {r['content'][:100]}...")

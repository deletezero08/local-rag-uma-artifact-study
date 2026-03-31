import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer

def calibrate_outliers(dim=512, top_k=32, num_samples=50):
    """
    Simulate outlier detection for a high-dimensional space (128-dim head).
    Calculates the persistent 'Heavy Hitter' channels using BGE-small embeddings.
    """
    print(f"🔍 Starting Outlier Calibration (Target: {top_k} channels in {dim} dimensions)...")
    
    model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    
    # Sample text from project README or dummy data to get real-world distribution
    texts = [
        "MemoraRAG is a SOTA RAG system optimized for Apple Silicon UMA.",
        "Unified Memory Architecture provides high-bandwidth between CPU and GPU.",
        "TurboQuant achieves near-optimal distortion rates using random rotation.",
        "Fast Walsh-Hadamard Transform (FWHT) reduces O(d^2) to O(d log d).",
        "Gradient-aware dynamic pruning detects cliffs in semantic relevance."
    ] * (num_samples // 5)
    
    # 1. Generate Embeddings (d=384 for BGE-small)
    embs = model.encode(texts) # (num_samples, 384)
    
    # 2. Reshape or Aggregate to match target dim (e.g. 128 for Llama heads)
    # We aggregate every 3 elements to simulate a 128-dim head slice if needed, 
    # but here we just analyze the 384-dim space and take top 10%
    full_dim = embs.shape[1]
    
    # 3. Calculate Mean Absolute Magnitude per channel
    mean_abs = np.mean(np.abs(embs), axis=0)
    
    # 4. Find Top K Indices
    outlier_indices = np.argsort(mean_abs)[::-1][:top_k].tolist()
    
    print(f"✅ Calibration Complete. Found {len(outlier_indices)} outlier channels.")
    print(f"📊 Top 5 Outliers (Index/Mag): {[(i, round(float(mean_abs[i]), 4)) for i in outlier_indices[:5]]}")
    
    output_path = "models/vector_indices/outlier_indices.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"dim": full_dim, "outlier_indices": outlier_indices}, f, indent=4)
    
    return outlier_indices

if __name__ == "__main__":
    calibrate_outliers(top_k=32)

import os
import glob
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from src.turbo_quant import TurboQuantizer
from pathlib import Path

# Config
DOCS_DIR = "/Users/delete/Desktop/rag_system_副本/docs"
INDEX_PATH = "/Users/delete/Desktop/rag_system_副本/models/vector_indices/turbo_index.json"
OUTLIER_PATH = "/Users/delete/Desktop/rag_system_副本/models/vector_indices/outlier_indices.json"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
DIM = 512 # BGE-small output dimension for this version

def build_index():
    print(f"📦 Loading Embedding Model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    # 1. Load and Chunk Documents
    documents = []
    file_paths = glob.glob(str(Path(DOCS_DIR) / "**/*.md"), recursive=True)
    file_paths += glob.glob(str(Path(DOCS_DIR) / "**/*.txt"), recursive=True)
    
    print(f"📖 Found {len(file_paths)} documentation files.")
    
    all_chunks = []
    metadatas = []
    
    for path in file_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                # Simple chunking by paragraph/length
                chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 20]
                for i, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    metadatas.append({"path": path, "chunk_id": i})
        except Exception as e:
            print(f"⚠️ Error reading {path}: {e}")

    print(f"🧩 Total Chunks: {len(all_chunks)}")
    if not all_chunks:
        print("❌ No text found in docs/. Aborting.")
        return

    # 2. Generate Embeddings
    print("🧬 Generating Embeddings (FP32)...")
    embeddings = model.encode(all_chunks, normalize_embeddings=True)
    embeddings = np.array(embeddings).astype(np.float32)

    # 3. Apply TurboQuant Encoding (SOTA Outlier-Aware)
    print(f"⚡ Applying TurboQuant (SOTA Outlier-Aware)...")
    tq = TurboQuantizer(dim=DIM, bits=3.5, outlier_indices_path=OUTLIER_PATH)
    encoded_data = tq.encode(embeddings)
    
    # 4. Save Index
    index_payload = {
        "dim": DIM,
        "outlier_indices": tq.outlier_indices,
        "D": tq.D.tolist(),
        "W_qjl": tq.W_qjl.tolist(),
        "codes": encoded_data["codes"].tolist(),
        "qjl": encoded_data["qjl"].tolist(),
        "params": encoded_data["params"],
        "scale_qjl": encoded_data["scale_qjl"].tolist(),
        "norms": encoded_data["norms"].tolist(),
        "chunks": all_chunks,
        "metadatas": metadatas
    }
    
    Path(INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index_payload, f)
    
    orig_size = embeddings.nbytes / 1024 / 1024 # MB
    # Estimate compressed size: codes (N,D) int8 + qjl (N,64) int8 + norms (N,1) float32
    comp_size = (len(all_chunks) * (DIM + 64 + 4)) / 1024 / 1024 # MB
    
    print("\n" + "="*40)
    print("🏁 SOTA INDEX BUILDING COMPLETE")
    print("="*40)
    print(f"Total Chunks:      {len(all_chunks)}")
    print(f"Original Size:     {orig_size:.2f} MB")
    print(f"Compressed Size:   ~{comp_size:.2f} MB")
    print(f"Compression Ratio: {orig_size/comp_size:.2f}x")
    print(f"Outlier Count:     {len(tq.outlier_indices)}")
    print(f"Index Saved:       {INDEX_PATH}")
    print("="*40)

if __name__ == "__main__":
    build_index()

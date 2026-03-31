import time
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.rag_pipeline import MemoraRAGPipeline
except ImportError:
    print("❌ Error: src/rag_pipeline.py not found. Please run from project root.")
    sys.exit(1)

def main():
    print("="*60)
    print("🚀 MemoraRAG V2: SOTA RAG Engine (Finalized Research Version)")
    print("="*60)
    print("Features: Gradient-Aware Dynamic Pruning | TurboQuant ADC | UMA Optimization")
    
    # Initialize Pipeline
    model_path = "Llama-3-8B-Instruct.Q4_K_M.gguf"
    index_path = "models/vector_indices/turbo_index.json"
    
    if not os.path.exists(model_path):
        print(f"❌ Error: Model {model_path} not found.")
        return
    if not os.path.exists(index_path):
        print(f"⚠️ Warning: Index {index_path} not found. Running with null-retrieval (inference only).")
    
    pipeline = MemoraRAGPipeline(model_path=model_path, index_path=index_path)
    
    print("\n✅ System Ready. Type 'exit' to quit.\n")
    
    while True:
        try:
            query = input("🧠 MemoraRAG > ").strip()
            if not query: continue
            if query.lower() in ("exit", "quit"): break
            
            print("⏳ Processing (Thinking + Retrieval + Generation)...")
            
            result = pipeline.run(query, use_dynamic=True)
            
            print("\n" + "-"*30)
            print(f"📖 Answer: {result['answer']}")
            print("-"*30)
            
            w = result["waterfall"]
            print(f"⏱️ Metrics: Total {w['total_pipeline_ms']:.0f}ms | Retrieval {w['retrieval_ms']:.0f}ms | Prefill {w['llm_prefill_ms']:.0f}ms")
            print(f"📉 Strategy: {result['pruning_strategy']}")
            print("-"*30 + "\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n🏁 Demo closed. Good luck with the thesis!")

if __name__ == "__main__":
    main()

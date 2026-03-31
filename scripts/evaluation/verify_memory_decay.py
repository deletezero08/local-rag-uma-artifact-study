#!/usr/bin/env python3
import os
import sys
import json
import time
import math
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import save_memory, load_memory, settings, MEMORY_DIR, _memory_key

def run_verification():
    print("🚀 Starting Memory Decay Verification...")
    
    test_file = "test_decay_doc.md"
    key = _memory_key(test_file)
    mem_file = MEMORY_DIR / f"{key}.json"
    
    # 1. Clear any existing test memory
    if mem_file.exists():
        mem_file.unlink()
    
    # Simulate current time
    now = time.time()
    day_seconds = 24 * 3600
    
    # We will bypass the save_memory function to directly insert fragments 
    # with artificial timestamps and simulate max_fragments pruning.
    
    # Create 110 fragments (exceeding default max_fragments=100)
    # Give them varying ages: 0 days to 109 days old
    fragments_to_insert = []
    
    for i in range(110):
        age_days = i
        created_at = now - (age_days * day_seconds)
        fragment = {
            "id": f"frag_{i}",
            "content": f"Insight from {age_days} days ago",
            "source": test_file,
            "created_at": created_at,
            "last_used_at": created_at,
            "decay_score": 1.0, # will be recalculated
            "tags": ["test"],
            "session_id": "test_session"
        }
        fragments_to_insert.append(fragment)
        
    # Write directly to simulate a heavily populated memory file
    mem_file.write_text(json.dumps(fragments_to_insert, ensure_ascii=False, indent=2), "utf-8")
    fragments_before = len(fragments_to_insert)
    print(f"✅ Inserted {fragments_before} fragments into {mem_file.name}")
    
    # 2. Trigger load_memory which should apply decay and sort them
    loaded_fragments = load_memory(test_file)
    
    # We also want to test the max_fragments constraint. save_memory enforces it.
    # Let's call save_memory once to trigger the truncation.
    save_memory(test_file, "A brand new insight", "test_session")
    
    # Load again to get the final pruned list
    final_fragments = load_memory(test_file)
    fragments_after = len(final_fragments)
    
    print(f"✅ After save_memory (pruning), fragment count is {fragments_after}")
    
    # 3. Verify decay logic and ranking
    decay_lambda = settings.get("memory", {}).get("decay_lambda", 0.08)
    
    ranked_ids = [f["id"] for f in final_fragments]
    decay_scores = [f["decay_score"] for f in final_fragments]
    
    # Output results
    results = {
        "file": test_file,
        "fragments_before": fragments_before + 1, # +1 for the new save_memory call
        "fragments_after": fragments_after,
        "ranked_ids": ranked_ids,
        "decay_scores": decay_scores,
        "decay_lambda": decay_lambda
    }
    
    results_dir = ROOT_DIR / "results" / "evaluation" / "support_checks"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / "memory_decay_check.json"
    
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), "utf-8")
    print(f"✅ Verification results saved to {out_file}")
    
    # Cleanup
    if mem_file.exists():
        mem_file.unlink()

if __name__ == "__main__":
    run_verification()

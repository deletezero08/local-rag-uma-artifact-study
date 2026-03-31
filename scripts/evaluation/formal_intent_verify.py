import sys
import os
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.engine import LocalRAG
from src.config import save_memory, DOCS_DIR, MEMORY_DIR

# Set up logging to a file for evidence
log_dir = Path("/Users/delete/Desktop/rag_system_副本/logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "formal_verification_run.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("formal_verify")

def cleanup():
    import shutil
    logger.info("Cleaning up environment...")
    for d in [DOCS_DIR, MEMORY_DIR]:
        if d.exists(): shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

def run_test_case(rag, query, description, expected_state, history=None):
    logger.info(f"--- [Test Case] {description} ---")
    logger.info(f"Query: '{query}'")
    
    gen = rag.stream_query(query, history_arr=history)
    results = []
    actual_state = "none"
    actual_file = None
    
    for item in gen:
        if item["type"] == "status":
            results.append(item["data"])
            # Extract state from status message if possible, or just log them
            logger.info(f"Status: {item['data']}")
        
        # In actual engine, _analyze_intent returns meta. 
        # But stream_query emits status messages.
        # We'll use a trick to catch the meta if we were calling retrieve_documents directly,
        # but here we rely on the status messages being emitted.
    
    # We'll run _analyze_intent directly to verify the exact state for the JSON report
    _, _, _, meta = rag._analyze_intent(query, history_arr=history)
    actual_state = meta.get("intent_state", "none")
    actual_file = meta.get("memory_fallback_file")
    
    logger.info(f"Actual Intent State: {actual_state}")
    
    pass_flag = (actual_state == expected_state)
    logger.info(f"Result: {'✅ PASS' if pass_flag else '❌ FAIL'}")
    
    return {
        "description": description,
        "query": query,
        "expected_state": expected_state,
        "actual_state": actual_state,
        "fallback_file": actual_file,
        "pass": pass_flag,
        "status_messages": results
    }

def formal_verification_suite():
    logger.info("📋 Starting Formal Verification for Research Log...")
    cleanup()
    rag = LocalRAG()
    results_data = {"test_runs": []}

    # 1. Phase 2: Smalltalk Bypass
    results_data["test_runs"].append(run_test_case(
        rag, "你好，请问你是谁？", "Smalltalk Bypass", "smalltalk"
    ))

    # 2. Phase 3: Memory Fallback (History)
    f1 = "api_v1.md"
    (DOCS_DIR / f1).write_text("# API V1\nDocs content.")
    rag.list_doc_files()
    
    history = [{"user": "查看一下 api_v1.md", "assistant": "好的，正在为您分析 api_v1.md"}]
    results_data["test_runs"].append(run_test_case(
        rag, "它刚才写了什么？", "Memory Fallback (History)", "memory_fallback", history=history
    ))

    # 3. Phase 1 Robustness: Boundary-Aware Regex
    # Test with a potential false positive 'i' if a file named 'i.pdf' existed
    (DOCS_DIR / "i.pdf").write_text("dummy")
    rag.list_doc_files()
    # Query contains '分析' which ends with '析' (xi), might match 'i' if boundaries aren't respected
    results_data["test_runs"].append(run_test_case(
        rag, "麻烦分析下内容", "Regex Boundary Check", "none" 
    ))

    # Save final report
    report_path = Path("/Users/delete/Desktop/rag_system_副本/results/evaluation/legacy_misc/formal_intent_verification_v2.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✨ Report saved to {report_path}")

if __name__ == "__main__":
    formal_verification_suite()

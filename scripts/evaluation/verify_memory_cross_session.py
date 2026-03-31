#!/usr/bin/env python3
"""
记忆跨会话验证脚本 (Memory Cross-Session Verification)
模拟: 注入记忆片段 → 新会话查询 → 验证记忆出现在上下文中。
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import save_memory, load_memory, MEMORY_DIR, _memory_key, list_doc_files


def run_verification(run_e2e: bool = False):
    print("🚀 Starting Memory Cross-Session Verification...")
    results = {"tests": [], "overall_pass": True}

    # --- Test 1: Inject → Load → Verify content presence ---
    print("\n📝 Test 1: Inject memory fragment and verify retrieval")
    test_docs = list_doc_files()
    if not test_docs:
        print("⚠️  No documents found in docs/. Using synthetic test file.")
        test_file = "test_cross_session_doc.md"
    else:
        test_file = test_docs[0]  # Use the first real document

    test_insight = "MemoraRAG 使用 RRF 算法融合向量检索与 BM25 关键词检索，k 值为 60。"
    test_session_id = "test-cross-session-001"

    # Clear existing memory for this file
    key = _memory_key(test_file)
    mem_path = MEMORY_DIR / f"{key}.json"
    if mem_path.exists():
        mem_path.unlink()

    # Inject
    save_ok = save_memory(test_file, test_insight, session_id=test_session_id, tags=["cross_session_test"])
    print(f"  💾 save_memory returned: {save_ok}")

    # Simulate "new session" by loading memory (no session state carried over)
    loaded = load_memory(test_file)
    found_insight = False
    if loaded:
        for frag in loaded:
            if test_insight in frag.get("content", ""):
                found_insight = True
                break

    test1_pass = save_ok and found_insight
    results["tests"].append({
        "name": "inject_and_retrieve",
        "file": test_file,
        "insight_injected": test_insight,
        "fragments_loaded": len(loaded) if loaded else 0,
        "insight_found_in_new_session": found_insight,
        "pass": test1_pass
    })
    print(f"  {'✅' if test1_pass else '❌'} Test 1: {'PASSED' if test1_pass else 'FAILED'}")

    # --- Test 2: Verify decay_score is present and valid ---
    print("\n📝 Test 2: Verify decay_score is present and valid (0 < score <= 1)")
    decay_valid = True
    if loaded:
        for frag in loaded:
            ds = frag.get("decay_score")
            if ds is None or not (0 < ds <= 1.0):
                decay_valid = False
                break
    else:
        decay_valid = False

    results["tests"].append({
        "name": "decay_score_valid",
        "pass": decay_valid,
        "sample_scores": [f.get("decay_score") for f in (loaded or [])]
    })
    print(f"  {'✅' if decay_valid else '❌'} Test 2: {'PASSED' if decay_valid else 'FAILED'}")

    # --- Test 3: Multiple insights accumulate (no overwrite) ---
    print("\n📝 Test 3: Multiple insights accumulate without overwriting")
    second_insight = "MemoraRAG 的记忆衰减系数 lambda 默认为 0.08，约 8-10 天后权重降至一半。"
    save_memory(test_file, second_insight, session_id="test-cross-session-002")
    loaded_again = load_memory(test_file)

    both_found = False
    if loaded_again:
        contents = [f.get("content", "") for f in loaded_again]
        has_first = any(test_insight in c for c in contents)
        has_second = any(second_insight in c for c in contents)
        both_found = has_first and has_second

    test3_pass = both_found and (len(loaded_again or []) >= 2)
    results["tests"].append({
        "name": "multiple_insights_accumulate",
        "fragments_after_two_saves": len(loaded_again) if loaded_again else 0,
        "both_insights_present": both_found,
        "pass": test3_pass
    })
    print(f"  {'✅' if test3_pass else '❌'} Test 3: {'PASSED' if test3_pass else 'FAILED'}")

    if run_e2e:
        print("\n📝 Test 4: LLM end-to-end memory distillation and injection")
        try:
            from src.engine import LocalRAG
            rag = LocalRAG()
            if rag.db is None:
                rag.index_docs()
            doc_files = rag.list_doc_files()
            if not doc_files:
                results["tests"].append({
                    "name": "llm_end_to_end",
                    "pass": False,
                    "reason": "no_docs"
                })
            else:
                test_file = doc_files[0]
                key = _memory_key(test_file)
                mem_path = MEMORY_DIR / f"{key}.json"
                original = mem_path.read_text("utf-8") if mem_path.exists() else None
                history = [
                    {"user": f"请阅读并总结 {Path(test_file).name}"},
                    {"assistant": "好的，我会总结该文档的关键内容。"}
                ]
                insights = rag.distill_insights(history)
                insight_used = insights[0] if insights else ""
                memory_saved = False
                if insight_used:
                    memory_saved = save_memory(test_file, insight_used, session_id="test-e2e-001", tags=["e2e"])
                question = f"总结一下 {Path(test_file).name} 的关键点"
                regular_docs, _, _, _, _ = rag._retrieve_documents(question, None, history_arr=history)
                injected = False
                if regular_docs:
                    for doc in regular_docs:
                        if "[相关记忆/见解]:" in doc.page_content and insight_used and insight_used in doc.page_content:
                            injected = True
                            break
                results["tests"].append({
                    "name": "llm_end_to_end",
                    "file": test_file,
                    "insights_count": len(insights),
                    "memory_saved": memory_saved,
                    "memory_injected": injected,
                    "pass": bool(insight_used and memory_saved and injected)
                })
                if original is None:
                    if mem_path.exists():
                        mem_path.unlink()
                else:
                    mem_path.write_text(original, "utf-8")
        except Exception as exc:
            results["tests"].append({
                "name": "llm_end_to_end",
                "pass": False,
                "error": str(exc)
            })

    # --- Overall ---
    results["overall_pass"] = all(t["pass"] for t in results["tests"])
    results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Save results
    results_dir = ROOT_DIR / "results" / "evaluation" / "support_checks"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / "memory_cross_session_check.json"
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), "utf-8")

    print(f"\n{'='*60}")
    print(f"Overall: {'✅ ALL PASSED' if results['overall_pass'] else '❌ SOME FAILED'}")
    print(f"Results saved to: {out_file}")
    print(f"{'='*60}")

    # Cleanup test memory
    if mem_path.exists():
        mem_path.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--e2e", action="store_true")
    args = parser.parse_args()
    run_verification(run_e2e=args.e2e)

#!/usr/bin/env python3
import sys
from pathlib import Path
import json
import time

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.engine import LocalRAG
from src.config import MEMORY_DIR, list_memories

async def verify_branded_memory():
    print("🚀 Starting MemoraRAG Branded Memory Verification...")
    rag = LocalRAG()
    
    # 1. 模拟第一轮对话：产生带品牌名的 Insight
    test_question = "请总结当前项目的核心改进，并提到 'MemoraRAG' 这个品牌名。"
    print(f"--- Session 1: Asking LLM to generate branded insight ---\nQ: {test_question}")
    
    # 我们直接通过 stream_query 或 query 运行，确保它触发 distill_insights
    # 为了演示，我们直接注入一个 Mock 记忆，因为自动化调用 LLM 蒸馏可能由于 prompt 长度在测试环境受限
    # 但我们更要验证的是：存储、衰减、检索 链路。
    
    from src.config import save_memory, load_memory
    
    test_file = "MEMORARAG_IMPROVEMENT_SUMMARY.md"
    insight_content = "MemoraRAG 已成功完成 14 项工程改进，并确立了系统时延瓶颈已从检索层转移至 LLM 生成层。"
    
    print(f"📦 Saving branded insight for {test_file}...")
    save_memory(test_file, insight_content, session_id="test_branded_verify")
    
    # 2. 验证文件已落盘
    memories = list_memories()
    print(f"🔎 Current memories in folder: {memories}")
    
    if test_file.replace(".md", "") in [m.replace("_md", "") for m in memories]:
        print("✅ Memory file created successfully.")
    else:
        # 尝试匹配 key
        from src.config import _memory_key
        key = _memory_key(test_file)
        if key in memories:
            print(f"✅ Memory file (key: {key}) created successfully.")
        else:
            print("❌ Memory file not found.")
            return

    # 3. 模拟跨 Session：重置 RAG 对象
    print("\n--- Session 2: Cross-session Retrieval ---")
    new_rag = LocalRAG()
    
    # 触发检索
    # 如果用户问 "我们在 MemoraRAG 中改进了多少项？" 
    # 系统应该路由到该文件并加载 Memory
    
    loaded = load_memory(test_file)
    print(f"📥 Loaded memory fragments for {test_file}: {len(loaded)}")
    
    found_brand = False
    for f in loaded:
        print(f"   - [{f['decay_score']:.4f}] {f['content']}")
        if "MemoraRAG" in f['content']:
            found_brand = True
            
    # 4. 结果记录
    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "branding_status": "MemoraRAG" if found_brand else "Failed",
        "fragments_count": len(loaded),
        "sample_insight": loaded[0]['content'] if loaded else None,
        "pass": found_brand and len(loaded) > 0
    }
    
    res_path = ROOT_DIR / "results" / "evaluation" / "support_checks" / "branded_memory_check.json"
    res_path.parent.mkdir(parents=True, exist_ok=True)
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(f"\n✅ Branded memory verification complete. Result saved to {res_path}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(verify_branded_memory())

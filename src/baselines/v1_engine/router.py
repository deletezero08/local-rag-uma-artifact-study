import os
import re
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

logger = logging.getLogger("rag_core")

class IntentRouter:
    """
    Decouples intent analysis (Fast-track, LLM, and Memory Fallback) 
    from the main LocalRAG engine.
    """
    
    def __init__(self, llm: Any, doc_list_func: Any) -> None:
        self.llm = llm
        self.get_all_files = doc_list_func
        self.stats = {
            "hits": 0,
            "bypass": 0,
            "misses": 0,
            "memory_fallback": 0,
            "smalltalk": 0
        }

    def is_smalltalk(self, question: str) -> bool:
        """Detect simple greetings or non-RAG queries."""
        smalltalk_keywords = ["你好", "你是谁", "在吗", "谢谢", "再见", "你能做什么", "自我介绍", "哈喽", "hello", "hi"]
        q = question.strip().lower().replace("，", "").replace("。", "").replace("？", "").replace("!", "").replace("！", "")
        
        if any(kw == q for kw in smalltalk_keywords):
            return True
            
        simple_patterns = [
            r"^(你好|哈喽|hi|hello|hey|早上好|中午好|下[午晚]好|请问你是|你是谁)",
            r"(你好|哈喽|hi|hello|hey).*(请问|是谁|名字)",
            r"^(谢谢|感谢|太棒了|厉害了|真棒)",
            r"^(再见|拜拜|bye)"
        ]
        return any(re.search(p, q) for p in simple_patterns) or len(q) <= 2

    def is_referential(self, question: str) -> bool:
        """Detect referential phrases like 'it', 'this doc', etc."""
        referential_phrases = ["它", "这份", "该文档", "上述内容", "上面提到的", "继续", "补充", "还有哪些", "下一步"]
        q = question.lower()
        return any(phrase in q for phrase in referential_phrases)

    def pick_recent_context(self, history_arr: Optional[List[Dict[str, Any]]], all_files: List[str]) -> Tuple[Optional[str], str]:
        """Backtrack history or memory to find the most relevant document for referential queries."""
        from .config import MEMORY_DIR
        import urllib.parse
        
        # 1. History backtrack
        if history_arr:
            for msg in reversed(history_arr):
                content = ((msg.get("assistant", "") or "") + " " + (msg.get("user", "") or "") + " " + (msg.get("content", "") or "")).lower()
                for rel_path in all_files:
                    if os.path.basename(rel_path).lower() in content or rel_path.lower() in content:
                        return rel_path, "history_match"

        # 2. Memory directory backtrack
        if MEMORY_DIR.exists():
            mem_files = sorted(list(MEMORY_DIR.glob("*.json")), key=lambda x: x.stat().st_mtime, reverse=True)
            for mem_file in mem_files:
                if mem_file.stem == "global_memory": continue
                target_rel_path = urllib.parse.unquote(mem_file.stem)
                if target_rel_path in all_files:
                    return target_rel_path, "recent_memory"
        return None, "none"

    def extract_intent_llm(self, question: str, all_files: List[str]) -> Optional[Dict[str, Any]]:
        """Use LLM to identify target file/dir/category."""
        if not self.llm or len(question) < 5: return None
        
        # Bypass check
        file_keywords = ["文件", "目录", "文件夹", "第", "最新", "最后", "pdf", "word", "excel", "表格", "这张", "那张"]
        if not any(k in question.lower() for k in file_keywords):
            self.stats["bypass"] += 1
            return None

        display_files = sorted(all_files)[:100]
        file_list_str = "\n".join(f"- {f}" for f in display_files)
        prompt = f"[File Intent Engine]\nList:\n{file_list_str}\n\nStrict JSON Format Only:\n{{\"target_file\": \"name/null\", \"target_dir\": \"name/null\", \"category\": \"pdf/word_text/image/data_web/markdown/null\"}}\n\nUser: {question}"

        try:
            raw = self.llm.invoke(prompt)
            match = re.search(r'\{.*\}', raw.strip(), re.DOTALL)
            if match:
                result = json.loads(match.group())
                if candidate := result.get("target_file"):
                    if candidate not in all_files: result["target_file"] = None
                return result
        except Exception as e:
            logger.warning(f"Router LLM Error: {e}")
        return None

    def analyze(self, question: str, category: Optional[str] = None, history_arr: Optional[List[Dict[str, Any]]] = None) -> Tuple[Optional[str], set, Optional[str], Dict[str, Any]]:
        """Main orchestration of intent routing."""
        all_files = self.get_all_files()
        target_filename, target_dirs, detected_category = None, set(), None
        meta = {"intent_state": "none", "fallback_triggered": False, "fallback_reason": "none", "memory_fallback_file": None}

        # 1. Smalltalk
        if self.is_smalltalk(question):
            self.stats["smalltalk"] += 1
            meta["intent_state"] = "smalltalk"
            return None, set(), None, meta

        # 2. Fast Track Regex
        cleaned_q = question.lower()
        for rel_path in all_files:
            filename = Path(rel_path).name.lower()
            if re.search(r'(?<![a-zA-Z0-9])' + re.escape(filename) + r'(?![a-zA-Z0-9])', cleaned_q):
                target_filename = rel_path
                meta["intent_state"] = "hit"
                break

        # 3. LLM Intent
        if not target_filename:
            llm_result = self.extract_intent_llm(question, all_files)
            if llm_result:
                target_filename = llm_result.get("target_file")
                if llm_result.get("target_dir"): target_dirs.add(llm_result["target_dir"])
                detected_category = llm_result.get("category")
                if target_filename or target_dirs or detected_category: meta["intent_state"] = "hit"

        # 4. Memory Fallback
        if not target_filename and not target_dirs and not category and self.is_referential(question):
            mem_file, reason = self.pick_recent_context(history_arr, all_files)
            if mem_file:
                target_filename = mem_file
                meta["intent_state"] = "memory_fallback"
                meta["fallback_triggered"] = True
                meta["fallback_reason"] = reason
                meta["memory_fallback_file"] = mem_file
                self.stats["memory_fallback"] += 1

        final_cat = category if category not in (None, "", "all") else detected_category
        if meta["intent_state"] == "hit": self.stats["hits"] += 1
        elif meta["intent_state"] == "none": self.stats["misses"] += 1
        
        return target_filename, target_dirs, final_cat, meta

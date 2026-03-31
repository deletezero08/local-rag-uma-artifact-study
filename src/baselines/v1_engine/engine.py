import sys
import os
import time
import asyncio
import logging
import json
import re
import math
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple, Iterator, AsyncGenerator

logger = logging.getLogger("rag_core")

if sys.version_info >= (3, 14):
    raise RuntimeError(
        "当前项目依赖的 chromadb 在 Python 3.14 下不兼容。"
        "请改用 Python 3.13 运行，例如执行 ./start_gui.command。"
    )

import torch
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
from .config import (
    DOCS_DIR,
    EMBED_MODEL,
    LLM_MODEL,
    MEMORY_DIR,
    OLLAMA_HOST,
    SKILLS_DIR,
    ensure_dirs,
    get_runtime_status,
    has_persisted_index,
    list_doc_files,
    list_skill_files,
    load_memory,
    record_file_usage,
    settings,
)
from .indexer import LOADER_MAP, load_persisted_db, rebuild_index, reset_index_storage
from .retriever import build_qa_chain, build_retriever, extract_sources
from .router import IntentRouter
try:
    from .router_v2 import get_router_v2
    from .kv_compressor import KVCompressor
    SOTA_AVAILABLE = True
except ImportError:
    SOTA_AVAILABLE = False

logger = logging.getLogger("rag_core")

# Session statistics managed by IntentRouter


class LocalRAG:
    def __init__(self) -> None:
        print("🚀 初始化忆联检索 MemoraRAG...")
        self.embeddings: Optional[HuggingFaceEmbeddings] = None
        self.llm: Optional[OllamaLLM] = None
        self.db: Optional[Any] = None
        self.qa: Optional[Any] = None
        self.retriever: Optional[Any] = None
        self._runtime_initialized: bool = False
        self.router: Optional[IntentRouter] = None

        prompt_template = """你是一个专业的中文知识库问答助手。请仔细阅读以下参考资料和对话历史，然后据此回答用户的问题。

当前系统时间: {current_time}

规则：
1. 优先使用参考资料中的原文信息，并结合之前的对话上下文进行理解。
2. 如果参考资料中没有相关内容，请明确说明"根据提供的文档，我无法找到相关信息"。
3. 回答时尽量标注信息来源（如"根据第X页..."）。
4. 如果问题涉及时间线、最新文件或对比，请务必参考各个【参考资料】的修改时间与【当前系统时间】。
5. 如果问题涉及多个文档，请先在内心进行综合分析和信息梳理，再给出结构化的结论。
6. 【关键规则】如果用户的问题是要求“分析”、“翻译”、“总结”某个具体文件（如“分析 rag 下的第一个 pdf”），说明这就是一个指令任务。请直接将下面给出的【参考资料】视作用户所指的文件内容，并对其执行翻译或总结任务！不要死板地在内容里搜索“第一个pdf”这样的字眼。
7. 不要凭空捏造，只基于参考资料和历史上下文作答。
8. 输出请使用清晰的 Markdown 格式（使用标题、列表或表格让信息易读）。

{skills}
{global_memory}
【历史对话记录】（如果没有则忽略）:
{history}

【参考资料】:
{context}

用户问题: {question}

你的回答:"""
        self.prompt_zh = PromptTemplate(
            template=prompt_template,
            input_variables=["history", "context", "question", "current_time", "skills", "global_memory"],
        )
        
        prompt_template_en = """You are a professional RAG (Retrieval-Augmented Generation) assistant. document analysis. Please read the following reference materials and conversation history carefully, then answer the user's question.

Current System Time: {current_time}

Rules:
1. Prioritize information from the reference materials and use conversation context.
2. If the answer is not in the references, state "Based on the provided documents, I cannot find relevant information."
3. Cite sources (e.g., "According to page X...").
4. For timeline or comparison questions, refer to file modification times vs Current System Time.
5. If the user asks to "analyze", "translate", or "summarize" a specific file (e.g., "analyze the first pdf in rag/"), treat the provided 【Reference Materials】 as that file's content and perform the task. Do not literally search for "first pdf".
6. Do not hallucinate. Stay grounded in the references and context.
7. Use clear Markdown (headers, lists, or tables).

{skills}
{global_memory}
【Conversation History】 (Ignore if empty):
{history}

【Reference Materials】:
{context}

User Question: {question}

Your Answer (Please reply in English):"""
        self.prompt_en = PromptTemplate(
            template=prompt_template_en,
            input_variables=["history", "context", "question", "current_time", "skills", "global_memory"],
        )
        
        # Default prompt
        self.current_prompt: PromptTemplate = self.prompt_zh if "zh" in EMBED_MODEL.lower() else self.prompt_en
        
        # Retrieval Mode (Exp-A: ensemble, Exp-B: rrf, Baseline: vector_only)
        self.retrieval_mode = os.getenv("RAG_RETRIEVAL_MODE", settings["retrieval"].get("default_mode", "rrf"))

        if has_persisted_index():
            self.load_indexed_db()

    def _ensure_runtime(self) -> None:
        if self._runtime_initialized:
            return
        if self.embeddings is None:
            device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
            print(f"📥 加载 Embedding 模型 ({device} 加速): {EMBED_MODEL}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=EMBED_MODEL,
                model_kwargs={"device": device},
                encode_kwargs={
                    "normalize_embeddings": True,
                    "batch_size": 64
                },
            )

        if self.llm is None:
            import httpx
            print(f"🧠 唤醒本地大模型: {LLM_MODEL}")
            self._http_client = httpx.Client(timeout=120.0)
            self.llm = OllamaLLM(
                model=LLM_MODEL, 
                temperature=settings.get("llm", {}).get("temperature", 0.1),
                base_url=OLLAMA_HOST
            )
            
            # --- V2 升级: Agentic Router (DSPy) ---
            v2_cfg = settings.get("v2_sota", {})
            if v2_cfg.get("agentic_router", False) and SOTA_AVAILABLE:
                print("🤖 启用 V2 Agentic 路由代理 (DSPy)...")
                self.router = get_router_v2(LLM_MODEL)
            else:
                self.router = IntentRouter(self.llm, self.list_doc_files)
                
            # --- V2 升级: KV Cache 压缩初始化 ---
            if v2_cfg.get("kv_compression", False) and SOTA_AVAILABLE:
                self.kv_compressor = KVCompressor(
                    compression_ratio=v2_cfg.get("compression_ratio", 0.5),
                    strategy=v2_cfg.get("strategy", "dynamic")
                )
        self._runtime_initialized = True

    def list_doc_files(self) -> List[str]:
        return list_doc_files()

    def list_skill_files(self) -> List[str]:
        return list_skill_files()

    @staticmethod
    def _ensure_dirs() -> None:
        ensure_dirs()

    def get_status(self) -> Dict[str, Any]:
        status = get_runtime_status()
        status["has_index"] = self.db is not None or status["has_index"]
        return status

    def index_docs(self, progress_callback: Optional[Any] = None) -> Dict[str, Any]:
        if progress_callback: progress_callback({"type": "progress", "message": "检查并加载向量模型..."})
        self._ensure_runtime()
        ensure_dirs()
        
        db, result = rebuild_index(self.embeddings, progress_callback=progress_callback)
        if not result["ok"]:
            return result
        
        # 仅在有变动或初始构建时更新
        if db:
            self.db = db
            self._build_qa_chain()
        return result

    def load_indexed_db(self) -> bool:
        if not has_persisted_index():
            return False

        print("📂 尝试加载已有知识库...")
        try:
            self._ensure_runtime()
            self.db = load_persisted_db(self.embeddings)
            self._build_qa_chain()
            print("   ✅ 知识库挂载成功！")
            return True
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"   ⚠️ 加载已有知识库失败: {exc}")
            if "no such table: collections" in str(exc).lower():
                print("   ⚠️ 检测到损坏的 Chroma 索引，正在自动重置索引目录...")
                logger.warning("corrupt_chroma_detected_resetting_storage")
                try:
                    reset_index_storage()
                except OSError as reset_exc:
                    logger.exception("failed_to_reset_corrupt_chroma: %s", reset_exc)
            self.db = None
            self.qa = None
            self.retriever = None
            return False

    def _build_qa_chain(self) -> None:
        if self.db is None:
            self.qa = None
            self.retriever = None
            return

        print(f"🔍 构建检索器 (Mode: {self.retrieval_mode})...")
        self.retriever = build_retriever(self.db, mode=self.retrieval_mode)
        # 动态选择 Prompt
        self.current_prompt = self.prompt_zh if "zh" in EMBED_MODEL.lower() else self.prompt_en
        self.qa = build_qa_chain(self.llm, self.retriever, self.current_prompt)

    def _get_category_documents(self, category: Optional[str]) -> Optional[List[Document]]:
        if self.db is None or category in (None, "", "all"):
            return None

        db_data = self.db.get(where={"file_category": category})
        documents: List[Document] = []
        if db_data and db_data.get("documents"):
            for index, text in enumerate(db_data["documents"]):
                metadata = db_data["metadatas"][index] if db_data.get("metadatas") else {}
                documents.append(Document(page_content=text, metadata=metadata))
        return documents

    def _analyze_intent(self, question: str, category: Optional[str] = None, history_arr: Optional[List[Dict[str, Any]]] = None) -> Tuple[Optional[str], set, Optional[str], Dict[str, Any]]:
        if not self.router: return None, set(), None, {"intent_state": "none", "fallback_triggered": False, "fallback_reason": "none", "memory_fallback_file": None}
        return self.router.analyze(question, category, history_arr)

    def _retrieve_documents(self, question: str, category: Optional[str] = None, history_arr: Optional[List[Dict[str, Any]]] = None) -> Tuple[List[Document], List[Document], Optional[str], Optional[str], Dict[str, Any]]:
        if self.db is None:
            return [], [], None, None
        all_files = self.list_doc_files()
        
        target_filename, target_dirs, final_category, meta = self._analyze_intent(question, category, history_arr)

        filters: List[Dict[str, Any]] = []
        if final_category:
            logger.info("intent_extracted category=%s", final_category)
            filters.append({"file_category": final_category})

        if target_filename:
            logger.info("intent_extracted target_file=%s", target_filename)
            filters.append({"source": str(DOCS_DIR / target_filename)})
        elif target_dirs:
            logger.info("intent_extracted target_dirs=%s", target_dirs)
            dir_file_sources = []
            for filename in all_files:
                parts = Path(filename).parts
                if any(d in parts for d in target_dirs):
                    dir_file_sources.append({"source": str(DOCS_DIR / filename)})
            if dir_file_sources:
                if len(dir_file_sources) == 1:
                     filters.append(dir_file_sources[0])
                else:
                     filters.append({"$or": dir_file_sources})

        if not filters:
            docs = self.retriever.invoke(question)
        else:
            if len(filters) == 1:
                filter_dict = filters[0]
            else:
                filter_dict = {"$and": filters}

            logger.debug("retrieval_filter_active filter=%s", filter_dict)

            # 优化 A: 无明确意图时不落到具体文件
            if target_filename and target_filename not in all_files:
                logger.warning("intent_target_not_found filename=%s, falling back", target_filename)
                meta["fallback_triggered"] = True
                meta["fallback_reason"] = "target_not_found"
                target_filename = None
                filter_dict = None

            # 改进：如果锁定了特定文件，限制 k 并禁用跨文件召回
            if target_filename:
                target_k = settings["retrieval"].get("vector_k", 12)
                search_params = {"k": target_k, "filter": filter_dict}
            else:
                target_k = 6
                search_params = {"k": target_k, "fetch_k": target_k * 3, "filter": filter_dict}

            vector_retriever = self.db.as_retriever(
                search_type="mmr" if not target_filename else "similarity",
                search_kwargs=search_params,
            )
            docs = vector_retriever.invoke(question)

        # 4. 分离 Skill 和普通文档
        skills = [d for d in docs if d.metadata.get("is_skill")]
        regular_docs = [d for d in docs if not d.metadata.get("is_skill")]

        # Reranker 精排：对普通文档进行二次评分（受配置开关控制）
        reranker_cfg = settings.get("reranker", {})
        if reranker_cfg.get("enabled", False) and len(regular_docs) > 5 and not target_filename:
            top_k = reranker_cfg.get("top_k", 8)
            regular_docs = self._rerank_documents(question, regular_docs, top_k=top_k)

        # --- 注入知识记忆 (Inject Knowledge Memory) ---
        memory_top_k = settings.get("memory", {}).get("top_k", 5)
        for doc in regular_docs:
            source_path = doc.metadata.get("source") or ""
            rel_path = "未知"
            if source_path:
                p = Path(source_path)
                try:
                    if str(DOCS_DIR) in str(p):
                        rel_path = str(p.relative_to(DOCS_DIR))
                    elif str(SKILLS_DIR) in str(p):
                        rel_path = str(p.relative_to(SKILLS_DIR))
                except ValueError:
                    rel_path = p.name

            fragments = load_memory(rel_path)
            if fragments:
                active_fragments = fragments[:memory_top_k]
                memory_text = ' '.join([f.get('content', '') for f in active_fragments])
                if memory_text:
                    if not doc.page_content.endswith('\n'):
                        doc.page_content += '\n'
                    doc.page_content += f'\n[相关记忆/见解]: {memory_text}'

        return regular_docs, skills, final_category, target_filename, meta

    def distill_insights(self, history_arr: List[Dict[str, Any]]) -> List[str]:
        if not self.llm or not history_arr:
            return []
        
        history_text = self._format_history(history_arr)
        prompt = f"""你是一个高级知识提取专家。请分析以下对话历史，并提炼出关于其中提到的核心结论、事实或深入见解。

提炼原则 (Extraction Principles)：
1. **原子化 (Atomic)**: 每条见解应独立且完整，只包含一个核心事实或逻辑。
2. **客观性 (Objective)**: 使用第三人称描述，不要包含对话语气（如“我认为”、“刚才说到”）。
3. **高密度 (High Density)**: 剔除废话，保留硬核知识。
4. **归口 (Assignment)**: 确保见解是针对文档内容的，而不是针对对话格式的。

对话历史：
{history_text}

提炼总结 (请每行返回一条见解，每条不超过 100 字，不要使用任何列表符号或序号):"""

        try:
            print('🤖 [Memory Distillation] Invoking LLM for extraction...')
            raw_response = self.llm.invoke(prompt)
            raw_text = getattr(raw_response, 'content', str(raw_response)).strip()
            
            lines_out = [re.sub(r'^[\d\. \-\*]+', '', line).strip() for line in raw_text.split('\n') if line.strip()]
            
            insights = []
            for line in lines_out:
                if len(line) > 10:
                    insights.append(line)
            
            print(f'✨ [Memory Distillation] Successfully distilled {len(insights)} atomic fragments.')
            return insights
        except Exception as e:
            print(f'❌ [Memory Distillation] Failed: {e}')
            logger.error('distill_insights_failed: %s', e)
            return []

    def _rerank_documents(self, question: str, docs: List[Document], top_k: int = 8) -> List[Document]:
        """
        性能优化版：使用单个 LLM 调用对多个候选段落进行批量打分。
        这比循环逐个打分快 10 倍以上。
        """
        if not docs or self.llm is None:
            return docs[:top_k]

        logger.info("rerank_bulk_start candidates=%s top_k=%s", len(docs), top_k)

        # 构造批量评分 Prompt
        snippets_text = ""
        for i, doc in enumerate(docs):
            content = doc.page_content.replace("\n", " ")[:200]
            snippets_text += f"ID:{i} | 内容: {content}\n"

        score_prompt = (
            f"请评估以下 {len(docs)} 个段落与用户问题\u201c{question}\u201d的相关性。\n"
            f"对于每个段落，给出 0-10 的评分（10为最相关）。\n"
            f"【严格要求】只返回一个 JSON 数组（按 ID 顺序排序的分数），例如: [8, 2, 9, 5...]\n"
            f"不要输出任何解释说明。\n\n"
            f"待评估段落：\n{snippets_text}\n"
            f"评分结果 (仅 JSON 数组):"
        )

        try:
            raw = self.llm.invoke(score_prompt).strip()

            match = re.search(r'\[[\d,\s.]+\]', raw)
            if match:
                scores = json.loads(match.group())
            else:
                scores = [int(s) for s in re.findall(r'\d+', raw)]

            scored = []
            for i, doc in enumerate(docs):
                score = scores[i] if i < len(scores) else 5
                scored.append((score, doc))

            scored.sort(key=lambda x: x[0], reverse=True)
            result = [doc for _, doc in scored[:top_k]]
            logger.info("rerank_bulk_success scores=%s", scores[:top_k])
            return result

        except Exception as e:
            logger.error("rerank_bulk_failed: %s", e)
            return docs[:top_k]

    def _build_skills_text(self, skills: List[Document]) -> str:
        """构建技能注入文本（全局 + 检索到的）。"""
        global_skills = []
        for f in SKILLS_DIR.glob('*'):
            if f.is_file() and f.name != '.gitkeep' and not f.name.startswith('.'):
                try:
                    content = f.read_text("utf-8").strip()
                    if content:
                        global_skills.append(f"【全局固定指令 - {f.name}】: {content}")
                except Exception:
                    continue

        if not global_skills and not skills:
            return ""

        combined = "【检测到匹配的专业技能指令，请务必作为行为准则优先遵循】:\n"
        for i, s in enumerate(global_skills, 1):
            combined += f"A{i}. {s}\n"
        for i, s in enumerate(skills, 1):
            fname = os.path.basename(s.metadata.get("source", "未知技能"))
            combined += f"B{i}. 局部技能[{fname}]: {s.page_content}\n"
        return combined

    @staticmethod
    def _build_global_memory_text() -> str:
        """获取全局记忆注入文本。"""
        global_mem_data = load_memory("global_memory")
        if global_mem_data:
            return f"【全局知识库见解 (Global Insights)】: {global_mem_data.get('insight', '')}\n"
        return ""

    @staticmethod
    def _format_context(source_docs: List[Document]) -> str:
        """将检索文档格式化为参考资料文本。"""
        parts = []
        for i, doc in enumerate(source_docs, 1):
            filename = os.path.basename(doc.metadata.get("source", "未知来源"))
            mtime = doc.metadata.get("file_mtime_str", "未知")
            parts.append(f"[文档 {i}] 文件名: {filename}, 修改时间: {mtime}\n内容: {doc.page_content}")
        return "\n\n".join(parts)

    def _prepare_prompt(self, question: str, source_docs: List[Document], skills: List[Document], history_text: str) -> str:
        """统一构建最终 Prompt（query/stream_query 共用）。"""
        context = self._format_context(source_docs)
        skills_text = self._build_skills_text(skills)
        global_mem_text = self._build_global_memory_text()
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        return self.current_prompt.format(
            history=history_text,
            context=context,
            question=question,
            current_time=current_time,
            skills=skills_text,
            global_memory=global_mem_text,
        )

    def query(self, question: str, category: Optional[str] = None, history_arr: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        question = (question or "").strip()
        history_text = self._format_history(history_arr)

        if not question:
            return {"ok": False, "answer": "⚠️ 请输入问题。", "sources": []}

        if self.qa is None:
            return {"ok": False, "answer": "⚠️ 请先执行选项 1 索引文档！", "sources": []}

        self._ensure_runtime()
        print("🤔 思考中...")

        last_history_text = self._latest_history_text(history_arr)
        search_query = f"{last_history_text + ' ' if last_history_text else ''}{question}"
        source_docs, skills, _, _, meta = self._retrieve_documents(search_query, category, history_arr)
        source_docs = self._clip_context(source_docs)

        if category not in (None, "", "all") and not source_docs:
            return {
                "ok": False,
                "answer": "⚠️ 当前选择的文档类型下没有匹配内容，请切换左侧类型或重建索引后重试。",
                "sources": [],
            }

        prompt_text = self._prepare_prompt(question, source_docs, skills, history_text)
        answer = self.llm.invoke(prompt_text)

        return {
            "ok": True,
            "answer": answer,
            "sources": extract_sources(source_docs),
            "meta": meta,
            "source_docs": source_docs,
        }

    def _format_history(self, history_arr: Optional[List[Dict[str, Any]]]) -> str:
        if not history_arr or not isinstance(history_arr, list):
            return ""
        lines = []
        for msg in history_arr[-5:]: # Keep last 5 messages for context window
            if not isinstance(msg, dict):
                continue
            role_raw = msg.get("role", "")
            role = "用户" if role_raw == "user" else "AI助手"
            content = msg.get("content", "").strip()
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _latest_history_text(self, history_arr: Optional[List[Dict[str, Any]]]) -> str:
        if not history_arr or not isinstance(history_arr, list):
            return ""
        last = history_arr[-1]
        if not isinstance(last, dict):
            return ""
        if last.get("content"):
            return str(last.get("content")).strip()
        user_text = str(last.get("user", "")).strip()
        assistant_text = str(last.get("assistant", "")).strip()
        return assistant_text or user_text

    def _clip_context(self, source_docs: List[Document]) -> List[Document]:
        """按均匀分配策略裁剪上下文，保证每个文档获得公平预算。"""
        eval_cfg = settings.get("evaluation", {})
        budget = int(eval_cfg.get("context_char_budget", 3000))
        if budget <= 0 or not source_docs:
            return source_docs
        # 过滤掉空文档
        valid_docs = [d for d in source_docs if (d.page_content or "").strip()]
        if not valid_docs:
            return []
        # 均匀分配预算（排名靠前的文档获得 1.5x 权重）
        n = len(valid_docs)
        weights = [1.5 if i < n // 3 else 1.0 for i in range(n)]
        total_weight = sum(weights)
        clipped: List[Document] = []
        for doc, w in zip(valid_docs, weights):
            per_doc_budget = max(100, int(budget * w / total_weight))
            text = doc.page_content.strip()
            piece = text[:per_doc_budget]
            clipped.append(Document(page_content=piece, metadata=dict(doc.metadata)))
        return clipped

    def stream_query(self, question: str, category: Optional[str] = None, history_arr: Optional[List[Dict[str, Any]]] = None) -> Iterator[Dict[str, Any]]:
        question = (question or "").strip()
        history_text = self._format_history(history_arr)

        logger.info("stream_query_start question_len=%s", len(question))
        if not question:
            logger.info("stream_query_reject_empty")
            yield {"type": "error", "data": "⚠️ 请输入问题！"}
            return

        if self.db is None or self.retriever is None:
            logger.info("stream_query_reject_no_index")
            yield {"type": "error", "data": "⚠️ 请先构建索引！"}
            return

        self._ensure_runtime()
        
        last_history_text = self._latest_history_text(history_arr)
        search_query = f"{last_history_text + ' ' if last_history_text else ''}{question}"
        
        # 0. 通知前端：正在分析意图
        yield {"type": "status", "data": "🔍 正在分析您的意图..."}
        
        # 1. 检索
        yield {"type": "status", "data": "📂 正在检索知识库..."}
        source_docs, skills, final_category, target_filename, meta = self._retrieve_documents(search_query, category, history_arr)
        source_docs = self._clip_context(source_docs)
        
        # 通知前端：意图分析完成
        status_msg = "🔍 意图分析完成。"
        if meta.get("intent_state") == "memory_fallback":
            status_msg = "🧠 命中指代性兜底。"
            
        if final_category:
            status_msg += f" 类别: {final_category}."
        if target_filename:
            status_msg += f" 目标文件: {os.path.basename(target_filename)}."
        if meta.get("intent_state") == "memory_fallback":
             if meta.get("fallback_reason") == "recent_memory":
                 status_msg += " (基于近期记忆)"
             else:
                 status_msg += " (基于历史记忆)"
        
        yield {"type": "status", "data": status_msg}

        if target_filename and source_docs:
            first_source = os.path.basename(source_docs[0].metadata.get("source", ""))
            yield {"type": "status", "data": f"📑 正在分析指定文档: {first_source}..."}
        elif source_docs:
            first_source_path = source_docs[0].metadata.get("source", "")
            yield {"type": "status", "data": "📑 正在提取全库最相关的参考片段..."}
            try:
                rel_path = str(Path(first_source_path).relative_to(DOCS_DIR))
                record_file_usage([rel_path])
            except Exception:
                pass
        
        if category not in (None, "", "all") and not source_docs:
            logger.info("stream_query_no_docs_for_category category=%s", category)
            yield {"type": "error", "data": "当前选择的文档类型下没有匹配内容，请切换左侧类型或重建索引后重试。"}
            return
            
        logger.info("stream_query_retrieved_docs=%s skills=%s", len(source_docs), len(skills))
        
        # 2. 构建 Prompt（复用公共方法）
        prompt_text = self._prepare_prompt(question, source_docs, skills, history_text)
        logger.info("stream_query_prompt_len=%s", len(prompt_text))

        has_token = False
        for chunk in self.llm.stream(prompt_text):
            text = chunk if isinstance(chunk, str) else getattr(chunk, "content", str(chunk))
            if text:
                has_token = True
                yield {"type": "token", "data": text}

        if not has_token:
            logger.info("stream_query_no_token")
            yield {
                "type": "error",
                "data": "模型未返回内容。请确认 Ollama 服务和模型状态（例如 qwen3:8b）后重试。",
            }
            return

        logger.info("stream_query_done_with_token")
        yield {"type": "sources", "data": extract_sources(source_docs)}

    @staticmethod
    def _extract_sources(source_docs):
        return extract_sources(source_docs)


def main():
    from scripts.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())

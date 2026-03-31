#!/usr/bin/env python3
import os
import sys
import json
import time
import copy
import resource
from typing import List, Dict, Any, Optional
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.engine import LocalRAG
from src.config import settings
from scripts.logger import log_entry

class RAGEvaluator:
    def __init__(self, model_name: str = None):
        self.rag = LocalRAG()
        # Use config if model_name not provided
        self.grading_model = model_name or settings.get("llm", {}).get("judge_model", "qwen3:8b")
        self.results_dir = Path(ROOT_DIR).parent / "results" / "evaluation"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _clip_text(text: str, max_chars: int) -> str:
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "...(truncated)"

    @staticmethod
    def _get_peak_rss_mb() -> float:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        raw = float(usage.ru_maxrss)
        if raw > 10_000_000:
            return raw / (1024.0 * 1024.0)
        return raw / 1024.0

    def _probe_ttft(self, question: str, category: str = "all") -> Optional[float]:
        start = time.time()
        try:
            gen = self.rag.stream_query(question, category=category)
            for event in gen:
                if event.get("type") == "token":
                    return time.time() - start
                if event.get("type") == "error":
                    return None
            return None
        except Exception:
            return None

    def _merge_eval_config(self, custom_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged = dict(settings.get("evaluation", {}))
        if custom_params and isinstance(custom_params.get("evaluation"), dict):
            merged.update(custom_params["evaluation"])
        return merged

    def _apply_retrieval_overrides(self, custom_params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not custom_params or not isinstance(custom_params.get("retrieval"), dict):
            return None
        retrieval_cfg = settings.setdefault("retrieval", {})
        backup = copy.deepcopy(retrieval_cfg)
        for key, value in custom_params["retrieval"].items():
            retrieval_cfg[key] = value
        return backup

    def _restore_retrieval_overrides(self, backup: Optional[Dict[str, Any]]) -> None:
        if backup is None:
            return
        settings["retrieval"] = backup

    def _load_question_set(self) -> List[Dict[str, Any]]:
        def load_json_cases(path: Path) -> List[Dict[str, Any]]:
            data = json.loads(path.read_text("utf-8"))
            rows = []
            for item in data:
                rows.append(
                    {
                        "id": item.get("id"),
                        "type": item.get("type", "unknown"),
                        "question": item.get("question", ""),
                        "source_docs": item.get("source_docs", []),
                        "ground_truth": item.get("ground_truth_candidate", item.get("ground_truth", "")),
                    }
                )
            return rows

        custom_cases = os.environ.get("EVAL_CASES_FILE", "").strip()
        if custom_cases:
            custom_path = Path(custom_cases)
            if not custom_path.is_absolute():
                custom_path = Path(ROOT_DIR) / custom_path
            if custom_path.exists():
                try:
                    rows = load_json_cases(custom_path)
                    print(f"✅ 已加载测试集(环境变量): {custom_path.name} (共 {len(rows)} 条)")
                    return rows
                except Exception as e:
                    print(f"⚠️ 解析 {custom_path.name} 失败: {e}，回退到默认数据集")

        verified_set = Path(ROOT_DIR).parent / "data" / "eval" / "test_cases_verified.json"
        if verified_set.exists():
            try:
                rows = load_json_cases(verified_set)
                print(f"✅ 已加载测试集: {verified_set.name} (共 {len(rows)} 条)")
                return rows
            except Exception as e:
                print(f"⚠️ 解析 {verified_set.name} 失败: {e}，回退到 Markdown 解析")

        # Fallback to question_set.md
        question_set = Path(ROOT_DIR).parent / "data" / "eval" / "question_set.md"
        if not question_set.exists():
            return []
        lines = question_set.read_text("utf-8").splitlines()
        rows = []
        for line in lines:
            if not line.startswith("|"):
                continue
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cols) < 4:
                continue
            if cols[0].lower() == "id" or cols[0].startswith("---"):
                continue
            rows.append({
                "id": cols[0],
                "type": cols[1],
                "question": cols[2],
                "source_docs": [c.strip() for c in cols[3].split(",") if c.strip()],
                "ground_truth": ""
            })
        print(f"✅ 已加载测试集: {question_set.name} (共 {len(rows)} 条，无标准答案)")
        return rows

    def _load_run_state(self) -> Dict[str, Any]:
        state_file = self.results_dir / "evaluation_run_state.json"
        if not state_file.exists():
            return {"completed_modes": {}}
        try:
            return json.loads(state_file.read_text("utf-8"))
        except Exception:
            return {"completed_modes": {}}

    def _save_run_state(self, state: Dict[str, Any]) -> None:
        state_file = self.results_dir / "evaluation_run_state.json"
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")

    def _load_mode_result_if_compatible(
        self,
        file_name: str,
        mode: str,
        n: int,
        iters: int,
        config_id: str,
        config_version: str
    ) -> Optional[Dict[str, Any]]:
        path = self.results_dir / file_name
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text("utf-8"))
            meta = data.get("metadata", {})
            if (
                meta.get("mode") == mode
                and meta.get("n") == n
                and meta.get("iterations") == iters
                and meta.get("config_id") == config_id
                and meta.get("config_version") == config_version
                and self._is_mode_complete(data.get("iterations", []), n, iters)
            ):
                return data
        except Exception:
            return None
        return None

    @staticmethod
    def _is_mode_complete(iter_results: List[List[Dict[str, Any]]], n: int, iters: int) -> bool:
        if len(iter_results) != iters:
            return False
        for rows in iter_results:
            if len(rows) != n:
                return False
        return True

    def _get_grade(
        self,
        question: str,
        ground_truth: str,
        answer: str,
        context: str,
        eval_cfg: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """Uses the LLM to grade the answer based on Faithfulness and Relevance."""
        eval_cfg = eval_cfg or settings.get("evaluation", {})
        metrics = eval_cfg.get("metrics", ["faithfulness", "relevance"])
        metrics_desc = "\n".join([f"{i+1}. {m.capitalize()}: ..." for i, m in enumerate(metrics)])
        max_context_chars = eval_cfg.get("max_grade_context_chars", 3600)
        max_answer_chars = eval_cfg.get("max_grade_answer_chars", 2200)
        max_truth_chars = eval_cfg.get("max_grade_truth_chars", 1400)
        clipped_context = self._clip_text(context, max_context_chars)
        clipped_answer = self._clip_text(answer, max_answer_chars)
        clipped_truth = self._clip_text(ground_truth, max_truth_chars)
        
        prompt = f"""作为一名公正的评分员，请评估 RAG 系统的回答质量。
参考资料: {clipped_context}
用户问题: {question}
标准答案: {clipped_truth}
系统回答: {clipped_answer}

请给出以下指标的评分（0-10分，只输出 JSON 格式，如 {{"faithfulness": 8, "relevance": 9}}）：
{metrics_desc}
评分 JSON:"""
        
        max_retries = eval_cfg.get("grade_max_retries", 2)
        for attempt in range(max_retries):
            try:
                # Cleanly invoke the model
                res = self.rag.llm.invoke(prompt)
                raw = res.content if hasattr(res, 'content') else str(res)
                raw = raw.strip()
                
                # Clean up the output to get pure JSON
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"): raw = raw[4:]
                
                # Robust JSON extraction
                import re
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                return json.loads(raw)
            except Exception as e:
                print(f"⚠️ 评分尝试 {attempt+1}/{max_retries} 失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1)) # Exponential backoff
                else:
                    print("❌ 达到最大重试次数，评分失败。")
                    return {"faithfulness": 0.0, "relevance": 0.0}

    def evaluate_mode(
        self,
        mode: str,
        test_cases: List[Dict[str, Any]],
        iterations: int = 1,
        checkpoint_tag: str = "",
        custom_params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        eval_cfg = self._merge_eval_config(custom_params)
        backup = self._apply_retrieval_overrides(custom_params)
        print(f"\n🚀 开始评估模式: {mode} (重复次数: {iterations})")
        self.rag.retrieval_mode = mode
        context_doc_limit = eval_cfg.get("phase_a_context_doc_limit", 6)
        context_chars_per_doc = eval_cfg.get("phase_a_context_chars_per_doc", 1000)
        checkpoint_interval = eval_cfg.get("checkpoint_interval", 5)
        collect_ttft = bool(eval_cfg.get("collect_ttft", False))
        try:
            self.rag._build_qa_chain()
        except Exception as e:
            print(f"⚠️ 构建 Q&A 链失败: {e}")
            self._restore_retrieval_overrides(backup)
            return []
        
        all_iterations_results = []
        tag_part = f"_{checkpoint_tag}" if checkpoint_tag else ""
        temp_file = self.results_dir / f"temp_{mode}{tag_part}_checkpoint.json"
        
        # Load progress if exists
        if temp_file.exists():
            with open(temp_file, "r") as f:
                all_iterations_results = json.load(f)
                # Assume 1 iteration for now or complexify as needed
                if all_iterations_results:
                    processed_ids = {c['id'] for iter_res in all_iterations_results for c in iter_res}
                    print(f"  ⏭️ 发现检查点，已跳过 {len(processed_ids)} 个已处理问题。")

        try:
            for i in range(iterations):
                print(f"  🔄 迭代 {i+1}/{iterations}...")
                iter_results = all_iterations_results[i] if i < len(all_iterations_results) else []
                iter_processed_ids = {c['id'] for c in iter_results}
                
                for case in test_cases:
                    if case['id'] in iter_processed_ids:
                        continue
                    
                    print(f"    📝 处理问题 {case['id']}...")
                    start_time = time.time()
                    rss_before = self._get_peak_rss_mb()
                    
                    try:
                        ttft = self._probe_ttft(case['question'], category="all") if collect_ttft else None
                        response = self.rag.query(case['question'], category="all")
                        elapsed = time.time() - start_time
                        rss_after = self._get_peak_rss_mb()
                        
                        source_docs = response.get("source_docs") or []
                        context_text = "\n".join([
                            d.page_content[:context_chars_per_doc] for d in source_docs[:context_doc_limit]
                        ])
                        
                        grades = self._get_grade(case['question'], case['ground_truth'], response['answer'], context_text, eval_cfg=eval_cfg)
                        meta = response.get("meta") or {}
                        
                        iter_results.append({
                            "id": case['id'],
                            "question": case['question'],
                            "answer": response['answer'],
                            "intent_state": meta.get("intent_state"),
                            "fallback_triggered": meta.get("fallback_triggered"),
                            "fallback_reason": meta.get("fallback_reason"),
                            "memory_fallback_file": meta.get("memory_fallback_file"),
                            "latency": elapsed,
                            "ttft": ttft,
                            "estimated_tokens": max(1, int(len(str(response['answer'])) / 1.6)),
                            "tokens_per_sec": round(max(1, int(len(str(response['answer'])) / 1.6)) / elapsed, 3) if elapsed > 0 else 0.0,
                            "chars_per_sec": round(len(str(response['answer'])) / elapsed, 3) if elapsed > 0 else 0.0,
                            "rss_peak_mb": round(rss_after, 3),
                            "rss_peak_delta_mb": round(max(0.0, rss_after - rss_before), 3),
                            "scores": grades,
                            "sources_count": len(response.get('sources', []))
                        })
                        iter_processed_ids.add(case['id'])
                        
                        if i < len(all_iterations_results):
                            all_iterations_results[i] = iter_results
                        else:
                            all_iterations_results.append(iter_results)
                        
                        if len(iter_results) % checkpoint_interval == 0:
                            with open(temp_file, "w") as f:
                                json.dump(all_iterations_results, f, ensure_ascii=False, indent=2)
                            
                    except Exception as e:
                        print(f"⚠️ 问题 {case['id']} 评估失败: {e}")
                
                if i >= len(all_iterations_results):
                    all_iterations_results.append(iter_results)
                else:
                    all_iterations_results[i] = iter_results
                with open(temp_file, "w") as f:
                    json.dump(all_iterations_results, f, ensure_ascii=False, indent=2)
                
            with open(temp_file, "w") as f:
                json.dump(all_iterations_results, f, ensure_ascii=False, indent=2)
        finally:
            self._restore_retrieval_overrides(backup)
        return all_iterations_results

    def run(self):
        test_cases = self._load_question_set()
        if not test_cases:
            cases_file = Path(ROOT_DIR) / "experiments" / "quick_test_cases.json"
            if not cases_file.exists():
                print("❌ 未找到测试用例文件。")
                return
            with open(cases_file, "r", encoding="utf-8") as f:
                test_cases = json.load(f)

        # Lock sample size
        n = len(test_cases)
        config_version = settings.get("version", "unknown")
        config_id = settings.get("config_id", "manual")
        seed = settings.get("evaluation", {}).get("seed", 42)
        iters = settings.get("evaluation", {}).get("iterations", 1)

        summary_data = []
        run_state = self._load_run_state()
        completed_modes = run_state.get("completed_modes", {})

        for mode in ["vector_only", "bm25_only", "ensemble", "rrf"]:
            reusable_name = completed_modes.get(mode, {}).get("file")
            reusable = None
            if reusable_name:
                reusable = self._load_mode_result_if_compatible(
                    reusable_name, mode, n, iters, config_id, config_version
                )
            if reusable:
                all_scores = [c['scores'] for r in reusable["iterations"] for c in r]
                all_latencies = [c['latency'] for r in reusable["iterations"] for c in r]
                avg_faith = sum(s['faithfulness'] for s in all_scores) / len(all_scores)
                avg_rel = sum(s['relevance'] for s in all_scores) / len(all_scores)
                avg_lat = sum(all_latencies) / len(all_latencies)
                summary_data.append({
                    "mode": mode,
                    "avg_faith": avg_faith,
                    "avg_rel": avg_rel,
                    "avg_lat": avg_lat,
                    "file": reusable_name
                })
                print(f"⏭️ 跳过模式 {mode}，复用结果文件: {reusable_name}")
                continue

            iter_results = self.evaluate_mode(mode, test_cases, iterations=iters)
            if not iter_results:
                continue
            
            # Aggregate across iterations
            mode_results = {
                "metadata": {
                    "mode": mode,
                    "config_version": config_version,
                    "config_id": config_id,
                    "n": n,
                    "seed": seed,
                    "iterations": iters,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "iterations": iter_results
            }

            output_file = self.results_dir / f"evaluation_{mode}_{int(time.time())}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(mode_results, f, ensure_ascii=False, indent=2)
            mode_complete = self._is_mode_complete(iter_results, n, iters)
            temp_file = self.results_dir / f"temp_{mode}_checkpoint.json"
            if mode_complete:
                if temp_file.exists():
                    temp_file.unlink()
            else:
                print(f"⚠️ 模式 {mode} 未完整完成（预期 {n}×{iters}，实际不完整），保留 checkpoint 供续跑。")
            
            # Calculate averages for summary
            all_scores = [c['scores'] for r in iter_results for c in r]
            all_latencies = [c['latency'] for r in iter_results for c in r]
            avg_faith = sum(s['faithfulness'] for s in all_scores) / len(all_scores)
            avg_rel = sum(s['relevance'] for s in all_scores) / len(all_scores)
            avg_lat = sum(all_latencies) / len(all_latencies)
            
            summary_data.append({
                "mode": mode,
                "avg_faith": avg_faith,
                "avg_rel": avg_rel,
                "avg_lat": avg_lat,
                "file": output_file.name
            })
            if mode_complete:
                completed_modes[mode] = {
                    "file": output_file.name,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                run_state["completed_modes"] = completed_modes
                self._save_run_state(run_state)

        self._print_final_table(summary_data)
        
        # Log to Research Log
        summary_str = " | ".join([f"{d['mode']}: Faith={d['avg_faith']:.1f}" for d in summary_data])
        log_entry(
            entry_type="Result",
            description=f"意图引擎全量消融实验 (Exp A-D, n={n})",
            results=summary_str,
            note=f"Config: {config_id}, v{config_version}"
        )

    def _print_final_table(self, summary_data: List[Dict[str, Any]]):
        print("\n" + "="*80)
        print(f"📊 4-Mode Comparison Table (n={settings.get('evaluation',{}).get('sample_size', 0)})")
        print("-" * 80)
        print(f"{'Mode':<15} | {'Faithfulness':<12} | {'Relevance':<10} | {'Latency':<8}")
        print("-" * 80)
        for d in summary_data:
            print(f"{d['mode']:<15} | {d['avg_faith']:<12.2f} | {d['avg_rel']:<10.2f} | {d['avg_lat']:<8.2f}s")
        print("-" * 80)
        print("Note: Statistical significance tests (T-test) were NOT run in this batch.")
        print("="*80)

if __name__ == "__main__":
    evaluator = RAGEvaluator()
    evaluator.run()

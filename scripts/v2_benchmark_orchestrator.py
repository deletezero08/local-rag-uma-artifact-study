import argparse
import json
import os
import random
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import psutil
import torch

# [V2 SOTA] Monkey-patch transformers to disable memory warmup spike on 16GB Macs
import transformers.modeling_utils

transformers.modeling_utils.caching_allocator_warmup = lambda *args, **kwargs: None

from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.kv_compressor import AdaptiveKVCompressor
from src.turbo_quant import TurboQuantizer

MODEL_PATH = "/Users/delete/Desktop/rag_system_副本/multihoprag-merged"
INDEX_PATH = "/Users/delete/Desktop/rag_system_副本/models/vector_indices/turbo_index.json"
RETRIEVAL_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_OUTPUT = "/Users/delete/Desktop/rag_system_副本/results/evaluation/support_runtime/v2_performance_final.json"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


class V2BenchmarkOrchestrator:
    def __init__(self, use_v2: bool = True, seed: int = 42):
        self.use_v2 = use_v2
        self.seed = seed
        set_seed(seed)

        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.process = psutil.Process(os.getpid())
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        self.retrieval_model = SentenceTransformer(RETRIEVAL_MODEL)
        self.max_context_tokens = min(
            2048,
            int(getattr(self.tokenizer, "model_max_length", 2048) or 2048),
        )
        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token_id is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        print(f"📦 Loading model on {self.device} (V2={use_v2})...")
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            device_map=self.device,
            dtype=torch.float16 if self.device == "mps" else torch.float32,
            trust_remote_code=True,
        )
        self.model.eval()
        if self.model.config.pad_token_id is None:
            self.model.config.pad_token_id = self.tokenizer.pad_token_id or self.model.config.eos_token_id

        print("⚡ Loading TurboIndex...")
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            self.index_data = json.load(f)

        self.tq = TurboQuantizer(dim=self.index_data["dim"])
        self.tq.D = np.array(self.index_data["D"], dtype=np.float32)
        self.tq.W_qjl = np.array(self.index_data["W_qjl"], dtype=np.float32)
        self.encoded = {
            "codes": np.array(self.index_data["codes"], dtype=np.int8),
            "qjl": np.array(self.index_data["qjl"], dtype=np.int8),
            "params": self.index_data["params"],
            "scale_qjl": np.array(self.index_data["scale_qjl"], dtype=np.float32),
        }

        self.warmup()

    def warmup(self) -> None:
        warmup_prompt = "Hello"
        print("🔥 Running one-time warmup pass...")
        inputs = self.tokenizer(
            warmup_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=min(16, self.max_context_tokens),
        ).to(self.device)
        with torch.inference_mode():
            outputs = self.model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
                use_cache=True,
            )
            next_token = torch.argmax(outputs.logits[:, -1, :], dim=-1, keepdim=True)
            self.model(
                input_ids=next_token,
                attention_mask=torch.ones(
                    (1, inputs["input_ids"].shape[1] + 1),
                    dtype=inputs["input_ids"].dtype,
                    device=inputs["input_ids"].device,
                ),
                past_key_values=outputs.past_key_values,
                use_cache=True,
            )
        if self.device == "mps":
            torch.mps.synchronize()
        print("✅ Warmup complete")

    def current_rss_mb(self) -> float:
        return self.process.memory_info().rss / 1024 / 1024

    def retrieve(self, query: str, top_k: int = 5) -> List[str]:
        q_emb = self.retrieval_model.encode([query], normalize_embeddings=True)
        scores = self.tq.inner_product(q_emb, self.encoded)[0]
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [self.index_data["chunks"][i] for i in top_indices]

    def benchmark_retrieval(self, queries: List[str], top_k: int = 5) -> Dict[str, object]:
        latencies_ms: List[float] = []
        top_hits: List[List[str]] = []
        for query in queries:
            start = time.perf_counter()
            results = self.retrieve(query, top_k=top_k)
            latencies_ms.append((time.perf_counter() - start) * 1000.0)
            top_hits.append(results)

        return {
            "queries": queries,
            "top_k": top_k,
            "latency_ms": latencies_ms,
            "avg_latency_ms": float(np.mean(latencies_ms)) if latencies_ms else 0.0,
            "rss_mb": self.current_rss_mb(),
            "sample_hits": top_hits[:2],
        }

    def run_inference(self, prompt: str, max_new_tokens: int = 50) -> Dict[str, float]:
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_context_tokens,
        ).to(self.device)
        pad_token_id = self.model.config.pad_token_id
        input_ids = inputs["input_ids"]
        attention_mask = inputs.get("attention_mask")

        print(
            f"  ↳ Running prefill: input_tokens={input_ids.shape[1]}, max_new_tokens={max_new_tokens}"
        )
        start_time = time.perf_counter()
        generated = input_ids
        with torch.inference_mode():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                use_cache=True,
            )
        next_token = torch.argmax(outputs.logits[:, -1, :], dim=-1, keepdim=True)
        if self.device == "mps":
            torch.mps.synchronize()
        ttft = time.perf_counter() - start_time

        generated = torch.cat([generated, next_token], dim=1)
        past_key_values = outputs.past_key_values

        decode_start = time.perf_counter()
        print("  ↳ Running decode continuation")
        per_token_decode_ms: List[float] = []
        for step_idx in range(max(0, max_new_tokens - 1)):
            step_attention_mask = torch.ones_like(generated, device=generated.device)
            step_start = time.perf_counter()
            with torch.inference_mode():
                outputs = self.model(
                    input_ids=generated[:, -1:],
                    attention_mask=step_attention_mask,
                    past_key_values=past_key_values,
                    use_cache=True,
                )
            if self.device == "mps":
                torch.mps.synchronize()
            step_elapsed_ms = (time.perf_counter() - step_start) * 1000.0
            per_token_decode_ms.append(step_elapsed_ms)
            print(f"    · decode step {step_idx + 1}: {step_elapsed_ms:.1f} ms")
            past_key_values = outputs.past_key_values
            next_token = torch.argmax(outputs.logits[:, -1, :], dim=-1, keepdim=True)
            generated = torch.cat([generated, next_token], dim=1)
            if pad_token_id is not None and torch.all(next_token == pad_token_id):
                break
        if self.device == "mps":
            torch.mps.synchronize()
        decode_time = time.perf_counter() - decode_start
        total_time = ttft + decode_time
        tokens_gen = generated.shape[1] - inputs.input_ids.shape[1]
        tps = float((tokens_gen - 1) / max(decode_time, 1e-6)) if tokens_gen > 1 else 0.0

        return {
            "ttft": float(ttft),
            "tps": tps,
            "tokens": float(tokens_gen),
            "rss": float(self.current_rss_mb()),
            "total_time": float(total_time),
            "decode_step_ms": per_token_decode_ms,
        }

    def benchmark_scaling(self, lengths: List[int], max_new_tokens: int = 20) -> Dict[str, Dict[str, float]]:
        results: Dict[str, Dict[str, float]] = {}
        print("\n📈 Context Scaling Benchmark")
        print("-" * 68)
        print("Length | TTFT (ms) | TPS | RSS (MB) | Total Time (s)")
        print("-" * 68)

        for length in lengths:
            context = "This is a fact about RAG optimization. " * max(1, length // 8)
            prompt = context + "\nQuestion: What is the main bottleneck? Answer:"
            try:
                print(f"⏳ Scaling case start: target_context={length}")
                metrics = self.run_inference(prompt, max_new_tokens=max_new_tokens)
                results[str(length)] = metrics
                print(
                    f"{length:<6} | {metrics['ttft']*1000:>9.1f} | {metrics['tps']:>4.1f} | "
                    f"{metrics['rss']:>8.1f} | {metrics['total_time']:>13.2f}"
                )
            except Exception as exc:  # noqa: BLE001
                results[str(length)] = {"status": "failed", "error": str(exc)}
                print(f"{length:<6} | FAILED: {exc}")

        return results

    def benchmark_concurrency(
        self,
        n_list: List[int],
        prompt: str,
        max_new_tokens: int = 30,
    ) -> Dict[str, Dict[str, float]]:
        print("\n🔥 Concurrency Benchmark")
        results: Dict[str, Dict[str, float]] = {}

        for n in n_list:
            print(f"⏳ Concurrency case start: N={n}")
            threads: List[threading.Thread] = []
            metrics_batch: List[Dict[str, float]] = []
            errors: List[str] = []
            lock = threading.Lock()

            def worker() -> None:
                try:
                    metrics = self.run_inference(prompt, max_new_tokens=max_new_tokens)
                    with lock:
                        metrics_batch.append(metrics)
                except Exception as exc:  # noqa: BLE001
                    with lock:
                        errors.append(str(exc))

            start = time.perf_counter()
            for _ in range(n):
                thread = threading.Thread(target=worker, daemon=True)
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()

            duration = time.perf_counter() - start
            total_tokens = sum(m["tokens"] for m in metrics_batch)
            system_tps = float(total_tokens / max(duration, 1e-6))
            avg_ttft = float(sum(m["ttft"] for m in metrics_batch) / len(metrics_batch)) if metrics_batch else 0.0

            results[str(n)] = {
                "status": "ok" if not errors else "partial_failure",
                "system_tps": system_tps,
                "avg_ttft": avg_ttft,
                "duration": float(duration),
                "completed_workers": float(len(metrics_batch)),
                "error_count": float(len(errors)),
            }
            if errors:
                results[str(n)]["errors"] = errors
            print(
                f"N={n} | Completed: {len(metrics_batch)} | Errors: {len(errors)} | "
                f"Sys TPS: {system_tps:.2f} | Avg TTFT: {avg_ttft:.2f}s"
            )

        return results

    def build_metadata(self, mode: str) -> Dict[str, object]:
        return {
            "mode": mode,
            "timestamp": time.time(),
            "seed": self.seed,
            "model_path": MODEL_PATH,
            "index_path": INDEX_PATH,
            "device": self.device,
            "use_v2": self.use_v2,
        }

    def summarize(self, retrieval: Dict[str, object], scaling: Dict[str, Dict[str, float]], concurrency: Dict[str, Dict[str, float]]) -> Dict[str, object]:
        succeeded_scaling = [v for v in scaling.values() if isinstance(v, dict) and v.get("status") != "failed"]
        scaling_points = len(succeeded_scaling)
        peak_rss = max((v.get("rss", 0.0) for v in succeeded_scaling), default=0.0)
        concurrency_entries = [
            v for v in concurrency.values()
            if isinstance(v, dict)
        ]
        best_tps = max((v.get("system_tps", 0.0) for v in concurrency_entries), default=0.0)
        return {
            "retrieval_avg_latency_ms": retrieval.get("avg_latency_ms", 0.0),
            "successful_scaling_points": scaling_points,
            "peak_rss_mb": peak_rss,
            "best_system_tps": best_tps,
        }

    def run(self, mode: str, output_path: str) -> Dict[str, object]:
        retrieval_queries = [
            "What is the core bottleneck in local RAG systems?",
            "Explain TurboQuant retrieval and KV compression.",
        ]
        test_prompt = "Explain the difference between FP16 and INT8 quantization in the context of LLM inference on modern GPUs."

        if mode == "smoke":
            lengths = [16]
            concurrency_levels = []
            max_new_tokens = 3
        else:
            lengths = [1024, 2048, 4096, 8192]
            concurrency_levels = [1, 2, 4]
            max_new_tokens = 20

        retrieval = self.benchmark_retrieval(retrieval_queries, top_k=5)
        scaling = self.benchmark_scaling(lengths, max_new_tokens=max_new_tokens)
        if concurrency_levels:
            concurrency = self.benchmark_concurrency(
                concurrency_levels,
                test_prompt,
                max_new_tokens=30 if mode == "full" else 12,
            )
        else:
            concurrency = {
                "status": "skipped",
                "reason": "Smoke mode skips concurrency to isolate single-request generation latency.",
            }

        compressor_events: List[Dict[str, float]] = []
        for module in self.model.modules():
            compressor = getattr(module, "kv_compressor", None)
            if isinstance(compressor, AdaptiveKVCompressor):
                compressor_events.extend(compressor.get_events())

        results = {
            "metadata": self.build_metadata(mode),
            "retrieval": retrieval,
            "scaling": scaling,
            "concurrency": concurrency,
            "kv_compression_events": compressor_events,
            "summary": self.summarize(retrieval, scaling, concurrency),
        }

        ensure_parent(output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Results saved to {output_path}")
        return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V2 benchmark orchestrator for Battle 4.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--smoke", action="store_true", help="Run a lightweight smoke benchmark.")
    group.add_argument("--full", action="store_true", help="Run the full benchmark suite.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Path to the benchmark JSON output.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    mode = "full" if args.full else "smoke"
    orchestrator = V2BenchmarkOrchestrator(use_v2=True, seed=args.seed)
    orchestrator.run(mode=mode, output_path=args.output)

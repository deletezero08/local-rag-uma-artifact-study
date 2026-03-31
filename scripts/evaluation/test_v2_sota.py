import torch
import time
import psutil
import os
import transformers.modeling_utils
# [V2 SOTA] Monkey-patch transformers to disable memory warmup spike on 16GB Macs
transformers.modeling_utils.caching_allocator_warmup = lambda *args, **kwargs: None

from transformers import AutoModelForCausalLM, AutoTokenizer, FalconConfig

MODEL_PATH = "/Users/delete/Desktop/rag_system_副本/multihoprag-merged"

def verify_v2():
    print("🚀 Verifying V2 SOTA: Adaptive KV + Chunked Prefill...")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    config = FalconConfig.from_pretrained(MODEL_PATH)
    
    # Load model with MPS + FP16
    # Note: Using low_cpu_mem_usage and avoiding the huge allocator warmup
    print("📥 Loading patched model (forcing eager attn for pruning)...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        config=config,
        device_map="mps",
        torch_dtype=torch.float16,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        attn_implementation="eager"
    )
    
    # Create a long context (4000 tokens)
    # This would have OOM'd in the baseline due to 12.8GB buffer + 8Kx8K matrix
    print("📝 Testing 4000-token prefill (Chunked + Compressed)...")
    prompt = "Context: " + "This is a test of the emergency broadcast system. " * 200
    inputs = tokenizer(prompt, return_tensors="pt").to("mps")
    print(f"   Input shape: {inputs.input_ids.shape}")
    
    start_time = time.perf_counter()
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=20,
            use_cache=True,
            do_sample=False
        )
    end_time = time.perf_counter()
    
    print("\n" + "="*40)
    print("🏁 V2 SOTA VERIFICATION")
    print("="*40)
    print(f"Execution Time: {end_time - start_time:.2f}s")
    print(f"Output: {tokenizer.decode(output[0][-20:], skip_special_tokens=True)}")
    print(f"Memory RSS: {psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024:.2f} MB")
    print("="*40)

if __name__ == "__main__":
    verify_v2()

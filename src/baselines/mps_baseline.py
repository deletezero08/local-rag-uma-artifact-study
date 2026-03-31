import torch
import time
import psutil
import os
import threading
from transformers import AutoModelForCausalLM, AutoTokenizer, FalconConfig

MODEL_PATH = "/Users/delete/Desktop/rag_system_副本/multihoprag-merged"

class MemoryMonitor(threading.Thread):
    def __init__(self, interval=0.1):
        super().__init__()
        self.interval = interval
        self.max_rss = 0
        self.running = True
        self.daemon = True

    def run(self):
        process = psutil.Process(os.getpid())
        while self.running:
            rss = process.memory_info().rss / (1024 * 1024)  # MB
            if rss > self.max_rss:
                self.max_rss = rss
            time.sleep(self.interval)

    def stop(self):
        self.running = False

def run_baseline():
    print(f"🚀 Loading Falcon-7B from {MODEL_PATH} on MPS...")
    
    # Start memory monitoring
    monitor = MemoryMonitor()
    monitor.start()

    load_start = time.perf_counter()
    
    # Config and Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    config = FalconConfig.from_pretrained(MODEL_PATH)
    
    # Force MPS + FP16
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        config=config,
        device_map="mps",
        torch_dtype=torch.float16,
        trust_remote_code=True
    )
    
    load_end = time.perf_counter()
    print(f"✅ Model loaded in {load_end - load_start:.2f}s")
    print(f"📊 Initial RSS: {psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024:.2f} MB")

    # Warm-up
    prompt = "Artificial Intelligence is a field of computer science that"
    inputs = tokenizer(prompt, return_tensors="pt").to("mps")
    print("🔥 Warming up...")
    for _ in range(3):
        _ = model.generate(**inputs, max_new_tokens=5, do_sample=False)

    # Throughput Measurement
    print("📏 Measuring Throughput (50 tokens)...")
    gen_start = time.perf_counter()
    output = model.generate(
        **inputs,
        max_new_tokens=50,
        do_sample=False,
        use_cache=True
    )
    gen_end = time.perf_counter()
    
    total_tokens = output.shape[1] - inputs.input_ids.shape[1]
    duration = gen_end - gen_start
    tps = total_tokens / duration
    
    print("\n" + "="*40)
    print("🏁 BASELINE RESULTS (V1 Native MPS)")
    print("="*40)
    print(f"Tokens Generated:  {total_tokens}")
    print(f"Total Duration:    {duration:.2f} s")
    print(f"Throughput (TPS):  {tps:.2f} tokens/s")
    print(f"Peak Memory (RSS): {monitor.max_rss:.2f} MB")
    print("="*40)

    # Test Long Context (OOM Trigger Check)
    print("\n⚠️  Testing Long Context (2048 tokens native limit)...")
    long_prompt = "Q: " + "repeat after me " * 1024
    long_inputs = tokenizer(long_prompt, return_tensors="pt", truncation=True, max_length=2048).to("mps")
    
    try:
        _ = model.generate(**long_inputs, max_new_tokens=10)
        print("✅ 2K Context PASSED (Uncompressed)")
    except Exception as e:
        print(f"❌ 2K Context FAILED: {str(e)}")

    monitor.stop()

if __name__ == "__main__":
    run_baseline()

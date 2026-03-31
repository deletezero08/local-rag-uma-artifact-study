import numpy as np
import time
import argparse
import sys

def simulate_pipeline(mode, duration=60):
    print(f"\n=== Starting System Virtual Memory Simulation: {mode.upper()} ===")
    
    allocations = []
    start = time.time()
    
    if mode == "mps":
        # Simulate loading huge FP16/FP32 matrices across Apple Silicon
        # Mac mini M4 has 16GB. We deliberately touch ~15GB of raw uncompressible dense float data 
        # (plus OS overhead) to violently trigger the limits of the unified memory architecture.
        memory_chunks = 38  # 38 * 400MB = 15.2GB (Leaves ~800MB for OS). Highly unstable.
        chunk_size = (10000, 10000) # 100M float32 = 400MB
    elif mode == "sota":
        # Simulate local compressed GGUF + KVCache optimized structures
        # Total footprint around 6-8GB. Perfectly cache-friendly.
        memory_chunks = 18  # 18 * 400MB = 7.2GB
        chunk_size = (10000, 10000)
    else:
        print("Unknown mode")
        return
        
    print(f"[{time.time()-start:.1f}s] Allocating {memory_chunks * 400} MB internal structure...")
    
    try:
        # Phase 1: Model Loading / Memory Prefill
        for i in range(memory_chunks):
            # Float32 arrays with random data prevents macOS APFS compressed memory from cheating
            chunk = np.random.rand(*chunk_size).astype(np.float32)
            allocations.append(chunk)
            time.sleep(0.3) # Simulate layer-by-layer parameter load latency
            sys.stdout.write(f"\rLoading chunk {i+1}/{memory_chunks}...")
            sys.stdout.flush()
            
        print(f"\n[{time.time()-start:.1f}s] Loading complete. Beginning decode phase (cache cycling)...")
        
        # Phase 2: Generation Loop (Cycling memory, forcing Pageouts/Swapouts)
        while time.time() - start < duration:
            # We deliberately read/write across the generated tensors horizontally and vertically 
            # to trigger continuous hardware page faults in MPS mode, but safety in SOTA mode.
            for i in range(0, len(allocations), max(1, len(allocations)//3)):
                allocations[i][50:5000, 50:5000] *= 1.01
            time.sleep(0.5) # Simulate token generation ops
            
    except MemoryError:
        print(f"\n[{time.time()-start:.1f}s] Hit hard memory wall! Thrashing imminent.")
        while time.time() - start < duration:
            try:
                # Keep touching existing memory to force continuous severe pageouts
                for i in range(len(allocations)):
                    allocations[i][::400, ::400] += 0.01
                time.sleep(1.0)
            except Exception:
                time.sleep(1.0)

    print(f"\n[{time.time()-start:.1f}s] Simulation complete execution.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['mps', 'sota'], required=True)
    parser.add_argument('--duration', type=int, default=60)
    args = parser.parse_args()
    simulate_pipeline(args.mode, args.duration)

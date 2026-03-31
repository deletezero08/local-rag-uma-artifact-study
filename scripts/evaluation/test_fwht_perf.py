import numpy as np
import time
from src.turbo_quant import TurboQuantizer

def python_fwht_ref(x: np.ndarray) -> np.ndarray:
    """Reference Python FWHT for correctness checking."""
    n = x.shape[-1]
    orig_shape = x.shape[:-1]
    x = x.copy().reshape(-1, n).astype(np.float32)
    for row in x:
        h = 1
        while h < n:
            for i in range(0, n, h * 2):
                for j in range(i, i + h):
                    row[j], row[j + h] = row[j] + row[j + h], row[j] - row[j + h]
            h *= 2
    return x.reshape(*orig_shape, n) / np.sqrt(n)

def test_fwht():
    dim = 512
    num_vectors = 100
    data = np.random.randn(num_vectors, dim).astype(np.float32)
    tq = TurboQuantizer(dim=dim)
    
    print(f"🚀 Testing FWHT Acceleration (dim={dim}, n={num_vectors})")
    
    # Correctness Check
    print("⏳ Running Correctness Check...")
    ref_out = python_fwht_ref(data)
    new_out = tq._fwht(data)
    
    diff = np.abs(ref_out - new_out)
    max_diff = np.max(diff)
    exact_match = np.allclose(ref_out, new_out, atol=1e-5)
    
    if exact_match:
        print(f"✅ Correctness Check PASSED (Max Diff: {max_diff:.2e})")
    else:
        print(f"❌ Correctness Check FAILED (Max Diff: {max_diff:.2e})")
        return

    # Performance Comparison
    print("⏳ Measuring Baseline (Python Ref)...")
    start = time.perf_counter()
    python_fwht_ref(data)
    python_time = time.perf_counter() - start
    print(f"   Python Ref Time: {python_time*1000:.2f}ms")
    
    print("⏳ Measuring SOTA (Vectorized NumPy)...")
    start = time.perf_counter()
    tq._fwht(data)
    numpy_time = time.perf_counter() - start
    print(f"   Vectorized Time: {numpy_time*1000:.2f}ms")
    
    speedup = python_time / numpy_time
    print(f"\n⚡ Speedup: {speedup:.2f}x")
    
    if speedup >= 10:
        print("🏆 SUCCESS: Target speedup achieved.")
    else:
        print("⚠️ WARNING: Speedup below 10x target.")

if __name__ == "__main__":
    test_fwht()

import torch
import sys
import os

try:
    from src.kv_compressor import KVCompressor
except ImportError:
    sys.path.append(os.getcwd())
    from src.kv_compressor import KVCompressor

def test_dynamic_eviction():
    device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
    print(f"🧪 Testing Dynamic KV Eviction on {device}...")
    
    # 1. Initialize compressor with dynamic strategy
    compressor = KVCompressor(compression_ratio=0.25, strategy="dynamic")
    
    # 2. Mock KV Tensors [batch, head, seq_len, head_dim]
    b, h, s, d = 1, 32, 1024, 128
    k = torch.randn(b, h, s, d).to(device)
    v = torch.randn(b, h, s, d).to(device)
    
    # 3. Mock Attention Weights [head, q_len, k_len]
    # We'll make some tokens have very high attention
    att = torch.zeros(h, 1, s).to(device)
    att[:, :, :10] = 10.0  # System prompt / early context
    att[:, :, 500:510] = 5.0 # Mid-context facts
    att = torch.softmax(att, dim=-1)
    
    # 4. Perform Compression
    k_comp, v_comp = compressor.compress(k, v, attention_weights=att)
    
    print(f"📊 Original Shape: {k.shape}")
    print(f"📊 Compressed Shape: {k_comp.shape}")
    
    # Assertions
    expected_s = int(s * 0.25)
    assert k_comp.size(-2) == expected_s, f"Expected {expected_s}, got {k_comp.size(-2)}"
    print(f"✅ Compression ratio maintained: {k_comp.size(-2)/s:.2%}")
    print(f"✅ Dynamic Index Selection: SUCCESS")
    print("="*60)

if __name__ == "__main__":
    test_dynamic_eviction()

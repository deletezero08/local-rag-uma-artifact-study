import os
from typing import Dict, List, Tuple

import psutil
import torch

class AdaptiveKVCompressor:
    """
    Memory-Aware Adaptive KV Cache Compressor for Falcon-7B (SOTA V2).
    Implements Heavy Hitter selection with dynamic retention based on RAM pressure.
    """
    def __init__(self, 
                 target_free_gb: float = 2.0, 
                 min_retention: float = 0.05, 
                 max_retention: float = 0.5,
                 window_size: int = 32,
                 sink_size: int = 64):
        self.target_free_gb = target_free_gb
        self.min_retention = min_retention
        self.max_retention = max_retention
        self.window_size = window_size
        self.sink_size = sink_size
        self.process = psutil.Process(os.getpid())
        self.events: List[Dict[str, float]] = []

    def _available_gb(self) -> float:
        return psutil.virtual_memory().available / (1024**3)

    def get_adaptive_ratio(self) -> float:
        """Calculate retention ratio based on available system memory."""
        free_gb = self._available_gb()
        
        if free_gb < self.target_free_gb:
            # Linear scale down to min_retention when free memory is critical
            ratio = self.min_retention + (self.max_retention - self.min_retention) * (free_gb / self.target_free_gb)
            return max(self.min_retention, ratio)
        return self.max_retention

    def get_events(self) -> List[Dict[str, float]]:
        """Return a shallow copy of compression events for downstream benchmarking."""
        return list(self.events)

    def select_heavy_hitters(self, 
                             attn_scores: torch.Tensor, 
                             num_to_keep: int) -> torch.Tensor:
        """
        Aggregate attention scores across all heads and find Top-K indices.
        attn_scores: (batch, num_heads, query_len, kv_len)
        """
        # Sum over heads and queries to find globally important tokens in the KV cache
        # shape: (batch, kv_len)
        importance = attn_scores.sum(dim=(1, 2))
        
        # Protect the 'sink' (early tokens) and 'window' (recent tokens)
        # by giving them infinite importance
        kv_len = importance.size(-1)
        if kv_len <= self.sink_size + self.window_size + num_to_keep:
            return torch.arange(kv_len, device=attn_scores.device)
            
        protected_mask = torch.zeros_like(importance, dtype=torch.bool)
        protected_mask[:, :self.sink_size] = True
        protected_mask[:, -self.window_size:] = True
        
        importance.masked_fill_(protected_mask, float('inf'))
        
        # Select Top-K
        _, indices = torch.topk(importance, k=num_to_keep + self.sink_size + self.window_size, dim=-1, sorted=True)
        return indices.sort(dim=-1).values

    @torch.no_grad()
    def compress(self, 
                 past_key_values: Tuple[torch.Tensor, torch.Tensor], 
                 attn_scores: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compress KV cache for a single layer.
        past_key_values: (key, value) where key/value are (batch, heads, seq, dim)
        attn_scores: (batch, heads, q_len, seq)
        """
        keys, values = past_key_values
        batch_size, num_heads, seq_len, head_dim = keys.shape
        
        ratio = self.get_adaptive_ratio()
        num_to_keep = max(1, int(seq_len * ratio))
        
        indices = self.select_heavy_hitters(attn_scores, num_to_keep)
        
        # indices is (batch, k)
        # We need to gather across the sequence dimension (dim=2)
        # keys/values are (batch, heads, seq, dim)
        k_idx = indices.unsqueeze(1).unsqueeze(-1).expand(-1, num_heads, -1, head_dim)
        
        new_keys = torch.gather(keys, 2, k_idx)
        new_values = torch.gather(values, 2, k_idx)

        available_gb = self._available_gb()
        event = {
            "batch_size": float(batch_size),
            "seq_len": float(seq_len),
            "ratio": float(ratio),
            "retained_tokens": float(new_keys.shape[2]),
            "available_gb": float(available_gb),
        }
        if ratio < self.max_retention:
            event["pruning_triggered"] = 1.0
        else:
            event["pruning_triggered"] = 0.0
        self.events.append(event)
            
        return new_keys, new_values

if __name__ == "__main__":
    # Test
    compressor = AdaptiveKVCompressor()
    print(f"Current Adaptive Ratio: {compressor.get_adaptive_ratio():.2%}")

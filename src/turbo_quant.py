import numpy as np
import os
import json
from typing import Tuple, List, Optional

class TurboQuantizer:
    """
    SOTA TurboQuant implementation (arXiv:2504.19874).
    Upgraded for "Absolute Quality Neutrality" using Outlier-Aware Quantization.
    """
    def __init__(self, dim: int = 384, bits: float = 3.5, outlier_indices_path: Optional[str] = None):
        self.dim = dim
        self.bits = bits
        
        # 1. Random Orthogonal Rotation Setup
        self.D = np.random.choice([-1, 1], size=dim).astype(np.float32)
        
        # 2. Outlier Channel Setup (Heavy Hitters)
        self.outlier_indices = []
        if outlier_indices_path and os.path.exists(outlier_indices_path):
            with open(outlier_indices_path, "r") as f:
                data = json.load(f)
                # Ensure indices are within current dimension
                self.outlier_indices = [idx for idx in data["outlier_indices"] if idx < self.dim]
        
        # 3. 1-bit QJL Residual Setup
        # We use a 64-bit projection for the residual correction
        self.W_qjl = np.random.randn(dim, 64).astype(np.float32)

    def _fwht(self, x: np.ndarray) -> np.ndarray:
        """
        Fast Walsh-Hadamard Transform (Vectorized NumPy Optimization).
        Computational Complexity: O(d log d)
        """
        n = x.shape[-1]
        orig_shape = x.shape[:-1]
        x = x.copy().reshape(-1, n).astype(np.float32)
        h = 1
        while h < n:
            x = x.reshape(-1, n // (2 * h), 2, h)
            a = x[:, :, 0, :]
            b = x[:, :, 1, :]
            x = np.stack([a + b, a - b], axis=2).reshape(-1, n)
            h *= 2
        return x.reshape(*orig_shape, n) / np.sqrt(n)

    def _quantize_outlier_aware(self, v: np.ndarray) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        Stage 1: Outlier-Aware Scalar Quantization.
        Allocates more bits to Heavy Hitter (Outlier) channels.
        Example (2.5-bit target): 3-bit for 32 outliers, 2-bit for the rest.
        """
        v_q = np.zeros_like(v)
        codes = np.zeros_like(v, dtype=np.int8)
        params = {}

        # 1. Handle Outliers (High Precision)
        if self.outlier_indices:
            outlier_mask = np.zeros(self.dim, dtype=bool)
            outlier_mask[self.outlier_indices] = True
            
            # Outliers get 3-bit (8 levels) or 4-bit (16 levels) depending on target
            outlier_levels = 8 if self.bits < 3.0 else 16
            v_out = v[..., outlier_mask]
            
            v_min, v_max = v_out.min(), v_out.max()
            step = (v_max - v_min) / (outlier_levels - 1)
            q = np.round((v_out - v_min) / (step + 1e-9)).astype(np.int8)
            v_q[..., outlier_mask] = q.astype(np.float32) * step + v_min
            codes[..., outlier_mask] = q
            params["outlier"] = (v_min, step)
            
            # Non-Outliers get 2-bit (4 levels) or 3-bit (8 levels)
            base_mask = ~outlier_mask
            base_levels = 4 if self.bits < 3.0 else 8
            v_base = v[..., base_mask]
            
            v_min_b, v_max_b = v_base.min(), v_base.max()
            step_b = (v_max_b - v_min_b) / (base_levels - 1)
            q_b = np.round((v_base - v_min_b) / (step_b + 1e-9)).astype(np.int8)
            v_q[..., base_mask] = q_b.astype(np.float32) * step_b + v_min_b
            codes[..., base_mask] = q_b
            params["base"] = (v_min_b, step_b)
        else:
            # Fallback to uniform if no outlier map exists
            levels = int(2**self.bits)
            v_min, v_max = v.min(), v.max()
            step = (v_max - v_min) / (levels - 1)
            q = np.round((v - v_min) / (step + 1e-9)).astype(np.int8)
            v_q = q.astype(np.float32) * step + v_min
            codes = q
            params["uniform"] = (v_min, step)
            
        return codes, v_q, params

    def encode(self, vectors: np.ndarray) -> dict:
        """
        Encode high-dimensional vectors to SOTA TurboQuant format.
        """
        # 0. L2 Normalization (Essential for mathematical consistency)
        norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
        normed = vectors / (norms + 1e-9)
        
        # 1. Random Sign Flip + Optimized FWHT
        rotated = self._fwht(normed * self.D)
        
        # 2. Stage 1: Outlier-Aware Quantization
        codes, v_q, params = self._quantize_outlier_aware(rotated)
        
        # 3. Stage 2: 1-bit QJL on the Residual (Unbiasedness Anchor)
        residual = rotated - v_q
        scale_qjl = np.mean(np.abs(residual), axis=-1, keepdims=True)
        qjl_bits = (np.dot(residual, self.W_qjl) > 0).astype(np.int8)
        
        return {
            "codes": codes,
            "qjl": qjl_bits,
            "params": params,
            "scale_qjl": scale_qjl,
            "norms": norms # Store for dequantization scaling
        }

    def inner_product(self, query_fp32: np.ndarray, encoded: dict) -> np.ndarray:
        """
        Asymmetric Distance Computation (ADC).
        """
        # 1. Normalize and Rotate Query
        q_norm = np.linalg.norm(query_fp32, axis=-1, keepdims=True)
        q_normed = query_fp32 / (q_norm + 1e-9)
        rotated_query = self._fwht(q_normed * self.D) # (M, D)
        
        # 2. Decode Stage 1 (Outlier-Aware)
        v_q = np.zeros((encoded["codes"].shape[0], self.dim), dtype=np.float32)
        params = encoded["params"]
        codes = encoded["codes"]
        
        if "uniform" in params:
            v_min, step = params["uniform"]
            v_q = codes.astype(np.float32) * step + v_min
        else:
            outlier_mask = np.zeros(self.dim, dtype=bool)
            outlier_mask[self.outlier_indices] = True
            
            v_min_o, step_o = params["outlier"]
            v_q[..., outlier_mask] = codes[..., outlier_mask].astype(np.float32) * step_o + v_min_o
            
            v_min_b, step_b = params["base"]
            v_q[..., ~outlier_mask] = codes[..., ~outlier_mask].astype(np.float32) * step_b + v_min_b
            
        ip1 = np.dot(rotated_query, v_q.T) # (M, N)
        
        # 3. Decode Stage 2 (QJL correction)
        proj_query = np.dot(rotated_query, self.W_qjl) # (M, 64)
        qjl_corr = np.dot(encoded["qjl"] * 2.0 - 1.0, proj_query.T).T # (M, N)
        qjl_corr = qjl_corr * encoded["scale_qjl"].T / np.sqrt(64)
        
        # 4. Final Scale by Vector Norms
        return (ip1 + qjl_corr) * encoded["norms"].T * q_norm

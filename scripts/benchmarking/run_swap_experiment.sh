#!/bin/bash
set -e
VENV_PYTHON="/Users/delete/Desktop/rag_system_副本/.venv313/bin/python3"

# Real UMA Hardware Virtual Memory Saturation Experiment
# Designed to capture authentic OS pageout activity

echo "====== [Experiment 1/2] Unoptimized Falcon-7B MPS Simulation ======"
echo "Starting swap profiler..."
$VENV_PYTHON scripts/benchmarking/profile_swap.py --out results/hardware/swap_mps_real.csv &
PROFILER_PID=$!

echo "Simulating dense FP16 macOS memory pressure (Allocating ~15GB)..."
$VENV_PYTHON scripts/benchmarking/experiment_memory_thrash.py --mode mps --duration 40

echo "Stopping profiler..."
kill -SIGINT $PROFILER_PID || true
sleep 3

echo "Allowing UMA hardware 5s cooldown..."
sleep 5

echo "====== [Experiment 2/2] Optimized GGUF Pipeline Simulation ======"
echo "Starting swap profiler..."
$VENV_PYTHON scripts/benchmarking/profile_swap.py --out results/hardware/swap_sota_real.csv &
PROFILER_PID=$!

echo "Simulating compressed INT4 memory footprint (Allocating ~7GB)..."
$VENV_PYTHON scripts/benchmarking/experiment_memory_thrash.py --mode sota --duration 40

echo "Stopping profiler..."
kill -SIGINT $PROFILER_PID || true
sleep 3

echo "Experiments completed! Generating Figure 3 natively..."
$VENV_PYTHON journal_paper_ccpe/generate_plots.py
echo "Done!"

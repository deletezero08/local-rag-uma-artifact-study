# Hardware Telemetry

This folder contains low-level runtime telemetry captured during constrained-hardware experiments.

## Current Files

- `concurrency_vmstat_trace.csv`
  - aggregated vm_stat trace for the paper-track concurrency study
- `concurrency_vmstat/`
  - per-round vm_stat traces for `full_context` and `optimized_path`

## Additional Telemetry

- `bandwidth_mps_real.csv`
- `swap_mps_real.csv`
- `swap_sota_real.csv`

These support the memory-saturation and paging interpretation used in the manuscript.

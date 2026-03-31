#!/usr/bin/env python3
"""
Hardware Swap Thrashing Monitor (Apple Silicon UMA)
Captures real-time Virtual Memory memory pressure (Pageouts & Swapouts).
No macOS root permissions required.
"""
import subprocess
import time
import argparse
import sys
import csv
import os

def run_vmstat(output_file, duration=None):
    cmd = ["vm_stat", "1"]
    print(f"📡 Starting physical memory swap profiling to {output_file}...")
    print("✅ No sudo required! Safe OS-level virtual memory probe activated.")
    
    start_time = time.time()
    
    # vm_stat gracefully flushes line by line over subprocess pipes on MacOS.
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)

    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Time_s', 'Pageouts_per_sec', 'Swapouts_per_sec'])
        
        headers = []
        try:
            skip_next = True
            for line in process.stdout:
                line = line.strip()
                if not line or "Mach Virtual Memory" in line:
                    skip_next = True
                    continue
                    
                tokens = line.split()
                if "free" in tokens and "pageout" in tokens:
                    headers = tokens
                    skip_next = True
                    continue
                
                if headers and len(tokens) == len(headers):
                    try:
                        if skip_next:
                            skip_next = False
                            continue
                        idx_pageout = headers.index("pageout")
                        idx_swapout = headers.index("swapouts")
                        
                        po = int(tokens[idx_pageout])
                        so = int(tokens[idx_swapout])
                        
                        elapsed = time.time() - start_time
                        if duration and elapsed > duration:
                            break
                            
                        # Logging the absolute pageouts + swapouts per second threshold
                        writer.writerow([round(elapsed, 2), po, so])
                        csvfile.flush()
                        
                        total_thrash = po + so
                        # Terminal status bar (Color coded based on thrash danger)
                        status_color = ""
                        if total_thrash > 1000:
                            status_color = "🔴 DANGER THRASING "
                        elif total_thrash > 100:
                            status_color = "🟡 WARNING PRESSURE "
                        else:
                            status_color = "🟢 STABLE "
                            
                        print(f"\r[🔥 {elapsed:04.1f}s] {status_color} Paging Activity (SSD IO): {total_thrash:05d} ops/sec", end='')
                    except ValueError:
                        pass
                        
        except KeyboardInterrupt:
            print("\n🛑 Profiling manually halted by user.")
        finally:
            process.terminate()
            print(f"\n💾 Saved physical swap trace to: {output_file}")
            print("Ready to be parsed by `generate_plots.py`.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Apple Silicon UMA Swap Profiler")
    parser.add_argument('--out', type=str, required=True, help="Output CSV path (e.g. ../results/hardware/swap_mps_real.csv)")
    parser.add_argument('--duration', type=int, default=0, help="Stop after N seconds. 0 = infinite (Ctrl+C to stop).")
    args = parser.parse_args()
    
    if args.duration == 0:
        run_vmstat(args.out)
    else:
        run_vmstat(args.out, args.duration)

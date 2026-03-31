#!/usr/bin/env python3
"""
Hardware Memory Bandwidth Parser
Extracts strictly the physical DCS (DRAM) read/write aggregates from a raw Apple Silicon powermetrics dump.
"""
import re
import csv
import argparse

def parse_trace(input_file, output_csv):
    print(f"📖 Parsing raw physical trace from {input_file} ...")
    
    with open(output_file, 'w', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['Time_s', 'DRAM_GBps'])
        
        elapsed_time = 0.0
        sample_interval = 0.5  # powermetrics -i 500 means 500ms
        
        current_block_total = 0.0
        block_has_data = False
        
        try:
            with open(input_file, 'r') as f_in:
                for line in f_in:
                    # Powermetrics output is chunked into sample boundaries.
                    # We detect the boundary of a new sample block to increment time.
                    if "Sampled system activity" in line or "***" in line:
                        # Flush the previous accumulated block
                        if block_has_data:
                            writer.writerow([round(elapsed_time, 2), round(current_block_total, 2)])
                            elapsed_time += sample_interval
                            current_block_total = 0.0
                            block_has_data = False
                    
                    # Target M-Series RAM limits
                    if "DCS" in line and "GB/s" in line:
                        parts = re.findall(r'([0-9.]+)\s*GB/s', line)
                        if parts:
                            current_block_total += sum(float(p) for p in parts)
                            block_has_data = True

            # End of file flush
            if block_has_data:
                writer.writerow([round(elapsed_time, 2), round(current_block_total, 2)])
                
        except Exception as e:
            print(f"❌ Error parsing logs: {e}")
            return
            
    print(f"✅ Parser successfully extracted pure bandwidth timeline to {output_csv}!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True, help="Raw powermetrics txt dump")
    parser.add_argument('--output', type=str, required=True, help="Parsed CSV path")
    args = parser.parse_args()
    parse_trace(args.input, args.output)

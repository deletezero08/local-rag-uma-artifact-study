#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT_DIR / "results" / "hardware" / "concurrency_vmstat"
DEFAULT_OUTPUT = ROOT_DIR / "results" / "hardware" / "concurrency_vmstat_trace.csv"
PATTERN = re.compile(r"(?P<mode>.+)_n(?P<concurrency>\d+)_r(?P<round>\d+)\.csv$")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate per-round vm_stat traces into a single CSV.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT))
    parser.add_argument("--out-file", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "mode",
        "concurrency",
        "round",
        "sample_index",
        "Timestamp",
        "Pageouts_per_sec",
        "Swapouts_per_sec",
        "Total_ops_per_sec",
    ]
    rows = []
    for csv_path in sorted(input_dir.glob("*.csv")):
        match = PATTERN.match(csv_path.name)
        if not match:
            continue
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for sample_index, row in enumerate(reader, start=1):
                try:
                    pageouts = float(row.get("Pageouts_per_sec", 0))
                    swapouts = float(row.get("Swapouts_per_sec", 0))
                except Exception:
                    continue
                rows.append(
                    {
                        "mode": match.group("mode"),
                        "concurrency": int(match.group("concurrency")),
                        "round": int(match.group("round")),
                        "sample_index": sample_index,
                        "Timestamp": row.get("Timestamp", ""),
                        "Pageouts_per_sec": pageouts,
                        "Swapouts_per_sec": swapouts,
                        "Total_ops_per_sec": pageouts + swapouts,
                    }
                )

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"SAVED: {out_path}")


if __name__ == "__main__":
    main()

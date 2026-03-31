#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def split_cases(cases: List[Dict[str, Any]], dev_size: int) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in cases:
        k = str(item.get("type", "unknown"))
        grouped.setdefault(k, []).append(item)

    for k in grouped:
        grouped[k].sort(key=lambda x: str(x.get("id", "")))

    total = len(cases)
    ratio = dev_size / total if total else 0.0
    exact = {k: len(v) * ratio for k, v in grouped.items()}
    base = {k: int(exact[k]) for k in grouped}
    remainders = sorted(grouped.keys(), key=lambda x: exact[x] - base[x], reverse=True)
    remain = dev_size - sum(base.values())
    for k in remainders:
        if remain <= 0:
            break
        base[k] += 1
        remain -= 1

    dev, test = [], []
    for k, rows in grouped.items():
        cut = max(0, min(base[k], len(rows)))
        dev.extend(rows[:cut])
        test.extend(rows[cut:])

    dev.sort(key=lambda x: str(x.get("id", "")))
    test.sort(key=lambda x: str(x.get("id", "")))
    return {"dev": dev, "test": test}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in-file", default="data/eval/test_cases_verified.json")
    parser.add_argument("--dev-size", type=int, default=20)
    parser.add_argument("--dev-out", default="data/eval/test_cases_dev20.json")
    parser.add_argument("--test-out", default="data/eval/test_cases_test40.json")
    args = parser.parse_args()

    in_file = Path(args.in_file)
    if not in_file.is_absolute():
        in_file = ROOT_DIR / in_file
    dev_out = Path(args.dev_out)
    if not dev_out.is_absolute():
        dev_out = ROOT_DIR / dev_out
    test_out = Path(args.test_out)
    if not test_out.is_absolute():
        test_out = ROOT_DIR / test_out

    cases = json.loads(in_file.read_text("utf-8"))
    if args.dev_size <= 0 or args.dev_size >= len(cases):
        raise RuntimeError(f"dev-size 必须在 1 到 {len(cases)-1} 之间")

    parts = split_cases(cases, args.dev_size)
    dev_out.write_text(json.dumps(parts["dev"], ensure_ascii=False, indent=2), "utf-8")
    test_out.write_text(json.dumps(parts["test"], ensure_ascii=False, indent=2), "utf-8")

    print(f"TOTAL={len(cases)} DEV={len(parts['dev'])} TEST={len(parts['test'])}")
    print(f"DEV_OUT={dev_out}")
    print(f"TEST_OUT={test_out}")


if __name__ == "__main__":
    main()

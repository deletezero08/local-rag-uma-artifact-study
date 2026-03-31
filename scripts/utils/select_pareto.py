#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent.parent.parent
SWEEP_SUMMARY = ROOT / "results" / "tuning" / "sweep_summary.json"
ABLATION_SUMMARY = ROOT / "results" / "evaluation" / "legacy_misc" / "ablation_summary.json"
OUT_PATH = ROOT / "results" / "tuning" / "pareto_selection.json"


def _load(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text("utf-8"))


def _dominates(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    qa = (a.get("faithfulness", 0.0), a.get("relevance", 0.0))
    qb = (b.get("faithfulness", 0.0), b.get("relevance", 0.0))
    la = a.get("latency_mean", 10**9)
    lb = b.get("latency_mean", 10**9)
    not_worse = qa[0] >= qb[0] and qa[1] >= qb[1] and la <= lb
    strictly_better = qa[0] > qb[0] or qa[1] > qb[1] or la < lb
    return not_worse and strictly_better


def pareto_front(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    front = []
    for i, row in enumerate(rows):
        dominated = False
        for j, other in enumerate(rows):
            if i == j:
                continue
            if _dominates(other, row):
                dominated = True
                break
        if not dominated:
            front.append(row)
    return sorted(front, key=lambda x: (x.get("latency_mean", 10**9), -x.get("faithfulness", 0.0), -x.get("relevance", 0.0)))


def main() -> None:
    sweep = _load(SWEEP_SUMMARY)
    ablation = _load(ABLATION_SUMMARY)

    base_f = float(ablation["ensemble"]["faithfulness"]["mean"])
    base_r = float(ablation["ensemble"]["relevance"]["mean"])

    rows = [
        r for r in sweep.get("rows", [])
        if r.get("mode") == "ensemble" and not r.get("phase_a_enabled", False)
    ]
    front = pareto_front(rows)

    qualified = [r for r in rows if r.get("faithfulness", 0.0) >= base_f and r.get("relevance", 0.0) >= base_r]
    recommended = sorted(
        qualified if qualified else front,
        key=lambda x: (x.get("latency_mean", 10**9), -x.get("faithfulness", 0.0), -x.get("relevance", 0.0)),
    )[0] if (qualified or front) else {}

    payload = {
        "baseline": {
            "mode": "ensemble",
            "faithfulness_mean": base_f,
            "relevance_mean": base_r,
        },
        "candidate_count": len(rows),
        "pareto_front": front,
        "recommended": recommended,
        "selection_rule": "优先满足质量不低于 baseline，再按 latency_mean 最小化；若无满足项，则在 Pareto 前沿中选 latency 最小。",
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    print(f"✅ Pareto selection saved: {OUT_PATH}")
    if recommended:
        w = recommended.get("weights", {})
        print(
            "推荐配置:",
            f"vector={w.get('vector')}, bm25={w.get('bm25')}, rrf_k={recommended.get('rrf_k')}, latency={recommended.get('latency_mean')}",
        )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
QSET_PATH = ROOT_DIR / "experiments" / "question_set.md"
RESULTS_DIR = ROOT_DIR / "experiments" / "results"
OUT_JSON = ROOT_DIR / "experiments" / "question_set_ground_truth_candidates.json"
OUT_MD = ROOT_DIR / "experiments" / "question_set_ground_truth_candidates.md"


def parse_question_set(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text("utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 4:
            continue
        if cols[0].lower() == "id" or cols[0].startswith("---"):
            continue
        rows.append(
            {
                "id": cols[0],
                "type": cols[1],
                "question": cols[2],
                "source_docs": [c.strip() for c in cols[3].split(",") if c.strip()],
            }
        )
    return rows


def flatten_checkpoint_rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], list):
            rows: List[Dict[str, Any]] = []
            for it in payload:
                rows.extend([x for x in it if isinstance(x, dict)])
            return rows
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        rows: List[Dict[str, Any]] = []
        for key in ("rows", "baseline_rows_all", "optimized_rows_all"):
            part = payload.get(key)
            if isinstance(part, list):
                rows.extend([x for x in part if isinstance(x, dict)])
        return rows
    return []


def pick_answer_map() -> Dict[str, str]:
    checkpoint_files = sorted(
        list(RESULTS_DIR.glob("temp_ensemble_accept_baseline_no_clip*checkpoint.json")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not checkpoint_files:
        return {}
    rows = flatten_checkpoint_rows(json.loads(checkpoint_files[0].read_text("utf-8")))
    answer_map: Dict[str, str] = {}
    for row in rows:
        qid = str(row.get("id", "")).strip()
        answer = str(row.get("answer", "")).strip()
        if qid and answer and qid not in answer_map:
            answer_map[qid] = answer
    return answer_map


def build_outputs() -> None:
    qrows = parse_question_set(QSET_PATH)
    answer_map = pick_answer_map()
    out_rows: List[Dict[str, Any]] = []
    for row in qrows:
        out_rows.append(
            {
                "id": row["id"],
                "type": row["type"],
                "question": row["question"],
                "source_docs": row["source_docs"],
                "ground_truth_candidate": answer_map.get(row["id"], ""),
                "label_source": "baseline_checkpoint_bootstrap",
                "needs_review": True,
            }
        )
    OUT_JSON.write_text(json.dumps(out_rows, ensure_ascii=False, indent=2), "utf-8")

    md_lines: List[str] = []
    md_lines.append("# Question Set Ground Truth Candidates")
    md_lines.append("")
    md_lines.append("请逐条人工复核以下候选答案。")
    md_lines.append("")
    for idx, row in enumerate(out_rows, start=1):
        md_lines.append(f"## {idx}. {row['id']} ({row['type']})")
        md_lines.append("")
        md_lines.append(f"问题：{row['question']}")
        md_lines.append("")
        md_lines.append(f"来源文档：{', '.join(row['source_docs'])}")
        md_lines.append("")
        md_lines.append("候选标准答案：")
        md_lines.append("")
        md_lines.append(row["ground_truth_candidate"] if row["ground_truth_candidate"] else "（未生成，需人工补写）")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
    OUT_MD.write_text("\n".join(md_lines), "utf-8")

    generated = sum(1 for x in out_rows if x["ground_truth_candidate"].strip())
    print(f"TOTAL={len(out_rows)} GENERATED={generated} MISSING={len(out_rows)-generated}")
    print(f"SAVED_JSON={OUT_JSON}")
    print(f"SAVED_MD={OUT_MD}")


if __name__ == "__main__":
    build_outputs()

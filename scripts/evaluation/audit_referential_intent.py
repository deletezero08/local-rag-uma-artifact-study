#!/usr/bin/env python3
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import DOCS_DIR, MEMORY_DIR, _memory_key, ensure_dirs, list_doc_files, save_memory
from src.router import IntentRouter


CASES_FILE = ROOT_DIR / "data" / "eval" / "referential_cases.json"
RESULT_FILE = ROOT_DIR / "results" / "evaluation" / "legacy_misc" / "referential_intent_audit.json"


def _prepare_docs() -> None:
    ensure_dirs()
    (DOCS_DIR / "referential_alpha.md").write_text("# Alpha\n历史回溯测试文档。", "utf-8")
    (DOCS_DIR / "referential_beta.md").write_text("# Beta\n近期记忆回退测试文档。", "utf-8")


def _cleanup_temp_memory(tracked_files: List[str]) -> None:
    for rel_path in tracked_files:
        key = _memory_key(rel_path)
        path = MEMORY_DIR / f"{key}.json"
        if path.exists():
            path.unlink()


def _run_case(router: IntentRouter, case: Dict[str, Any]) -> Dict[str, Any]:
    setup_file = case.get("setup_memory_file")
    if setup_file:
        save_memory(setup_file, f"{setup_file} 的关键结论。", session_id="referential-audit")

    target_filename, _, _, meta = router.analyze(
        question=case["question"],
        category=case.get("category"),
        history_arr=case.get("history"),
    )

    actual = {
        "intent_state": meta.get("intent_state"),
        "fallback_reason": meta.get("fallback_reason"),
        "memory_fallback_file": meta.get("memory_fallback_file"),
        "target_file": target_filename,
    }

    expected_state = case.get("expected_state")
    expected_reason = case.get("expected_fallback_reason")
    expected_file = case.get("expected_file")

    state_ok = actual["intent_state"] == expected_state
    reason_ok = True if expected_reason is None else actual["fallback_reason"] == expected_reason
    file_ok = True
    if expected_file is not None:
        file_ok = (actual["memory_fallback_file"] == expected_file) or (actual["target_file"] == expected_file)

    passed = state_ok and reason_ok and file_ok
    return {
        "id": case.get("id"),
        "description": case.get("description"),
        "question": case.get("question"),
        "expected": {
            "intent_state": expected_state,
            "fallback_reason": expected_reason,
            "file": expected_file,
        },
        "actual": actual,
        "pass": passed,
    }


def main() -> None:
    if not CASES_FILE.exists():
        raise FileNotFoundError(f"Cases file not found: {CASES_FILE}")

    _prepare_docs()
    cases = json.loads(CASES_FILE.read_text("utf-8"))
    router = IntentRouter(llm=None, doc_list_func=list_doc_files)

    tracked_memory = [c["setup_memory_file"] for c in cases if c.get("setup_memory_file")]
    runs = [_run_case(router, case) for case in cases]

    matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in runs:
        exp = r["expected"]["intent_state"] or "none"
        act = r["actual"]["intent_state"] or "none"
        matrix[exp][act] += 1

    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(runs),
        "passed": sum(1 for r in runs if r["pass"]),
        "overall_pass": all(r["pass"] for r in runs),
        "cases": runs,
        "confusion_matrix": matrix,
    }

    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")

    print("📊 Referential Intent Audit")
    for r in runs:
        status = "✅" if r["pass"] else "❌"
        print(f"{status} {r['id']} | expected={r['expected']['intent_state']} actual={r['actual']['intent_state']}")
    print(f"Overall: {'PASS' if payload['overall_pass'] else 'FAIL'} ({payload['passed']}/{payload['total']})")
    print(f"Saved: {RESULT_FILE}")

    _cleanup_temp_memory(tracked_memory)


if __name__ == "__main__":
    main()

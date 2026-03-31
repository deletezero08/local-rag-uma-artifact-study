#!/usr/bin/env python3
import json
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parent.parent.parent
OUT_BASE = ROOT / "output" / "thesis_data"
KEEP_LATEST = 1
SOURCE_GROUPS: Tuple[Tuple[str, Path, Tuple[str, ...]], ...] = (
    ("evaluation", ROOT / "results" / "evaluation", ("*.json", "*.csv", "*.md")),
    ("tuning", ROOT / "results" / "tuning", ("*.json",)),
    ("hardware", ROOT / "results" / "hardware", ("*.json", "*.csv")),
)
SKIP_NAMES = {"README.md"}


def iter_snapshot_dirs() -> Iterable[Path]:
    if not OUT_BASE.exists():
        return []
    return sorted([p for p in OUT_BASE.iterdir() if p.is_dir()], reverse=True)


def collect_snapshot_index() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for d in iter_snapshot_dirs():
        manifest = d / "manifest.json"
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text("utf-8"))
        rows.append(
            {
                "snapshot": d.name,
                "created_at": data.get("created_at", ""),
                "archive_dir": str(d),
                "files_count": len(data.get("files", [])),
            }
        )
    return rows


def refresh_latest_files(index_rows: List[Dict[str, Any]]) -> None:
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    index_path = OUT_BASE / "index.json"
    index_path.write_text(json.dumps(index_rows, ensure_ascii=False, indent=2), "utf-8")
    latest = index_rows[0] if index_rows else {}
    latest_path = OUT_BASE / "latest_snapshot.json"
    latest_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2), "utf-8")


def prune_old_snapshots(keep_latest: int = KEEP_LATEST) -> None:
    rows = collect_snapshot_index()
    for row in rows[keep_latest:]:
        archive_dir = Path(row["archive_dir"])
        if archive_dir.exists():
            shutil.rmtree(archive_dir)


def iter_source_files() -> Iterable[Tuple[str, Path]]:
    for label, base_dir, patterns in SOURCE_GROUPS:
        if not base_dir.exists():
            continue
        seen = set()
        for pattern in patterns:
            for file_path in sorted(base_dir.glob(pattern), key=lambda p: p.name):
                if file_path.name in SKIP_NAMES or file_path.name in seen:
                    continue
                seen.add(file_path.name)
                yield label, file_path


def main() -> None:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = OUT_BASE / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for label, file_path in iter_source_files():
        target = out_dir / label / file_path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
        copied.append(str(target.relative_to(out_dir)))

    manifest = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source_dirs": {label: str(path) for label, path, _ in SOURCE_GROUPS},
        "archive_dir": str(out_dir),
        "files": sorted(copied),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    prune_old_snapshots()
    refresh_latest_files(collect_snapshot_index())
    print(f"✅ archive created: {out_dir}")
    print(f"files: {len(copied)}")


if __name__ == "__main__":
    main()

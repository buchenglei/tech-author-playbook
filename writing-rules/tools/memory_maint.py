#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_maint.py — 阶段 2 清理过时记忆负担（不删真源）。

- 列出可归档项
- 将 workflow/*.bak、*.tmp、draft-*.md 移入 workflow/archive/
- 压缩 notes_brief 到最近 20 条
- 打印 never_delete 清单提醒

用法：python3 memory_maint.py books/my-book [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

KEEP_EXACT = {
    "00_阶段状态.json", "04_写作宪法.md", "01_读者报告.md", "02_编辑审校.md",
    "03_作者改进方案.md", "05_章节滚动评估.md", "07_项目反哺报告.md",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    book = Path(a.book_dir).resolve()
    wf = book / "workflow"
    if not wf.is_dir():
        print(f"错误：缺 {wf}")
        return 2
    archive = wf / "archive"
    archive.mkdir(exist_ok=True)
    memory = wf / "memory"
    memory.mkdir(exist_ok=True)

    moved = []
    for p in sorted(wf.glob("*")):
        if not p.is_file():
            continue
        name = p.name
        if name in KEEP_EXACT or name.endswith(".md") and not name.startswith(("draft-", "tmp-", "old-")):
            if not name.endswith((".bak", ".tmp")) and not name.startswith(("draft-", "tmp-", "old-")):
                continue
        if name.endswith((".bak", ".tmp")) or name.startswith(("draft-", "tmp-", "old-")):
            dest = archive / f"{datetime.now():%Y%m%d}-{name}"
            if a.dry_run:
                moved.append(f"would move {name}")
            else:
                shutil.move(str(p), dest)
                moved.append(f"moved {name} -> archive/")

    # 压缩 notes_brief
    st_path = wf / "00_阶段状态.json"
    if st_path.is_file():
        st = json.loads(st_path.read_text(encoding="utf-8"))
        notes = st.get("notes_brief") or []
        if len(notes) > 20:
            st["notes_brief"] = notes[-20:]
            if not a.dry_run:
                st_path.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            moved.append(f"trim notes_brief {len(notes)} -> 20")

    # 摘要到 memory/
    brief = memory / "CURRENT.md"
    lines = [f"# 当前窗口摘要（{datetime.now():%Y-%m-%d %H:%M}）", ""]
    if st_path.is_file():
        st = json.loads(st_path.read_text(encoding="utf-8"))
        lines += [
            f"- phase: {st.get('phase')}",
            f"- chapters_done: {', '.join(st.get('chapters_done') or []) or '—'}",
            f"- blockers: {len(st.get('blockers') or [])}",
            "",
            "## notes_brief 尾部",
        ]
        lines += [f"- {x}" for x in (st.get("notes_brief") or [])[-5:]]
    if not a.dry_run:
        brief.write_text("\n".join(lines) + "\n", encoding="utf-8")
    moved.append("refresh memory/CURRENT.md")

    print("memory_maint:")
    for m in moved or ["nothing to do"]:
        print(" ", m)
    print("禁止删除：01–08 标准文件、frozen units、handoff、台账术表、写作宪法、三类报告、00_阶段状态.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress_report.py — 一页进度：体量 / 页数估计 / 缺报告 / 阶段。

用法：python3 progress_report.py books/my-book
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wordcount import cjk_len  # noqa: E402  与 G3/G8/合同同口径


def load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: progress_report.py <book_dir>")
        return 2
    book = Path(sys.argv[1]).resolve()
    outline = load_json(book / "02_outline.json")
    wf = load_json(book / "workflow" / "00_阶段状态.json")
    pages = (load_json(book / "workflow" / "00_大纲合同.json")).get("pages") or {}

    secs = [s for ch in (outline.get("chapters") or [])
            for s in (ch.get("sections") or [])]
    written = budget = n_units = 0
    for s in secs:
        budget += int(s.get("words") or 0)
        p = book / "units" / f"{(s.get('id') or '')}.md"
        if p.is_file():
            written += cjk_len(p.read_text(encoding="utf-8", errors="ignore"))
            n_units += 1

    cpp = int(pages.get("chars_per_page") or 450)
    lo, hi = pages.get("target_min"), pages.get("target_max")
    est = written / cpp if cpp else 0
    missing = [n for n in ("01_读者报告.md", "02_编辑审校.md", "09_大纲×规范融合评估.md")
               if not (book / "workflow" / n).is_file()]

    print(f"书：{wf.get('book') or book.name}")
    print(f"phase={wf.get('phase')}  rule_conflict={wf.get('rule_conflict_status')}")
    print(f"单元：{n_units}/{len(secs)} 已有正文")
    print(f"字数：实写约 {written} / 节预算合计 {budget}（cjk_len）")
    print(f"页数估计：约 {est:.0f} 页（合同目标 {lo}–{hi}）")
    if lo and est < lo:
        print(f"⚠ 体量不足：还差约 {lo - est:.0f} 页量级（禁止用梗概凑）")
    print(f"缺报告文件：{missing or '无'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress_report.py — 一页进度：体量 / 页数估计 / 缺报告 / 阶段。

用法：python3 progress_report.py books/my-book
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def cjk_len(s: str) -> int:
    return len(re.findall(r"[一-鿿]", s)) + len(re.findall(r"[A-Za-z0-9_]+", s)) // 2


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: progress_report.py <book_dir>")
        return 2
    book = Path(sys.argv[1]).resolve()
    outline = json.loads((book / "02_outline.json").read_text(encoding="utf-8"))
    state = json.loads((book / "05_state.json").read_text(encoding="utf-8"))
    contract = {}
    cp = book / "workflow" / "00_大纲合同.json"
    if cp.is_file():
        contract = json.loads(cp.read_text(encoding="utf-8"))

    secs = []
    for ch in outline.get("chapters") or []:
        for s in ch.get("sections") or []:
            secs.append(s)
    written = 0
    budget = 0
    n_units = 0
    for s in secs:
        budget += int(s.get("words") or 0)
        p = book / "units" / f"{(s.get('id') or '')}.md"
        if p.is_file():
            written += cjk_len(p.read_text(encoding="utf-8", errors="ignore"))
            n_units += 1
    pages = contract.get("pages") or {}
    cpp = int(pages.get("chars_per_page") or 450)
    lo_p = pages.get("target_min")
    hi_p = pages.get("target_max")
    est_pages = written / cpp if cpp else 0

    missing = []
    for n in ("01_读者报告.md", "02_编辑审校.md", "09_大纲×规范融合评估.md"):
        p = book / "workflow" / n
        if not p.is_file():
            missing.append(n)

    print(f"书：{state.get('book')}")
    print(f"阶段：{state.get('state') or (book / 'workflow' / '00_阶段状态.json')}")
    wf = json.loads((book / "workflow" / "00_阶段状态.json").read_text(encoding="utf-8")) if (book / "workflow" / "00_阶段状态.json").is_file() else {}
    print(f"phase={wf.get('phase')}  rule_conflict={wf.get('rule_conflict_status')}")
    print(f"单元：{n_units}/{len(secs)} 已有正文")
    print(f"字数：实写约 {written} / 节预算合计 {budget}")
    print(f"页数估计：约 {est_pages:.0f} 页（合同目标 {lo_p}–{hi_p}）")
    if lo_p and est_pages < lo_p:
        print(f"⚠ 体量不足：还差约 {lo_p - est_pages:.0f} 页量级（禁止用梗概凑）")
    print(f"缺报告文件：{missing or '无'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

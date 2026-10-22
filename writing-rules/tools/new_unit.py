#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""new_unit.py — 从 outline 预填单元 spec，减少手抄与 Token。

用法：
  python3 new_unit.py books/my-book C01-S2
  python3 new_unit.py books/my-book --all
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KIT_SPEC = ROOT / "writing-rules" / "kit" / "03_单元spec.md"

TEMPLATE = """# 单元 spec：{id}

## 1. id
{id}

## 2. question
{question}

## 3. bridge
{bridge}

## 4. layer
{layer}

## 5. produces
{produces}

## 6. claims（断言清单）

| # | 断言 | 级 | 来源 / 命令 | 台账 |
|---|---|---|---|---|
| A1 |  | E1 |  | E- |

## 7. evidence
（每条断言的可复现证据）

## 8. concepts_introduced

| 术语 | 一句定义（≤40 字） | 禁止别名 |
|---|---|---|
|  |  |  |

## 9. concepts_used
{concepts}

## 10. code

| 文件 | 行范围 | 代码块用途 |
|---|---|---|
| — | — | 无 |

## 11. word_budget
目标 {words} 字，下限 {lo}，上限 {hi}

---

## 写前自问（三层剥法，§0.1）

| 层 | 本节的答案 |
|---|---|
| 现象层留下什么问题 |  |
| 机制层接住它，推翻/修正了什么 |  |
| 代价层给出什么判断依据 |  |

---

## DoD

写作中快检：①只答 question ②代价非空 ③数字挂账。
冻结前全量八项 + lint 零 P0（见 briefs/S3_单元.md）。
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir")
    ap.add_argument("unit_id", nargs="?", default="")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    book = Path(a.book_dir).resolve()
    outline = json.loads((book / "02_outline.json").read_text(encoding="utf-8"))
    units = book / "units"
    units.mkdir(exist_ok=True)

    wanted = []
    for ch in outline.get("chapters") or []:
        for sec in ch.get("sections") or []:
            sid = sec.get("id") or ""
            if a.all or sid == a.unit_id:
                wanted.append(sec)

    if not wanted:
        print(f"错误：未找到单元 {a.unit_id!r}", file=sys.stderr)
        return 2

    for sec in wanted:
        sid = sec["id"]
        out = units / f"{sid}.spec.md"
        if out.exists():
            print(f"skip {out.name}（已存在）")
            continue
        words = int(sec.get("words") or 2500)
        text = TEMPLATE.format(
            id=sid,
            question=sec.get("question", ""),
            bridge=sec.get("bridge", ""),
            layer=sec.get("layer", ""),
            produces=sec.get("produces", ""),
            concepts=", ".join(sec.get("concepts") or []) or "（无）",
            words=words,
            lo=int(words * 0.6),
            hi=int(words * 1.2),
        )
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

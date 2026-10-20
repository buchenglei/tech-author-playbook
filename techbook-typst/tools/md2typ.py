#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""md2typ.py — 将 writing-rules 单元 Markdown 装配为 techbook-typst 章节。

契约（见 PROBLEMS.md P7）：
  # 章标题        → = 标题
  ## 小节         → == 标题
  ### 小节        → === 标题
  Markdown 表格   → #tbl(...)
  - / 1. 列表     → Typst 列表
  ```lang 代码块  → 围栏代码（lang 缺失时用 text）
  正文段落        → 段落（组件如 #goal/#tip 由编者补，不自动猜）

用法：
  python3 md2typ.py units/C01-S1.md units/C01-S2.md ... --title "章标题" -o chapters/ch1.typ
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def md_table_to_typst(lines: list[str], caption: str = "表") -> str:
    rows = []
    for ln in lines:
        s = ln.strip()
        if not s.startswith("|"):
            continue
        if set(s.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        rows.append(cells)
    if not rows:
        return ""
    header, body = rows[0], rows[1:]
    def cell(c: str) -> str:
        c = c.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
        c = c.replace("#", "\\#")
        return f"[{c}]"
    cap = caption.replace("[", "\\[").replace("]", "\\]").replace("#", "\\#")
    parts = ["#tbl(", "  columns: (" + ", ".join(["1fr"] * len(header)) + "),",
             "  header: (" + ", ".join(cell(h) for h in header) + "),"]
    for r in body:
        r = (r + [""] * len(header))[: len(header)]
        parts.append("  (" + ", ".join(cell(c) for c in r) + "),")
    parts.append(f"  caption: [{cap}],")
    parts.append(")")
    return "\n".join(parts)


def convert(md_text: str, chapter_title: str | None = None) -> str:
    lines = md_text.splitlines()
    out: list[str] = ['#import "../src/book.typ": *', ""]
    if chapter_title:
        out.append(f"= {chapter_title}")
        out.append("")

    i = 0
    n = len(lines)
    first_h1 = True
    last_heading = "表"
    while i < n:
        ln = lines[i]
        s = ln.strip()

        # fenced code
        if s.startswith("```"):
            lang = s[3:].strip() or "text"
            block = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            body = "\n".join(block).replace("\\", "\\\\")
            out.append(f"```{lang}")
            out.extend(block)
            out.append("```")
            out.append("")
            continue

        # table
        if s.startswith("|"):
            tbl_lines = []
            while i < n and lines[i].strip().startswith("|"):
                tbl_lines.append(lines[i])
                i += 1
            out.append(md_table_to_typst(tbl_lines, caption=last_heading))
            out.append("")
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            last_heading = title
            if level == 1 and not chapter_title and first_h1:
                out.append(f"= {title}")
                first_h1 = False
            elif level == 1 and chapter_title:
                # 单元标题 → 章内二级
                out.append(f"== {title}")
            elif level == 2 and chapter_title:
                out.append(f"=== {title}")
            elif level == 2:
                out.append(f"== {title}")
            elif level == 3:
                out.append(f"=== {title}")
            else:
                out.append(f"==== {title}")
            out.append("")
            i += 1
            continue

        # lists
        if re.match(r"^[-*+]\s+", s):
            item = re.sub(r"^[-*+]\s+", "", s)
            out.append(f"- {inline(item)}")
            i += 1
            continue
        m = re.match(r"^(\d+)[.)]\s+(.*)$", s)
        if m:
            out.append(f"+ {inline(m.group(2))}")
            i += 1
            continue

        # blank
        if not s:
            out.append("")
            i += 1
            continue

        # paragraph (join consecutive plain lines)
        para = [s]
        i += 1
        while i < n:
            t = lines[i].strip()
            if (not t or t.startswith("#") or t.startswith("|") or t.startswith("```")
                    or re.match(r"^[-*+]\s+", t) or re.match(r"^\d+[.)]\s+", t)):
                break
            para.append(t)
            i += 1
        out.append(inline(" ".join(para)))
        out.append("")

    # drop leading unit H1 if chapter_title provided and we emitted it as section
    return "\n".join(out).strip() + "\n"


def inline(text: str) -> str:
    # bold **x** → #strong[x]
    text = re.sub(r"\*\*([^*]+)\*\*", r"#strong[\1]", text)
    # code `x` → #code[x]  (only simple)
    text = re.sub(r"`([^`]+)`", r"#code[\1]", text)
    # 裸 # 需转义，避免被当成 Typst 标记（code 组件内容内 # 已安全）
    if "#strong[" not in text and "#code[" not in text:
        text = text.replace("#", "\\#")
    else:
        # 保护已生成标记外的裸 #
        parts = re.split(r"(#strong\[[^\]]*\]|#code\[[^\]]*\])", text)
        text = "".join(p if p.startswith("#strong") or p.startswith("#code") else p.replace("#", "\\#")
                       for p in parts)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--title", default="")
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args()
    parts = []
    for src in a.sources:
        parts.append(Path(src).read_text(encoding="utf-8"))
    merged = "\n\n".join(parts)
    text = convert(merged, chapter_title=a.title or None)
    Path(a.output).write_text(text, encoding="utf-8")
    print(f"wrote {a.output} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

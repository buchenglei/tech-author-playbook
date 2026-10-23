#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""md2typ.py — 将 writing-rules 单元 Markdown 装配为 techbook-typst 章节。

契约：
  # 章标题        → = 标题（有 --title 时降为 ==）
  ## 小节         → == 标题（有 --title 时降为 ===）
  Markdown 表格   → #tbl(...)（支持 <!-- caption: ... -->）
  - / 1. 列表     → Typst 列表
  ```lang 代码块  → 围栏代码（lang 缺失时用 text）
  ![alt](p)       → #fig(image(p), caption: [alt]) / 行内 #image(p)
  [text](url)     → #link("url")[text]
  > 引用          → #quote[...]
  --- / ***       → 分隔线

图片资源：
  --asset-dir <dir> 时，把 Markdown 相对图片复制到 <dir>/<源文件名>/<图片名>，
  并把引用重写为相对 -o 输出目录的路径；找不到图片时保留原路径并警告。

用法：
  python3 md2typ.py units/C01-S1.md units/C01-S2.md --title "章标题" -o chapters/ch1.typ
  python3 md2typ.py units/C01-S1.md --title "章标题" -o chapters/ch1.typ --asset-dir chapters/../assets
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CAPTION_RE = re.compile(r"<!--\s*caption:\s*(.*?)\s*-->")
HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")


def _escape_cell(c: str) -> str:
    c = c.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    return c.replace("#", "\\#")


def md_table_to_typst(lines: list[str], caption: str | None = None) -> str:
    rows = []
    for ln in lines:
        s = ln.strip()
        if not s.startswith("|"):
            continue
        if set(s.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        rows.append([c.strip() for c in s.strip("|").split("|")])
    if not rows:
        return ""
    header, body = rows[0], rows[1:]
    parts = [
        "#tbl(",
        "  columns: (" + ", ".join(["1fr"] * len(header)) + "),",
        "  header: (" + ", ".join(f"[{_escape_cell(h)}]" for h in header) + "),",
    ]
    for r in body:
        r = (r + [""] * len(header))[: len(header)]
        parts.append("  (" + ", ".join(f"[{_escape_cell(c)}]" for c in r) + "),")
    if caption:
        parts.append(f"  caption: [{_escape_cell(caption)}],")
    else:
        parts.append("  caption: none,")
    parts.append(")")
    return "\n".join(parts)


class Converter:
    def __init__(self, source_path: Path | None = None,
                 asset_dir: Path | None = None,
                 output_dir: Path | None = None):
        self.source_path = source_path
        self.asset_dir = asset_dir
        self.output_dir = output_dir
        self.warnings: list[str] = []

    def resolve_asset(self, src: str) -> str:
        if src.startswith(("http://", "https://", "data:")):
            self.warnings.append(f"外部图片未下载：{src}")
            return src
        if self.source_path is None:
            return src
        p = (self.source_path.parent / src).resolve()
        if not p.is_file():
            self.warnings.append(f"图片不存在：{src}（来自 {self.source_path.name}）")
            return src
        if self.asset_dir is None:
            return src
        dest = self.asset_dir / self.source_path.stem / p.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        if self.output_dir is not None:
            return os.path.relpath(dest, self.output_dir).replace("\\", "/")
        return dest.as_posix()

    def hold(self, tokens: list[str], value: str) -> str:
        tokens.append(value)
        return f"\x00{len(tokens) - 1}\x00"

    def inline(self, text: str) -> str:
        tokens: list[str] = []
        text = IMAGE_RE.sub(
            lambda m: self.hold(tokens, f'#image("{self.resolve_asset(m.group(2))}")'),
            text,
        )
        text = LINK_RE.sub(
            lambda m: self.hold(tokens, f'#link("{m.group(2)}")[{m.group(1)}]'),
            text,
        )
        text = re.sub(r"\*\*([^*]+)\*\*",
                      lambda m: self.hold(tokens, f"#strong[{m.group(1)}]"), text)
        text = re.sub(r"`([^`]+)`",
                      lambda m: self.hold(tokens, f"#code[{m.group(1)}]"), text)
        text = text.replace("#", "\\#")
        text = text.replace("[", "\\[").replace("]", "\\]")
        for i, value in enumerate(tokens):
            text = text.replace(f"\x00{i}\x00", value)
        return text

    def convert(self, md_text: str, chapter_title: str | None = None,
                emit_import: bool = True, emit_chapter_title: bool = True) -> str:
        lines = md_text.splitlines()
        out: list[str] = []
        if emit_import:
            out += ['#import "../src/book.typ": *', ""]
        if chapter_title and emit_chapter_title:
            out += [f"= {chapter_title}", ""]

        offset = 1 if chapter_title else 0
        pending_caption: str | None = None
        i, n = 0, len(lines)
        while i < n:
            ln = lines[i]
            s = ln.strip()

            # HTML caption / comment
            if s.startswith("<!--"):
                m = CAPTION_RE.match(s)
                if m:
                    pending_caption = m.group(1)
                i += 1
                continue

            # fenced code
            if s.startswith("```"):
                lang = s[3:].strip() or "text"
                block = []
                i += 1
                while i < n and not lines[i].strip().startswith("```"):
                    block.append(lines[i])
                    i += 1
                i += 1
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
                caption = pending_caption
                # 也允许表后紧跟/隔一空行 <!-- caption: ... -->（作者更自然的写法）
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                if j < n:
                    cm = CAPTION_RE.match(lines[j].strip())
                    if cm:
                        caption = cm.group(1)
                        i = j + 1
                out.append(md_table_to_typst(tbl_lines, caption))
                pending_caption = None
                out.append("")
                continue

            # standalone image
            m = IMAGE_RE.fullmatch(s)
            if m:
                alt, src = m.group(1), m.group(2)
                path = self.resolve_asset(src)
                cap = f", caption: [{_escape_cell(alt)}]" if alt else ", caption: none"
                out += [f'#fig(image("{path}"){cap})', ""]
                i += 1
                continue

            # blockquote
            if s.startswith(">"):
                quote_lines = []
                while i < n and lines[i].strip().startswith(">"):
                    quote_lines.append(re.sub(r"^\s*>\s?", "", lines[i]).strip())
                    i += 1
                out += ["#quote[", *[self.inline(x) for x in quote_lines], "]", ""]
                continue

            # horizontal rule
            if HR_RE.match(s):
                out += ["#line(length: 100%)", ""]
                i += 1
                continue

            # headings
            m = re.match(r"^(#{1,6})\s+(.*)$", s)
            if m:
                level = min(len(m.group(1)) + offset, 4)
                out += ["=" * level + " " + m.group(2).strip(), ""]
                i += 1
                continue

            # lists
            if re.match(r"^[-*+]\s+", s):
                item = re.sub(r"^[-*+]\s+", "", s)
                out.append(f"- {self.inline(item)}")
                i += 1
                continue
            m = re.match(r"^(\d+)[.)]\s+(.*)$", s)
            if m:
                out.append(f"+ {self.inline(m.group(2))}")
                i += 1
                continue

            if not s:
                out.append("")
                i += 1
                continue

            # paragraph: join consecutive plain lines
            para = [s]
            i += 1
            while i < n:
                t = lines[i].strip()
                if (not t or t.startswith("#") or t.startswith("|") or t.startswith("```")
                        or t.startswith(">") or t.startswith("<!--")
                        or re.match(r"^[-*+]\s+", t) or re.match(r"^\d+[.)]\s+", t)
                        or HR_RE.match(t)):
                    break
                para.append(t)
                i += 1
            out += [self.inline(" ".join(para)), ""]

        return "\n".join(out).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--title", default="")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--asset-dir", default="", help="复制图片资源的目标目录")
    a = ap.parse_args()

    output = Path(a.output)
    asset_dir = Path(a.asset_dir) if a.asset_dir else None
    parts: list[str] = []
    warnings: list[str] = []
    for idx, src in enumerate(a.sources):
        src_path = Path(src)
        conv = Converter(src_path, asset_dir, output.parent)
        text = src_path.read_text(encoding="utf-8-sig")
        parts.append(conv.convert(
            text,
            chapter_title=a.title or None,
            emit_import=(idx == 0),
            emit_chapter_title=(idx == 0),
        ))
        warnings.extend(conv.warnings)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(parts).strip() + "\n", encoding="utf-8")
    for w in warnings:
        print(f"警告：{w}", file=sys.stderr)
    print(f"wrote {output} ({len(parts)} source(s), {len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())

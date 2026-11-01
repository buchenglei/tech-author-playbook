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

Typst 转义约定（本文件的核心，务必不要改坏）：
  Typst markup 里 `_ * $ < > @ ~ ` # [ ] \\` 都是语法字符。散文里出现孤立
  的 `_` 会开启未闭合的 emphasis，编译直接报 "unclosed delimiter"。
  因此本文件区分两条通道：
    * markup 通道（正文散文、表格单元格、标题、链接文本）
      → 用 markup_escape() 逐字符转义 12 个语法字符。
    * 字符串通道（行内代码、加粗的整段文字）
      → 用 typst_string() 包成 Typst 字符串字面量，字符串内容不被 markup
        解析，因此 08_读者假设.md、List<T>、x:DataType="vm:Boo" 之类原样输出。
      注意：#code("...") 传字符串是全字面的，而 #code[...] 传 content block
      会把内容当 markup 解析（这正是此前编译失败的根因）。

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
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
CODE_RE = re.compile(r"`([^`]+)`")

# Typst markup 语法字符 → 转义后写法（12 项，均实测编译通过）
MARKUP_ESCAPES = {
    "\\": "\\\\",
    "#": "\\#",
    "[": "\\[",
    "]": "\\]",
    "_": "\\_",
    "*": "\\*",
    "$": "\\$",
    "<": "\\<",
    ">": "\\>",
    "@": "\\@",
    "~": "\\~",
    "`": "\\`",
}


def markup_escape(s: str) -> str:
    """把普通文本转成 Typst markup 安全文本（不处理引号，保留 smart quote）。"""
    return "".join(MARKUP_ESCAPES.get(ch, ch) for ch in s)


def typst_string(s: str) -> str:
    """把任意文本包成 Typst 字符串字面量；字符串内容不会被 markup 解析。"""
    out = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{out}"'


def render_cell(c: str) -> str:
    """表格单元格 / 题注渲染：行内代码走字符串通道，其余走 markup 转义。"""
    tokens: list[str] = []

    def sub(m: re.Match[str]) -> str:
        tokens.append(f"#code({typst_string(m.group(1))})")
        return f"\x00{len(tokens) - 1}\x00"

    text = CODE_RE.sub(sub, c)
    text = markup_escape(text)
    for i, value in enumerate(tokens):
        text = text.replace(f"\x00{i}\x00", value)
    return text


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
        "  header: (" + ", ".join(f"[{render_cell(h)}]" for h in header) + ",),",
    ]
    for r in body:
        r = (r + [""] * len(header))[: len(header)]
        parts.append("  (" + ", ".join(f"[{render_cell(c)}]" for c in r) + ",),")
    if caption:
        parts.append(f"  caption: [{render_cell(caption)}],")
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
            # 资源原地不动，但引用必须相对输出文件重定位（P23：装配产物
            # 若沿用单元视角的路径，落位到 chapters/ 后会指错目录）
            if self.output_dir is not None:
                return os.path.relpath(p, self.output_dir).replace("\\", "/")
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
        """把一行 Markdown 散文渲染成 Typst markup。

        关键：所有语法片段先抽成 token 占位符，只对「纯文本部分」做 markup
        转义，最后再把 token 放回——顺序不能反，否则会破坏宏调用。
        """
        tokens: list[str] = []

        # 1. 图片（整段替换成宏调用）
        text = IMAGE_RE.sub(
            lambda m: self.hold(tokens, f"#image({typst_string(self.resolve_asset(m.group(2)))})"),
            text,
        )

        # 2. 链接：#link("url")[文本]。link 的第二个参数只能是 content block，
        #    所以链接文本走 markup 转义通道。
        text = LINK_RE.sub(
            lambda m: self.hold(
                tokens,
                f"#link({typst_string(m.group(2))})[{markup_escape(m.group(1))}]",
            ),
            text,
        )

        # 3. 加粗：#strong[内容]，内部允许再嵌行内代码
        def bold_sub(m: re.Match[str]) -> str:
            inner = self._inner(m.group(1), tokens)
            return self.hold(tokens, f"#strong[{inner}]")

        text = BOLD_RE.sub(bold_sub, text)

        # 4. 行内代码：字符串通道，内容全字面
        text = CODE_RE.sub(
            lambda m: self.hold(tokens, f"#code({typst_string(m.group(1))})"),
            text,
        )

        # 5. 剩余纯文本做 markup 转义（此时 token 仍是占位符，不会被误伤）
        text = markup_escape(text)

        # 6. 放回 token
        for i, value in enumerate(tokens):
            text = text.replace(f"\x00{i}\x00", value)
        return text

    def _inner(self, text: str, tokens: list[str]) -> str:
        """渲染一段被包裹进 content block 的文本（加粗内部用）。"""
        inner_tokens: list[str] = []
        t = CODE_RE.sub(
            lambda m: self.hold(inner_tokens, f"#code({typst_string(m.group(1))})"),
            text,
        )
        t = markup_escape(t)
        for i, value in enumerate(inner_tokens):
            t = t.replace(f"\x00{i}\x00", value)
        return t

    def heading(self, text: str) -> str:
        """标题：允许行内代码，其余 markup 转义（处理 C# 里的 #、反引号标题）。"""
        tokens: list[str] = []
        t = CODE_RE.sub(
            lambda m: self.hold(tokens, f"#code({typst_string(m.group(1))})"),
            text,
        )
        t = markup_escape(t)
        for i, value in enumerate(tokens):
            t = t.replace(f"\x00{i}\x00", value)
        return t

    def convert(self, md_text: str, chapter_title: str | None = None,
                emit_import: bool = True, emit_chapter_title: bool = True) -> str:
        lines = md_text.splitlines()
        out: list[str] = []
        if emit_import:
            out += ['#import "../src/book.typ": *', ""]
        if chapter_title and emit_chapter_title:
            out += [f"= {self.heading(chapter_title)}", ""]

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
                cap = f", caption: [{render_cell(alt)}]" if alt else ", caption: none"
                out += [f'#fig(image({typst_string(path)}){cap})', ""]
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
                out += ["=" * level + " " + self.heading(m.group(2).strip()), ""]
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

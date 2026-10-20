#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assemble_book.py — 把写作工程 units/ 装配成可编译书稿（闭眼流水线）。

步骤：
  1. 读 02_outline.json，按章收集 units/<id>.md
  2. 用 md2typ 生成 chapters/chN.typ（文件名由章序号决定，可预测）
  3. 写/更新 config.toml 的 [[chapters]] 清单
  4. 可选 --compile：调用 techbook 的 nu build.nu book / typst

用法：
  python3 assemble_book.py books/how-to-write-a-tech-book
  python3 assemble_book.py books/my-book --engine techbook-typst --compile
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MD2TYP = ROOT / "techbook-typst" / "tools" / "md2typ.py"
DEFAULT_ENGINE = ROOT / "techbook-typst"


def chapter_filename(index: int) -> str:
    """闭眼约定：第 N 章 → chapters/chN.typ"""
    return f"ch{index}.typ"


def run_md2typ(sources: list[Path], title: str, out: Path) -> None:
    cmd = [sys.executable, str(MD2TYP), *[str(s) for s in sources],
           "--title", title, "-o", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"md2typ 失败：{r.stdout}\n{r.stderr}")


def update_config_chapters(config: Path, entries: list[tuple[str, str]]) -> None:
    """entries: [(path, note)]。保留 config 其余段，重写 [[chapters]]。"""
    text = config.read_text(encoding="utf-8") if config.is_file() else (
        '[doc]\ntitle = "Untitled"\nauthors = ["CodeBu"]\n\n[layout]\n'
    )
    lines = text.splitlines()
    out_lines: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == "[[chapters]]":
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith("[") and not s.startswith("[[chapters]]"):
                    break
                if s.startswith("[["):
                    break
                i += 1
            continue
        out_lines.append(lines[i])
        i += 1
    body = "\n".join(out_lines).rstrip() + "\n"
    blocks = []
    for p, n in entries:
        blocks.append(f'[[chapters]]\npath = "{p}"\nnote = "{n}"\n')
    config.write_text(body + "\n" + "\n".join(blocks), encoding="utf-8")


def write_preface(chapters_dir: Path, claim: str) -> Path:
    p = chapters_dir / "preface.typ"
    if p.is_file():
        return p
    claim = claim or "见正文各章承诺。"
    p.write_text(
        '#import "../src/book.typ": preface, tip, lead\n\n'
        "#preface(title: \"前言\")[\n\n"
        f"这本书承诺：{claim}\n\n"
        "#lead[写给谁]\n\n见 08_读者假设.md（请编者改写本段）。\n\n"
        "#tip[\n  本文件由 assemble_book.py 生成占位，请改写。\n]\n]\n",
        encoding="utf-8",
    )
    return p


def write_appendix(chapters_dir: Path) -> Path:
    p = chapters_dir / "appendix-a.typ"
    if p.is_file():
        return p
    p.write_text(
        '#import "../src/book.typ": *\n\n#appendix[速查]\n\n（占位：编者补充。）\n',
        encoding="utf-8",
    )
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir")
    ap.add_argument("--out", default="", help="chapters 输出目录（默认 <book>/chapters）")
    ap.add_argument("--engine", default=str(DEFAULT_ENGINE), help="techbook 引擎目录")
    ap.add_argument("--config", default="", help="config.toml 路径")
    ap.add_argument("--compile", action="store_true")
    ap.add_argument("--sync-handoff", action="store_true", help="同时跑 sync_handoff")
    a = ap.parse_args()

    book = Path(a.book_dir).resolve()
    outline_path = book / "02_outline.json"
    if not outline_path.is_file():
        raise SystemExit(f"错误：缺 {outline_path}")
    outline = json.loads(outline_path.read_text(encoding="utf-8"))
    meta = outline.get("book") or {}
    claim = meta.get("claim", "")

    out_dir = Path(a.out).resolve() if a.out else (book / "chapters")
    out_dir.mkdir(parents=True, exist_ok=True)

    write_preface(out_dir, claim)
    # 相对引擎根目录的 path 前缀
    engine = Path(a.engine).resolve()
    config = Path(a.config).resolve() if a.config else (engine / "config.toml")

    def to_config_path(p: Path) -> str:
        try:
            return p.relative_to(config.parent).as_posix()
        except ValueError:
            return str(p)

    entries: list[tuple[str, str]] = []
    entries.append((to_config_path(out_dir / "preface.typ"), "前言"))

    idx = 0
    for ch in outline.get("chapters") or []:
        sources = []
        for sec in ch.get("sections") or []:
            sid = sec.get("id") or ""
            md = book / "units" / f"{sid}.md"
            if md.is_file():
                sources.append(md)
            else:
                print(f"警告：缺单元正文 {md}", file=sys.stderr)
        idx += 1
        fname = chapter_filename(idx)
        out_typ = out_dir / fname
        if not sources:
            # 闭眼约定：无正文也出章骨架，保证能编译
            out_typ.write_text(
                f'#import "../src/book.typ": *\n\n= {ch.get("title", f"第{idx}章")}\n\n'
                f"（占位：units/ 尚无本章正文，写完后重新 assemble。）\n",
                encoding="utf-8",
            )
            print(f"stub {ch.get('id')} -> {fname}（无单元正文）")
        else:
            run_md2typ(sources, ch.get("title", f"第{idx}章"), out_typ)
            print(f"assembled {ch.get('id')} -> {fname} ({len(sources)} units)")
        entries.append((to_config_path(out_typ), f"第{idx}章 {ch.get('title', '')}"))

    write_appendix(out_dir)
    entries.append((to_config_path(out_dir / "appendix-a.typ"), "附录 速查"))

    # 仅当输出落在引擎 chapters/ 或显式 --config 时，才改 config.toml
    out_is_engine_ch = False
    try:
        out_is_engine_ch = out_dir.resolve() == (engine / "chapters").resolve()
    except Exception:
        out_is_engine_ch = False
    if a.config or out_is_engine_ch:
        update_config_chapters(config, entries)
        print(f"updated {config} ({len(entries)} chapter entries)")
    else:
        print(f"跳过 config.toml（out={out_dir} 不在引擎 chapters/；需要时加 --config）")
        # 仍写出清单便于人工挂载
        manifest = out_dir / "chapters.manifest"
        manifest.write_text(
            "\n".join(f"{p}\t{n}" for p, n in entries) + "\n", encoding="utf-8"
        )
        print(f"wrote {manifest}")

    if a.sync_handoff:
        sync = ROOT / "writing-rules" / "tools" / "sync_handoff.py"
        subprocess.run([sys.executable, str(sync), str(book)], check=False)

    if a.compile:
        if not engine.is_dir():
            raise SystemExit(f"错误：引擎目录不存在 {engine}")
        nu = shutil.which("nu")
        if nu and (engine / "build.nu").is_file():
            r = subprocess.run([nu, "build.nu", "book"], cwd=engine)
        else:
            typst = shutil.which("typst")
            if not typst:
                raise SystemExit("错误：未找到 nu 或 typst")
            r = subprocess.run(
                [typst, "compile", "--root", str(engine), "main.typ", "dist/book.pdf"],
                cwd=engine,
            )
        if r.returncode != 0:
            return r.returncode
        print(f"compiled {engine / 'dist' / 'book.pdf'}")

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())

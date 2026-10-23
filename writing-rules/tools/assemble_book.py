#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assemble_book.py — 把写作工程 units/ 装配成书内可编译的 Typst 工程。

默认（推荐）：
  books/<slug>/typst/
    main.typ          ← 从引擎复制，只装配
    config.toml       ← 由书目元数据 + chapters 生成
    src/              ← 引擎快照（首次复制，之后保留本地修改）
    chapters/chN.typ  ← 由 units/ 生成
    assets/           ← 图片等资源
    dist/book.pdf     ← --compile 产物

显式 --out 仍保留旧的“只输出 chapters”模式，用于兼容；
该模式不自动改引擎 config，也不自动 compile。

用法：
  python3 assemble_book.py books/my-book                 # 生成 books/my-book/typst/
  python3 assemble_book.py books/my-book --compile       # 再编译书内 PDF
  python3 assemble_book.py books/my-book --out /tmp/ch   # 兼容：只出 chapters
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MD2TYP = ROOT / "techbook-typst" / "tools" / "md2typ.py"
DEFAULT_ENGINE = ROOT / "techbook-typst"


def chapter_filename(index: int) -> str:
    """闭眼约定：第 N 章 → chapters/chN.typ"""
    return f"ch{index}.typ"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def run_md2typ(sources: list[Path], title: str, out: Path,
               asset_dir: Path | None = None) -> None:
    cmd = [sys.executable, str(MD2TYP), *[str(s) for s in sources],
           "--title", title, "-o", str(out)]
    if asset_dir is not None:
        cmd += ["--asset-dir", str(asset_dir)]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        raise SystemExit(f"md2typ 失败：{r.stdout}\n{r.stderr}")


def toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list) or isinstance(v, tuple):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    return json.dumps("" if v is None else str(v), ensure_ascii=False)


def load_toml(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def generate_config(config: Path, base: dict, doc: dict,
                    entries: list[tuple[str, str]]) -> None:
    """按已知段写 TOML；保留 base 的 layout/color/code/fonts 等标量段。"""
    lines: list[str] = []
    for section in ("doc", "layout", "color", "code", "fonts"):
        if section == "doc":
            data = doc
        else:
            data = base.get(section)
            if not isinstance(data, dict):
                continue
        lines.append(f"[{section}]")
        for k, v in data.items():
            if v is None:
                continue
            lines.append(f"{k} = {toml_value(v)}")
        lines.append("")
    for path, note in entries:
        lines.append("[[chapters]]")
        lines.append(f"path = {toml_value(path)}")
        lines.append(f"note = {toml_value(note)}")
        lines.append("")
    config.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def ensure_book_project(book: Path, engine: Path, typst_root: Path) -> None:
    """首次把引擎快照进书内；已有 src/ 不覆盖，保留本地修改。"""
    if not (typst_root / "src" / "book.typ").is_file():
        src_root = engine / "src"
        dst_root = typst_root / "src"
        dst_root.mkdir(parents=True, exist_ok=True)
        for name in ("book.typ", "theme.typ", "component.typ", "cover.typ", "toc.typ"):
            shutil.copy2(src_root / name, dst_root / name)
        for name in ("lib", "themes"):
            shutil.copytree(src_root / name, dst_root / name, dirs_exist_ok=True)
    for name in ("main.typ",):
        dst = typst_root / name
        if not dst.is_file() and (engine / name).is_file():
            shutil.copy2(engine / name, dst)
    for name in ("FONTS.md",):
        src = engine / name
        dst = typst_root / name
        if src.is_file() and not dst.is_file():
            shutil.copy2(src, dst)
    (typst_root / "chapters").mkdir(parents=True, exist_ok=True)
    (typst_root / "assets").mkdir(parents=True, exist_ok=True)
    (typst_root / "dist").mkdir(parents=True, exist_ok=True)


def update_config_chapters(config: Path, entries: list[tuple[str, str]]) -> None:
    """兼容旧模式：保留 config 其余段，只重写 [[chapters]]。"""
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
    blocks = [f'[[chapters]]\npath = "{p}"\nnote = "{n}"\n' for p, n in entries]
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


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir")
    ap.add_argument("--out", default="",
                    help="兼容：只输出 chapters 到该目录（不生成书内 typst 工程）")
    ap.add_argument("--engine", default=str(DEFAULT_ENGINE), help="techbook 引擎目录")
    ap.add_argument("--config", default="", help="显式 config.toml（兼容旧模式）")
    ap.add_argument("--compile", action="store_true")
    ap.add_argument("--allow-engine", action="store_true",
                    help="允许写进 techbook-typst/（仅维护样书时用）")
    ap.add_argument("--sync-handoff", action="store_true", help="同时跑 sync_handoff")
    a = ap.parse_args()

    book = Path(a.book_dir).resolve()
    engine = Path(a.engine).resolve()
    outline_path = book / "02_outline.json"
    if not outline_path.is_file():
        raise SystemExit(f"错误：缺 {outline_path}")
    if not (engine / "src" / "book.typ").is_file():
        raise SystemExit(f"错误：引擎目录不像 techbook：{engine}")

    outline = load_json(outline_path)
    meta = outline.get("book") or {}
    card = load_json(book / "01_立项卡.json")
    claim = meta.get("claim") or card.get("claim") or ""

    legacy = bool(a.out)
    if legacy:
        out_dir = Path(a.out).resolve()
        typst_root = None
        config = Path(a.config).resolve() if a.config else None
    else:
        typst_root = book / "typst"
        out_dir = typst_root / "chapters"
        config = Path(a.config).resolve() if a.config else typst_root / "config.toml"
        ensure_book_project(book, engine, typst_root)

    for p in (out_dir, config.parent if config else out_dir):
        if is_under(p, engine) and not a.allow_engine:
            raise SystemExit(
                f"错误：拒绝写入引擎目录 {p}。默认输出书内 typst/；"
                "维护样书请显式加 --allow-engine。"
            )
    out_dir.mkdir(parents=True, exist_ok=True)

    write_preface(out_dir, claim)

    def to_config_path(p: Path) -> str:
        if config is None:
            return p.as_posix()
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
            out_typ.write_text(
                f'#import "../src/book.typ": *\n\n= {ch.get("title", f"第{idx}章")}\n\n'
                f"（占位：units/ 尚无本章正文，写完后重新 assemble。）\n",
                encoding="utf-8",
            )
            print(f"stub {ch.get('id')} -> {fname}（无单元正文）")
        else:
            asset_dir = (typst_root / "assets") if typst_root else (out_dir.parent / "assets")
            run_md2typ(sources, ch.get("title", f"第{idx}章"), out_typ, asset_dir)
            print(f"assembled {ch.get('id')} -> {fname} ({len(sources)} units)")
        entries.append((to_config_path(out_typ), f"第{idx}章 {ch.get('title', '')}"))

    write_appendix(out_dir)
    entries.append((to_config_path(out_dir / "appendix-a.typ"), "附录 速查"))

    if legacy:
        if a.config and config:
            update_config_chapters(config, entries)
            print(f"updated {config} ({len(entries)} chapter entries)")
        else:
            manifest = out_dir / "chapters.manifest"
            manifest.write_text(
                "\n".join(f"{p}\t{n}" for p, n in entries) + "\n", encoding="utf-8"
            )
            print(f"跳过 config.toml（兼容模式）；清单 {manifest}")
    else:
        # 首次生成时不要继承样书的 subtitle/team/org/version/history；
        # 已有书内 config 才作为 base 保留作者的修改。
        if config.is_file():
            base = load_toml(config)
            old_doc = dict(base.get("doc") or {})
        else:
            base = load_toml(engine / "config.toml")
            old_doc = {}
        doc = dict(old_doc)
        doc["title"] = card.get("title") or meta.get("title") or book.name
        doc["subtitle"] = card.get("subtitle") or old_doc.get("subtitle") or ""
        authors = card.get("authors") or old_doc.get("authors") or ["CodeBu"]
        doc["authors"] = [authors] if isinstance(authors, str) else authors
        doc["team"] = card.get("team") or old_doc.get("team") or ""
        doc["org"] = card.get("org") or old_doc.get("org") or ""
        doc["abstract"] = card.get("abstract") or claim or old_doc.get("abstract") or ""
        doc["version"] = card.get("version") or old_doc.get("version") or "v0.1"
        doc["date"] = card.get("date") or old_doc.get("date") or date.today().isoformat()
        doc["category"] = card.get("category") or old_doc.get("category") or "技术写作"
        doc["keywords"] = card.get("keywords") or old_doc.get("keywords") or []
        if not doc.get("history"):
            doc["history"] = [[doc["version"], doc["date"], "初稿", "CodeBu"]]
        generate_config(config, base, doc, entries)
        print(f"updated {config} ({len(entries)} chapter entries)")

    if a.sync_handoff:
        sync = ROOT / "writing-rules" / "tools" / "sync_handoff.py"
        subprocess.run([sys.executable, str(sync), str(book)], check=False)

    if a.compile:
        if legacy:
            raise SystemExit("错误：兼容 --out 模式不自动 compile；请省略 --out 生成书内 typst/")
        typst = shutil.which("typst")
        if not typst:
            raise SystemExit("错误：未找到 typst（书内 typst/ 需要 typst compile）")
        r = subprocess.run(
            [typst, "compile", "--root", str(typst_root), "main.typ", "dist/book.pdf"],
            cwd=typst_root,
        )
        if r.returncode != 0:
            return r.returncode
        print(f"compiled {typst_root / 'dist' / 'book.pdf'}")

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())

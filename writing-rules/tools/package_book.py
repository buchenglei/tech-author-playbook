#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""package_book.py — 打包干净的 tar.gz 交付物。

包内结构：
  README.md  MANIFEST.txt  book.pdf
  typst/     （可编译工程：main.typ / config.toml / chapters/ / src/ …）
  manuscript/（写作工程：01–08、units、台账术表）
  handoff/   （交接包六文件）
  workflow/  （报告与宪法，不含 archive/）

排除：日志、archive、DS_Store、pycache、draft-/tmp-/ *.bak、smoke 产物等。

用法：
  python3 package_book.py books/my-book --engine techbook-typst
  python3 package_book.py books/my-book --engine techbook-typst --out dist/my-book.tar.gz
  python3 package_book.py books/my-book --engine techbook-typst --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXCLUDE_NAMES = {
    ".DS_Store", "Thumbs.db", ".git", "__pycache__", ".venv", ".idea", ".vscode",
    ".mimocode", ".claude", "smoke.pdf",
}
EXCLUDE_SUFFIX = (".log", ".err", ".tmp", ".bak", ".swp", ".pyc")
EXCLUDE_PREFIX = ("draft-", "tmp-", "old-", "_")
EXCLUDE_DIRS = {"archive", "dist", ".git", "__pycache__"}


def want(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    parts = rel.parts
    for p in parts:
        if p in EXCLUDE_NAMES or p in EXCLUDE_DIRS:
            return False
        if p.startswith(EXCLUDE_PREFIX) and p not in ("01_立项卡.json",):
            # 允许 01_… 编号文件；挡 draft- tmp- old- _demo
            if p.startswith(("draft-", "tmp-", "old-", "_")):
                return False
    if path.name in EXCLUDE_NAMES:
        return False
    if path.name.endswith(EXCLUDE_SUFFIX):
        return False
    if path.name.startswith(("draft-", "tmp-", "old-")):
        return False
    return True


def copy_tree(src: Path, dest: Path, dry: bool) -> list[str]:
    added = []
    if not src.is_dir():
        return added
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        if not want(p, src):
            continue
        rel = p.relative_to(src)
        out = dest / rel
        added.append(str(Path(dest.name) / rel))
        if not dry:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(p.read_bytes())
    return added


def gen_readme(book_title: str, slug: str) -> str:
    return f"""# 交付说明 · {book_title}

本包为技术书交付物（tar.gz 解压后目录）。含**可编译 Typst 源码**、**PDF**、**写作工程**与**评审反馈**，便于人工继续修改。

## 包内结构

| 路径 | 用途 |
| --- | --- |
| `book.pdf` | 当前成品，先读这个 |
| `typst/` | 排版工程（改样式/章节最终形态） |
| `manuscript/` | 写作工程（大纲、单元 spec/正文、台账、术表） |
| `handoff/` | 交接包（结构、术语、断言、校验、未验证项） |
| `workflow/` | 读者/编辑报告、改进方案、写作宪法 |
| `MANIFEST.txt` | 文件清单与版本 |

## 如何从源码编译 PDF

```bash
cd typst
typst compile --root . main.typ dist/book.pdf
```

依赖：Typst 0.15+。字体见 `typst/FONTS.md`（缺字会告警并回退）。若含 `build.nu` 也可用 `nu build.nu book`。

## 如何修改

1. **改内容**：`manuscript/units/*.md` 为内容真源；改后同步 `typst/chapters/chN.typ`（或用写作线 `assemble_book`，见仓库 tech-author-playbook）。
2. **改版式**：`typst/src/` 与 `typst/config.toml`；章节内勿写 `#set page/text/par`。
3. **改事实与来源**：`manuscript/04_ledger.csv` + 对应单元；推断句须带「推断/未实测」。
4. **反馈**：填入 `workflow/` 下读者报告 / 编辑审校 / 写作宪法，勿只口头修改。

## 真源约定

- 内容：`manuscript/units/`
- 成书排版：`typst/chapters/` 与 `typst/src/`
- 交付状态与未验证：`handoff/05_unverified.md`（不得为空）

## 编译产物

PDF 生成于 `typst/dist/book.pdf`；包内 `book.pdf` 为打包时快照，改稿后请重编并替换。
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir")
    ap.add_argument("--engine", default=str(ROOT / "techbook-typst"))
    ap.add_argument("--out", default="", help="输出 tar.gz 路径")
    ap.add_argument("--pdf", default="", help="PDF 路径（默认 engine/dist/book.pdf）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    book = Path(a.book_dir).resolve()
    engine = Path(a.engine).resolve()
    if not book.is_dir():
        raise SystemExit(f"书稿目录不存在: {book}")
    if not engine.is_dir():
        raise SystemExit(f"引擎目录不存在: {engine}")

    slug = book.name
    title = slug
    card = book / "01_立项卡.json"
    if card.is_file():
        try:
            title = json.loads(card.read_text(encoding="utf-8")).get("title") or slug
        except Exception:
            pass

    pdf = Path(a.pdf).resolve() if a.pdf else (engine / "dist" / "book.pdf")
    out = Path(a.out).resolve() if a.out else (ROOT / "dist" / f"{slug}-delivery.tar.gz")

    files: list[tuple[str, bytes]] = []

    def add_bytes(arc: str, data: bytes):
        files.append((arc, data))

    add_bytes("README.md", gen_readme(title, slug).encode("utf-8"))

    # typst 工程
    n_typst = 0
    if engine.is_dir():
        for p in sorted(engine.rglob("*")):
            if not p.is_file() or not want(p, engine):
                continue
            rel = p.relative_to(engine)
            # 不要引擎里的 dist 产物（PDF 另放根）
            if rel.parts and rel.parts[0] == "dist":
                continue
            add_bytes(f"typst/{rel.as_posix()}", p.read_bytes())
            n_typst += 1

    # manuscript：排除 workflow/handoff（下面单独放，避免双份）
    n_manu = 0
    for p in sorted(book.rglob("*")):
        if not p.is_file() or not want(p, book):
            continue
        rel = p.relative_to(book)
        top = rel.parts[0] if rel.parts else ""
        if top in ("handoff", "workflow", "chapters"):
            continue
        add_bytes(f"manuscript/{rel.as_posix()}", p.read_bytes())
        n_manu += 1

    # handoff / workflow
    for folder, arc in (("handoff", "handoff"), ("workflow", "workflow")):
        src = book / folder
        if not src.is_dir():
            continue
        for p in sorted(src.rglob("*")):
            if not p.is_file() or not want(p, src):
                continue
            rel = p.relative_to(src)
            # workflow 只保留报告模板产物，丢 memory 缓存
            if folder == "workflow" and rel.parts and rel.parts[0] == "memory" and p.name != "CURRENT.md":
                continue
            add_bytes(f"{arc}/{rel.as_posix()}", p.read_bytes())

    # PDF
    if pdf.is_file():
        add_bytes("book.pdf", pdf.read_bytes())
    else:
        print(f"警告：未找到 PDF {pdf}（包内将无 book.pdf）")

    manifest = [
        f"package: {slug}-delivery",
        f"title: {title}",
        f"date: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"typst_files: {n_typst}",
        f"manuscript_files: {n_manu}",
        f"total_files: {len(files) + 1}",
        "rebuild: cd typst && typst compile --root . main.typ dist/book.pdf",
        "",
        "files:",
    ]
    manifest.extend(f"  {name}" for name, _ in sorted(files))
    add_bytes("MANIFEST.txt", ("\n".join(manifest) + "\n").encode("utf-8"))

    if a.dry_run:
        print(f"dry-run {out} ({len(files)} files)")
        for name, _ in files:
            print(" ", name)
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, "w:gz") as tar:
        for name, data in files:
            info = tarfile.TarInfo(name=f"{slug}/{name}")
            info.size = len(data)
            info.mtime = int(dt.datetime.now().timestamp())
            tar.addfile(info, io.BytesIO(data))
    print(f"wrote {out} ({len(files)} files, {out.stat().st_size} bytes)")
    print("自检：解压后读 README.md；用 typst 编译验证。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
import re
import subprocess
import sys
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


def gen_readme(meta: dict, outline: dict, slug: str) -> str:
    title = meta.get("title") or slug
    claim = meta.get("claim") or ""
    abstract = meta.get("abstract") or claim
    subtitle = meta.get("subtitle") or ""
    authors = meta.get("authors") or "CodeBu"
    if isinstance(authors, list):
        authors = " / ".join(str(x) for x in authors)
    reader_before = meta.get("reader_before") or ""
    reader_after = meta.get("reader_after") or []
    if isinstance(reader_after, str):
        reader_after = [reader_after]
    chapters = []
    for ch in (outline.get("chapters") or []):
        chapters.append(f"- **{ch.get('id', '')} {ch.get('title', '')}** — {ch.get('purpose', '')}")
    toc = "\n".join(chapters) or "（见 `manuscript/02_outline.json`）"

    about_more = ""
    if meta.get("increment_note"):
        about_more += "\n**增量**（" + str(meta.get("increment", "")) + "）：" + str(meta.get("increment_note")) + "\n"
    if reader_before:
        about_more += "\n**适合谁**：" + reader_before + "\n"
    if reader_after:
        about_more += "\n**读完你能**：\n" + "\n".join("- " + x for x in reader_after) + "\n"

    promise = ""
    if claim and claim != abstract:
        promise = "\n## 本书承诺\n\n" + claim + "\n"

    sub_line = ("\n> " + subtitle + "\n") if subtitle else ""

    return (
        "# " + title + "\n"
        + sub_line + "\n"
        + abstract + "\n"
        + promise + about_more
        + "\n## 目录\n\n" + toc + "\n"
        + """
## 快速开始

- **先读书**：[`book.pdf`](book.pdf)（打包时编译产物）
- **只改文字**：改 [`manuscript/units/`](manuscript/units/) 后同步章节源码
- **改版式 / 重编 PDF**：

```bash
cd typst
typst compile --root . main.typ dist/book.pdf
```

依赖 [Typst](https://typst.app) 0.15+。字体说明见 [`typst/FONTS.md`](typst/FONTS.md)。

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| `book.pdf` | 成品 PDF |
| `typst/` | 可编译 Typst 工程（章节、引擎、配置） |
| `manuscript/` | 写作工程：立项、大纲、单元、台账、术语 |
| `handoff/` | 交接包：结构、术语、断言账本、校验、未验证项 |
| `workflow/` | 读者 / 编辑评审与写作宪法 |
| `MANIFEST.txt` | 打包文件清单 |
| `LICENSE` | 许可证（MIT） |

## 从源码到产物

1. 安装 Typst 0.15+
2. `cd typst && typst compile --root . main.typ dist/book.pdf`
3. 可选：改 `typst/config.toml`（书名、开本、字体），改 `typst/chapters/*.typ`（正文排版形态）
4. 内容与事实以 `manuscript/` 为准；数字与出处见 `manuscript/04_ledger.csv`，未验证项见 `handoff/05_unverified.md`

## 给贡献者 / 评审

- 反馈请落在 `workflow/`（读者报告、编辑审校、写作宪法修订）
- 不要只交口头意见；改动尽量带位置（章节 / 原句）
- 本书宣称的验证边界以 `handoff/05_unverified.md` 为准

## License

MIT © """ + authors + """。排版引擎与正文同仓库分发，保留本 `LICENSE` 即可再分发。

---

*本包由 tech-author-playbook 写书工作流生成（离线使用以包内文件为准）。*
"""
    )


def main() -> int:
    # 错误消息经 SystemExit 打到 stderr；GBK 控制台会按本地编码写导致下游解析乱码
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir")
    ap.add_argument("--engine", default=str(ROOT / "techbook-typst"))
    ap.add_argument("--out", default="", help="输出 tar.gz 路径")
    ap.add_argument("--pdf", default="", help="PDF 路径（默认书内 typst/dist/book.pdf，其次 engine/dist）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-name", action="store_true",
                    help="允许在人终审未签字时用「终版/final/ready」命名（自行承担）")
    ap.add_argument("--skip-quality", action="store_true",
                    help="跳过 validate_quality（交付说明须标 draft）")
    a = ap.parse_args()

    book = Path(a.book_dir).resolve()
    engine = Path(a.engine).resolve()
    if not book.is_dir():
        raise SystemExit(f"书稿目录不存在: {book}")
    if not engine.is_dir():
        raise SystemExit(f"引擎目录不存在: {engine}")

    slug = book.name
    meta: dict = {"title": slug, "authors": "CodeBu"}
    card = book / "01_立项卡.json"
    if card.is_file():
        try:
            meta.update(json.loads(card.read_text(encoding="utf-8")))
        except Exception:
            pass
    outline: dict = {}
    op = book / "02_outline.json"
    if op.is_file():
        try:
            outline = json.loads(op.read_text(encoding="utf-8"))
        except Exception:
            pass
    # 优先使用书内 typst/（assemble_book 默认产物）；否则回退引擎样书
    book_typst = book / "typst"
    typst_src = book_typst if (book_typst / "main.typ").is_file() else engine
    # config 摘要可作书籍介绍补充
    cfgp = typst_src / "config.toml"
    if cfgp.is_file() and not meta.get("abstract"):
        cfg_text = cfgp.read_text(encoding="utf-8")
        m = re.search(r'abstract\s*=\s*"([^"]*)"', cfg_text)
        if m:
            meta["abstract"] = m.group(1)
        m2 = re.search(r'subtitle\s*=\s*"([^"]*)"', cfg_text)
        if m2:
            meta["subtitle"] = m2.group(1)
    if meta.get("title") == slug and outline.get("book", {}).get("title"):
        meta["title"] = outline["book"]["title"]

    pdf = Path(a.pdf).resolve() if a.pdf else (typst_src / "dist" / "book.pdf")

    # 交付状态：final 人签字前一律 draft；「终版/final/ready」命名受护栏约束
    wf_state = book / "workflow" / "00_阶段状态.json"
    if not wf_state.is_file():
        wf_state = book / "manuscript" / "workflow" / "00_阶段状态.json"
    final_signed = False
    try:
        final_signed = bool(json.loads(wf_state.read_text(encoding="utf-8-sig"))
                            .get("human_confirmations", {}).get("final", {}).get("confirmed"))
    except Exception:
        pass
    delivery_status = "ready" if final_signed else "draft"
    out = Path(a.out).resolve() if a.out else (ROOT / "dist" / f"{slug}-delivery.tar.gz")
    if re.search(r"(终版|final|ready)", out.name, re.I) and delivery_status != "ready" \
            and not a.force_name:
        raise SystemExit(
            f"错误：{out.name} 含「终版/final/ready」，但人终审未签字（{wf_state}）。"
            "内容第一：请改名 draft，或 --force-name 显式承担。")

    files: list[tuple[str, bytes]] = []

    def add_bytes(arc: str, data: bytes):
        files.append((arc, data))

    add_bytes("README.md",
              (f"> 交付状态：**{delivery_status}**"
               + ("" if delivery_status == "ready" else "（人终审未签字；不得称终版/ready）")
               + "\n\n" + gen_readme(meta, outline, slug)).encode("utf-8"))
    lic = ROOT / "LICENSE"
    if lic.is_file():
        add_bytes("LICENSE", lic.read_bytes())

    # typst 工程（优先书内；不含 dist 产物）
    n_typst = 0
    if typst_src.is_dir():
        for p in sorted(typst_src.rglob("*")):
            if not p.is_file() or not want(p, typst_src):
                continue
            rel = p.relative_to(typst_src)
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
        if top in ("handoff", "workflow", "chapters", "typst"):
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
        f"title: {meta.get('title', slug)}",
        f"delivery_status: {delivery_status}",
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

    # 交付前质量验收（内容第一：体量、报告非空、过程一致）
    vq = ROOT / "writing-rules" / "tools" / "validate_quality.py"
    if vq.is_file() and not a.skip_quality:
        rr = subprocess.run([sys.executable, str(vq), str(book)], capture_output=True)
        out_txt = (rr.stdout or b"").decode("utf-8", errors="replace")
        print(out_txt)
        if rr.returncode == 2:
            print("交付被质量门禁拦截：请补体量/报告/过程状态，或显式 --skip-quality（须在交付说明声明 draft）")
            return 2

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

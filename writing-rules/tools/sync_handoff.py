#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_handoff.py — 把书稿工程源文件同步进 handoff/ 交接包。

拷贝关系（S7 六文件）：
  02_outline.json   ← <book>/02_outline.json
  02_glossary.json  ← <book>/06_glossary.json
  03_ledger.csv     ← <book>/04_ledger.csv
  04_check.json     ← 保留既有文件；若无则提示先跑校验
  00_README.md / 05_unverified.md 为交接叙述，不覆盖

同步后在 00_README.md 追加/更新「最近同步」时间戳（拷贝时间点）。

用法：
  python3 sync_handoff.py <book_dir>
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

COPIES = {
    "02_outline.json": "02_outline.json",
    "06_glossary.json": "02_glossary.json",
    "04_ledger.csv": "03_ledger.csv",
}
STAMP_RE = re.compile(r"^> 最近同步：.*$", re.M)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir", help="书稿工程目录（含 02_outline.json 等）")
    a = ap.parse_args()
    book = Path(a.book_dir).resolve()
    if not book.is_dir():
        print(f"错误：不是目录 {book}", file=sys.stderr)
        return 2
    handoff = book / "handoff"
    handoff.mkdir(exist_ok=True)

    for src_name, dst_name in COPIES.items():
        src = book / src_name
        dst = handoff / dst_name
        if not src.is_file():
            print(f"错误：缺源文件 {src}", file=sys.stderr)
            return 2
        shutil.copy2(src, dst)
        print(f"copied {src_name} -> handoff/{dst_name}")

    check = handoff / "04_check.json"
    if not check.is_file():
        print("警告：handoff/04_check.json 不存在，请先跑校验并写入 04_check.json")

    readme = handoff / "00_README.md"
    stamp_line = f"> 最近同步：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}（拷贝时间点，由 sync_handoff.py 写入）"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        if STAMP_RE.search(text):
            text = STAMP_RE.sub(stamp_line, text, count=1)
        else:
            text = text.rstrip() + "\n\n" + stamp_line + "\n"
        readme.write_text(text, encoding="utf-8")
        print(f"stamped handoff/00_README.md")
    else:
        print("警告：缺 handoff/00_README.md，未写同步时间戳")

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())

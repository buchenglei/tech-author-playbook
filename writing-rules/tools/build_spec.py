#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_spec.py — 按序拼接 writing-rules/spec/*.md，供 lint/registry 与单页阅读。

规则正文以 spec/ 分片为单一真源；本脚本只做拼接，不改内容。
用法：
  python3 build_spec.py            # 打印到 stdout
  python3 build_spec.py --write /tmp/技术书籍写作规范_v1.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ORDER = [
    "00-overview.md",
    "01-作者身份与执行契约.md",
    "02-立项.md",
    "03-读者.md",
    "04-全书结构.md",
    "05-写作单元.md",
    "06-主题三族.md",
    "07-语言与风格.md",
    "08-校验.md",
    "09-书稿工程.md",
    "10-交接.md",
    "A-规则总表.md",
    "B-模板索引.md",
    "C-门禁速查.md",
    "D-故障处置.md",
    "E-三族速查.md",
    "F-待校准项.md",
    "G-术语表.md",
    "H-文风样例.md",
]


def load_spec_dir(spec_dir: Path) -> str:
    parts = []
    for name in ORDER:
        p = spec_dir / name
        if not p.is_file():
            raise SystemExit(f"缺少 {p}")
        parts.append(p.read_text(encoding="utf-8").rstrip() + "\n")
    return "\n".join(parts) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", metavar="PATH", help="写入拼接结果")
    ap.add_argument("--spec-dir", default="", help="spec 目录（默认：本文件上级/spec）")
    a = ap.parse_args()
    spec_dir = Path(a.spec_dir) if a.spec_dir else Path(__file__).resolve().parents[1] / "spec"
    text = load_spec_dir(spec_dir)
    if a.write:
        Path(a.write).write_text(text, encoding="utf-8")
        print(f"wrote {a.write} ({len(text)} bytes)", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

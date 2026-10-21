#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_tests.py — writing-rules / 工具链回归测试（无第三方依赖）。

覆盖 PROBLEMS.md 中已修缺陷与门禁行为，防止回退。
用法：python3 run_tests.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LINT = ROOT / "writing-rules" / "tools" / "spec_lint.py"
MD2TYP = ROOT / "techbook-typst" / "tools" / "md2typ.py"
SYNC = ROOT / "writing-rules" / "tools" / "sync_handoff.py"
BOOK = ROOT / "books" / "how-to-write-a-tech-book"

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def run(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def lint_json(path: Path, profile="manuscript"):
    r = run([sys.executable, str(LINT), str(path), "--profile", profile, "--json"])
    try:
        return json.loads(r.stdout), r.returncode
    except Exception:
        return {"_raw": r.stdout + r.stderr, "P0": [], "P1": [], "P2": []}, r.returncode


def gate(which: str, base: Path):
    r = run([sys.executable, str(LINT), "--gate", which, str(base)])
    return r.returncode, r.stdout


def main() -> int:
    print("== spec_lint 回归 ==")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # P1：check_claims 解包不得崩溃（曾因 paragraphs 三元组炸）
        f = td / "claims.md"
        f.write_text("# t\n\n句子提到 1200 ms 延迟与 3.5 GB 内存。\n", encoding="utf-8")
        data, code = lint_json(f)
        check("check_claims 不崩溃且报数字", "P0" in data and any(
            "L-CLAIM-01" in i.get("rule_id", "") for i in data.get("P0", [])), str(data)[:200])

        # P4：manuscript 引用规范规则 ID 不得误报
        f2 = td / "ref.md"
        f2.write_text("# t\n\n见 TOP-01 与 TEAM-04。\n\n段落一句。\n", encoding="utf-8")
        data, _ = lint_json(f2)
        p0ids = [i.get("rule_id") for i in data.get("P0", [])]
        check("manuscript 不报 S-RULE-01", "S-RULE-01" not in p0ids, str(p0ids))

        # L-FORM-01：禁止认知链挂牌标题
        f4 = td / "label.md"
        f4.write_text("# t\n\n## 现象：挂钩\n\n正文一句。\n", encoding="utf-8")
        data, _ = lint_json(f4)
        check("L-FORM-01 禁挂牌标题", any(i.get("rule_id") == "L-FORM-01" for i in data.get("P0", [])), str(data)[:200])

        # L-FORM-02：每节表格上限
        tables = "\n\n".join(f"| a | b |\n| 1 | 2 |\n" for _ in range(3))
        f5 = td / "tables.md"
        f5.write_text(f"# t\n\n## 小节\n\n{tables}\n", encoding="utf-8")
        data, _ = lint_json(f5)
        check("L-FORM-02 表格上限", any(i.get("rule_id") == "L-FORM-02" for i in data.get("P0", [])), str(data)[:200])

        # 禁用词仍应拦截
        f3 = td / "bad.md"
        f3.write_text("# t\n\n这很重要，务必注意。\n", encoding="utf-8")
        data, _ = lint_json(f3)
        check("禁用词 L-LANG-01", any(i.get("rule_id") == "L-LANG-01" for i in data.get("P0", [])))

        # G0：repo: URL 合法
        proj = td / "proj"
        proj.mkdir()
        card = {
            "title": "T", "claim": "在某条件下机制导致某结果，反例是 X",
            "increment": "判断", "reader_before": "a", "reader_after": ["b"],
            "scope_in": ["x"], "scope_out": [{"item": "y", "reason": "z"}] * 3,
            "prerequisites": [{"item": "p", "fallback": "f"}],
            "sources": [
                {"title": "S1", "url": "repo:writing-rules/spec/01.md", "version": "1", "locator": "§1", "type": "E1"},
                {"title": "S2", "url": "https://example.com/a", "version": "1", "locator": "§2", "type": "E1"},
                {"title": "S3", "url": "repo:writing-rules/spec/02.md", "version": "1", "locator": "§3", "type": "E1"},
            ],
            "risk": [{"item": "r", "review_by": "2027-01"}],
            "kill_criteria": ["k1", "k2"], "family": "C",
        }
        (proj / "01_立项卡.json").write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
        code, out = gate("G0", proj)
        check("G0 接受 repo: 与 https", code == 0, out)
        card["sources"][0]["url"] = "https://example.com/external"
        # 写死平台地址也不该在示例中出现；G0 本身只校验非空——见 CONTRIBUTING 约定
        (proj / "01_立项卡.json").write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
        code, out = gate("G0", proj)
        check("G0 仍可过（https）", code == 0, out)

        # G2：bridge 空应报
        outline = {
            "book": {"title": "T", "type": "实战书", "claim": "x y z w a b", "target_words": 30000, "family": "C"},
            "chapters": [{
                "id": "C01", "title": "c", "purpose": "p", "produces": "o",
                "role": {"phenomenon": "C01-S1", "mechanism": "C01-S2", "cost": "C01-S3"},
                "sections": [
                    {"id": "C01-S1", "title": "s1", "question": "q", "produces": "p", "bridge": "", "layer": "现象", "deps": [], "status": "planned"},
                    {"id": "C01-S2", "title": "s2", "question": "q", "produces": "p", "bridge": "b", "layer": "机制", "deps": ["C01-S1"], "status": "planned"},
                    {"id": "C01-S3", "title": "s3", "question": "q", "produces": "p", "bridge": "b?", "layer": "代价", "deps": ["C01-S2"], "status": "planned"},
                ],
            }],
            "paths": [{"name": "linear", "order": ["C01"]}],
        }
        (proj / "02_outline.json").write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8")
        code, out = gate("G2", proj)
        check("G2 空 bridge 报 STR-06", "STR-06" in out and "bridge" in out, out)

        # G3：扫 units/ 全部而非第一个
        units = proj / "units"
        units.mkdir()
        (units / "B-last.md").write_text("# t\n\n重要\n", encoding="utf-8")  # 应被扫到
        (units / "A-first.md").write_text("# t\n\n好的句子。\n", encoding="utf-8")
        code, out = gate("G3", proj)
        check("G3 扫描多个 unit", "重要" in out or "L-LANG-01" in out, out)

        # G6：handoff/ 回落
        (proj / "handoff").mkdir()
        for name, body in [
            ("00_README.md", "# r\n"),
            ("01_outline.json", "{}"),
            ("02_glossary.json", "{}"),
            ("03_ledger.csv", "id\n"),
            ("04_check.json", "{}"),
            ("05_unverified.md", "未验证项说明：" + "内容够长，" * 30),
        ]:
            (proj / "handoff" / name).write_text(body, encoding="utf-8")
        code, out = gate("G6", proj)
        check("G6 找 handoff/", code == 0, out)

    print("== md2typ ==")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "u.md"
        src.write_text(
            "# 节标题\n\n正文 **粗体** 与 `code`。\n\n"
            "| A | B |\n| --- | --- |\n| # | 2 |\n\n"
            "```text\nhi\n```\n",
            encoding="utf-8",
        )
        out = td / "ch.typ"
        r = run([sys.executable, str(MD2TYP), str(src), "--title", "章", "-o", str(out)])
        text = out.read_text(encoding="utf-8") if out.is_file() else ""
        check("md2typ 生成", r.returncode == 0 and "= 章" in text and "== 节标题" in text, r.stdout + r.stderr)
        check("md2typ 转义表格 #", "\\#" in text or "[\\#]" in text or "header: ([\\#]" in text, text[:500])
        check("md2typ code 组件", "#code[code]" in text, text)

    print("== sync_handoff ==")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        b = td / "b"
        (b / "handoff").mkdir(parents=True)
        (b / "02_outline.json").write_text("{}", encoding="utf-8")
        (b / "06_glossary.json").write_text("{}", encoding="utf-8")
        (b / "04_ledger.csv").write_text("id\n", encoding="utf-8")
        (b / "handoff" / "00_README.md").write_text("# r\n", encoding="utf-8")
        r = run([sys.executable, str(SYNC), str(b)])
        st = (b / "handoff" / "00_README.md").read_text(encoding="utf-8")
        check("sync_handoff 拷贝并打戳", r.returncode == 0 and "最近同步" in st and (b / "handoff" / "01_outline.json").is_file(), r.stdout + r.stderr)

    print("== init_book / assemble_book ==")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        init = ROOT / "writing-rules" / "tools" / "init_book.py"
        asm = ROOT / "writing-rules" / "tools" / "assemble_book.py"
        r = run([sys.executable, str(init), "t-book", "--title", "T", "--claim",
                 "在条件 C 下机制 M 导致 R，反例是 X", "--dest", str(td)])
        b = td / "t-book"
        check("init_book 生成标准文件", r.returncode == 0 and (b / "02_outline.json").is_file()
              and (b / "units").is_dir() and (b / "handoff").is_dir(), r.stdout + r.stderr)
        code, out = gate("G0", b)
        check("init_book 后 G0 可过", code == 0, out)
        r = run([sys.executable, str(asm), str(b), "--engine", str(ROOT / "techbook-typst"),
                 "--out", str(b / "chapters")])
        check("assemble 出 chapters", r.returncode == 0 and (b / "chapters" / "ch1.typ").is_file()
              and (b / "chapters" / "preface.typ").is_file(), r.stdout + r.stderr)
        check("assemble 不乱写引擎 config", (b / "chapters" / "chapters.manifest").is_file()
              or "跳过 config" in r.stdout, r.stdout)

    print("== 金样板 smoke ==")
    if BOOK.is_dir():
        for g in ("G0", "G1", "G2", "G3", "G5", "G6"):
            code, out = gate(g, BOOK)
            check(f"金样板 {g}", code == 0, out.splitlines()[0] if out else "")
    else:
        check("金样板目录存在", False, str(BOOK))

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

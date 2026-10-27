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
sys.path.insert(0, str(ROOT / "writing-rules" / "tools"))
import quality_gate  # noqa: E402

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


class Result:
    """subprocess 结果的轻量包装：统一按 UTF-8 解码，避免 GBK 控制台误伤。"""

    def __init__(self, rr):
        self.returncode = rr.returncode
        self.stdout = rr.stdout.decode("utf-8", errors="replace") if rr.stdout else ""
        self.stderr = rr.stderr.decode("utf-8", errors="replace") if rr.stderr else ""


def run(cmd, cwd=None):
    return Result(subprocess.run(cmd, capture_output=True, cwd=cwd))


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
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
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

        # 绕过口收紧：段内有 E- 但句子内无 E- 的数字仍要报（不再整段免检）
        f6 = td / "bypass.md"
        f6.write_text(
            "# t\n\n"
            "本段有锚 E-001 说明某事。\n\n"
            "另一句给出 3000 ms 延迟与 99.99% 可用性，这句自己没有台账。\n",
            encoding="utf-8")
        data, _ = lint_json(f6)
        check("check_claims 逐句核对（E- 不免整段）",
              any(i.get("rule_id") == "L-CLAIM-01" for i in data.get("P0", [])),
              str(data)[:300])

        # 同句有 E- 则放行
        f7 = td / "okclaim.md"
        f7.write_text("# t\n\n延迟 3000 ms（E-001）已实测。\n", encoding="utf-8")
        data, _ = lint_json(f7)
        check("check_claims 同句 E- 放行",
              not any(i.get("rule_id") == "L-CLAIM-01" for i in data.get("P0", [])),
              str(data)[:200])

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
        check("L-FORM-02 表格提示(P2)", any(i.get("rule_id") == "L-FORM-02" for i in data.get("P2", [])), str(data)[:200])

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

        # 图 / 链接 / 引用 / 表注 / 资源复制
        (td / "fig").mkdir()
        (td / "fig" / "a.png").write_bytes(b"x")
        src.write_text(
            "# 图节\n\n![架构](fig/a.png)\n\n"
            "[链接](https://typst.app)\n\n> 引用一行\n\n"
            "| A | B |\n| --- | --- |\n| 1 | 2 |\n\n"
            "<!-- caption: 对照表 -->\n",
            encoding="utf-8",
        )
        out2 = td / "out" / "ch.typ"
        asset = td / "out" / "assets"
        r = run([sys.executable, str(MD2TYP), str(src), "--title", "章", "-o", str(out2),
                 "--asset-dir", str(asset)])
        text2 = out2.read_text(encoding="utf-8") if out2.is_file() else ""
        check("md2typ 图片转 #fig", '#fig(image("assets/u/a.png"' in text2
              and (asset / "u" / "a.png").is_file(), text2[:500] + r.stdout + r.stderr)
        check("md2typ 链接转 #link", '#link("https://typst.app")[链接]' in text2, text2[:500])
        check("md2typ 引用转 #quote", "#quote[" in text2 and "引用一行" in text2, text2[:500])
        check("md2typ 表注取 caption", "caption: [对照表]" in text2, text2[:500])

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
        check("init_book 生成大纲合同", (b / "workflow" / "00_大纲合同.json").is_file(), "")
        check("init_book 生成 workflow", (b / "workflow" / "00_阶段状态.json").is_file()
              and (b / "workflow" / "04_写作宪法.md").is_file()
              and (b / "workflow" / "01_读者报告.md").is_file()
              and (b / "workflow" / "06_终审").is_dir(), r.stdout + r.stderr)
        card = json.loads((b / "01_立项卡.json").read_text(encoding="utf-8"))
        outline = json.loads((b / "02_outline.json").read_text(encoding="utf-8"))
        check("init_book family 同源", card.get("family") == outline["book"].get("family"),
              f"{card.get('family')} vs {outline['book'].get('family')}")
        # new_unit 预填
        nu = ROOT / "writing-rules" / "tools" / "new_unit.py"
        r = run([sys.executable, str(nu), str(b), "C01-S1"])
        spec = b / "units" / "C01-S1.spec.md"
        check("new_unit 预填 spec", r.returncode == 0 and spec.is_file()
              and "C01-S1" in spec.read_text(encoding="utf-8"), r.stdout + r.stderr)
        # run_gates 紧凑：脚手架含占位时 G0 必须红（不得假绿）
        rg = ROOT / "writing-rules" / "tools" / "run_gates.py"
        r = run([sys.executable, str(rg), str(b), "--skip", "G3,G4,G5,G6,G7,G8"])
        check("run_gates 可跑且占位 G0 红", "G0 FAIL" in r.stdout and r.returncode != 0,
              r.stdout + r.stderr)
        # memory_maint
        mm = ROOT / "writing-rules" / "tools" / "memory_maint.py"
        (b / "workflow" / "draft-old.md").write_text("x", encoding="utf-8")
        r = run([sys.executable, str(mm), str(b)])
        check("memory_maint 归档草稿", r.returncode == 0 and not (b / "workflow" / "draft-old.md").exists(),
              r.stdout + r.stderr)
        # package_book
        pkg = ROOT / "writing-rules" / "tools" / "package_book.py"
        out_tar = td / "pack.tar.gz"
        r = run([sys.executable, str(pkg), str(b), "--engine", str(ROOT / "techbook-typst"),
                 "--out", str(out_tar), "--skip-quality",
                 "--pdf", str(ROOT / "techbook-typst" / "dist" / "book.pdf")])
        import tarfile as tf
        names = []
        if out_tar.is_file():
            with tf.open(out_tar, "r:gz") as tar:
                names = tar.getnames()
        pdf_exists = (ROOT / "techbook-typst" / "dist" / "book.pdf").is_file()
        check("package_book 产出 tar.gz", r.returncode == 0 and out_tar.is_file()
              and any(x.endswith("README.md") for x in names)
              and any("typst/" in x for x in names)
              and any("manuscript/" in x for x in names)
              and (not pdf_exists or any(x.endswith("book.pdf") for x in names)),
              r.stdout + r.stderr + str(names[:8]))
        with tf.open(out_tar, "r:gz") as tar:
            rd = next(n for n in tar.getnames() if n.endswith("README.md"))
            text = tar.extractfile(rd).read().decode("utf-8")
        check("package_book 含 LICENSE", any(x.endswith("LICENSE") for x in names), str(names))
        check("README 含书籍介绍", ("本书承诺" in text or "适合谁" in text)
              and "从源码到产物" in text and "License" in text, text[:200])
        check("package_book 无 archive/日志", not any("archive/" in x or x.endswith(".log") for x in names),
              str(names))
        # 清掉占位后 G0 才允许过（负例在上，正例在下）
        card_p = b / "01_立项卡.json"
        card = json.loads(card_p.read_text(encoding="utf-8"))
        card["claim"] = "在规模 S2 的服务仓库里，未锁依赖树会导致同 commit 构建产物漂移"
        card["increment_note"] = "对照五道版本锁给出可指认症状与体检命令"
        card["reader_before"] = "能独立维护一个 .NET 服务仓库"
        card["sources"] = [
            {"title": "MSBuild 求值顺序", "type": "E1", "url": "https://learn.microsoft.com/msbuild",
             "version": "2026-10", "locator": "property-functions"},
            {"title": "NuGet 锁文件", "type": "E1",
             "url": "https://learn.microsoft.com/nuget/consume-packages/package-references-in-project-files",
             "version": "2026-10", "locator": "lock-file"},
            {"title": "本机实测", "type": "E1", "url": "repo:writing-rules/spec/05-写作单元.md",
             "version": "1.0", "locator": "§4.7"},
        ]
        card["risk"] = [{"item": "SDK 版本号易过期", "review_by": "2027-01"}]
        card["kill_criteria"] = ["连续两章无新判断", "读者测试表明目标不可达"]
        card_p.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
        code, out = gate("G0", b)
        check("填充真实来源后 G0 可过", code == 0, out)
        r = run([sys.executable, str(asm), str(b), "--engine", str(ROOT / "techbook-typst"),
                 "--out", str(b / "chapters")])
        check("assemble 出 chapters", r.returncode == 0 and (b / "chapters" / "ch1.typ").is_file()
              and (b / "chapters" / "preface.typ").is_file(), r.stdout + r.stderr)
        check("assemble 不乱写引擎 config", (b / "chapters" / "chapters.manifest").is_file()
              or "跳过 config" in r.stdout, r.stdout)

        engine_cfg = ROOT / "techbook-typst" / "config.toml"
        before = engine_cfg.read_bytes()
        r = run([sys.executable, str(asm), str(b), "--engine", str(ROOT / "techbook-typst")])
        check("assemble 默认生成书内 typst/", r.returncode == 0
              and (b / "typst" / "main.typ").is_file()
              and (b / "typst" / "config.toml").is_file()
              and (b / "typst" / "src" / "book.typ").is_file()
              and (b / "typst" / "chapters" / "ch1.typ").is_file(), r.stdout + r.stderr)
        check("assemble 不覆盖引擎 config", engine_cfg.read_bytes() == before, r.stdout)

        # package_book 优先打包书内 typst/
        pkg = ROOT / "writing-rules" / "tools" / "package_book.py"
        out_tar2 = td / "booktypst.tar.gz"
        r = run([sys.executable, str(pkg), str(b), "--engine", str(ROOT / "techbook-typst"),
                 "--out", str(out_tar2), "--skip-quality"])
        names2 = []
        if out_tar2.is_file():
            import tarfile as tf2
            with tf2.open(out_tar2, "r:gz") as tar:
                names2 = tar.getnames()
        check("package_book 优先书内 typst", any(x.endswith("typst/main.typ") for x in names2)
              and not any(x.endswith("typst/chapters/ch1-intro.typ") for x in names2),
              str(names2[:8]) + r.stdout[:200])

    print("== 门禁假绿与真源巡检 ==")
    # G4 未实现必须红，不得 PASS
    code, out = gate("G4", BOOK)
    check("G4 未实现不得假绿", code != 0 and "未实现的门禁" in out, out[:200])
    r = run([sys.executable, str(ROOT / "writing-rules" / "tools" / "run_gates.py"),
             str(BOOK), "--skip", "G0,G1,G2,G3,G5,G6,G7,G8"])
    check("run_gates 对 G4 报 FAIL", "G4 FAIL" in r.stdout or "G4 SKIP" in r.stdout,
          r.stdout[:300])

    # check_rule_coverage：声称脚本必须有实现
    cov = ROOT / "writing-rules" / "tools" / "check_rule_coverage.py"
    r = run([sys.executable, str(cov)])
    check("check_rule_coverage 可跑", "COVERAGE_" in r.stdout, r.stdout[:300])
    check("check_rule_coverage 无 P0 悬空脚本", "COVERAGE_PASS" in r.stdout,
          r.stdout[:500])
    r = run([sys.executable, str(LINT), str(ROOT / "writing-rules" / "spec"), "--registry"])
    check("规则总表 145 条", "共 **145** 条" in r.stdout, r.stdout[:300])
    check("规则总表含 CLAIM/HUMOR/B/F",
          all(x in r.stdout for x in ("CLAIM-01", "HUMOR-01", "B-01", "F-01")),
          r.stdout[-800:])

    print("== validate_quality ==")
    vq = ROOT / "writing-rules" / "tools" / "validate_quality.py"
    # 金样板无大纲合同页数时应提示；有 units 应报告体量问题（样板单节较短）
    r = run([sys.executable, str(vq), str(BOOK)])
    # 金样板可能因体量/合同 FAIL，这是预期；至少脚本可跑
    check("validate_quality 可运行", r.returncode in (0, 1, 2) and "QUALITY" in r.stdout, r.stdout[:300])

    # 文件名契约：01_读者报告-第1章.md 也算命中（WORKFLOW §7）
    with tempfile.TemporaryDirectory() as td2:
        b2 = Path(td2) / "book"
        (b2 / "units").mkdir(parents=True)
        (b2 / "workflow").mkdir()
        (b2 / "02_outline.json").write_text(json.dumps({
            "book": {"title": "t", "type": "实战书", "family": "B", "claim": "c",
                     "target_words": 50000},
            "chapters": [{"id": "C01", "title": "t", "purpose": "p",
                          "role": {"phenomenon": "C01-S1", "mechanism": "C01-S1", "cost": "C01-S1"},
                          "sections": [{"id": "C01-S1", "title": "t", "question": "q",
                                        "produces": "p", "deps": [], "status": "drafting",
                                        "words": 2000, "bridge": "b"}]}],
            "paths": [], "concepts": [],
        }, ensure_ascii=False), encoding="utf-8")
        (b2 / "05_state.json").write_text("{}", encoding="utf-8")
        (b2 / "units" / "C01-S1.md").write_text("# t\n\n" + "字" * 2000, encoding="utf-8")
        (b2 / "workflow" / "00_大纲合同.json").write_text(json.dumps({
            "book": {"target_words_min": 40000, "target_words_max": 60000},
            "section": {"words_absolute_min": 100, "words_min_ratio": 0.5},
        }), encoding="utf-8")
        (b2 / "workflow" / "01_读者报告-第1章.md").write_text(
            "# 读者报告\n\n日期 | 2026-10-22\n\n具体意见三条。\n", encoding="utf-8")
        (b2 / "workflow" / "02_编辑审校-第1章.md").write_text(
            "# 编辑审校\n\n日期 | 2026-10-22\n\n结论：通过。\n", encoding="utf-8")
        (b2 / "workflow" / "09_大纲×规范融合评估.md").write_text(
            "# 融合\n\n日期 | 2026-10-22\n\n裁决 C-01。\n", encoding="utf-8")
        r = run([sys.executable, str(vq), str(b2)])
        check("validate_quality 认 01_读者报告-第1章.md",
              "缺 workflow/01_读者报告" not in r.stdout, r.stdout[:300])

        # P0-F：人工确认不得「默示」
        (b2 / "workflow" / "00_阶段状态.json").write_text(json.dumps({
            "phase": "P3",
            "rule_conflict_status": "confirmed",
            "rule_conflict_decision": "用户委托 Agent 全程推进，视为默示确认",
            "reader_persona_confirmed_by_human": False,
            "pending_human": ["L2 终验"],
        }, ensure_ascii=False), encoding="utf-8")
        r = run([sys.executable, str(vq), str(b2)])
        check("默示确认被拒", "默示" in r.stdout, r.stdout[:300])

    print("== quality_gate ==")
    with tempfile.TemporaryDirectory() as td:
        b = Path(td) / "qbook"
        (b / "units").mkdir(parents=True)
        (b / "workflow").mkdir()
        outline = {
            "book": {"title": "Q", "type": "实战书", "claim": "claim enough words",
                     "target_words": 30000, "family": "B"},
            "chapters": [{
                "id": "C01", "title": "章", "purpose": "p", "produces": "o",
                "role": {"phenomenon": "C01-S1", "mechanism": "C01-S1", "cost": "C01-S1"},
                "sections": [{"id": "C01-S1", "title": "节", "question": "q",
                              "produces": "p", "bridge": "b", "layer": "现象",
                              "deps": [], "words": 2000, "status": "checking"}],
            }],
            "paths": [{"name": "linear", "order": ["C01"]}],
        }
        (b / "02_outline.json").write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8")
        (b / "05_state.json").write_text(json.dumps({
            "book": "Q", "stage": "S2", "done_units": ["C01-S1"],
        }), encoding="utf-8")
        (b / "workflow" / "00_阶段状态.json").write_text(json.dumps({
            "phase": "P1", "human_in_loop": True,
        }, ensure_ascii=False), encoding="utf-8")
        (b / "04_ledger.csv").write_text(
            "id,claim,level,source_title,url,version,locator,cmd,exit_code,output_hash,date,unit\n"
            "E-001,本机实测,E0,本机,,1,run,dotnet --version,0,abc,2026-01-01,C01-S1\n",
            encoding="utf-8")
        (b / "units" / "C01-S1.spec.md").write_text(
            "# spec\n\n## 6. claims\n\n| A1 | x | E0 | cmd | E-001 |\n", encoding="utf-8")
        (b / "units" / "C01-S1.md").write_text(
            "# 节\n\n## 小节\n\n```csharp\nfoo.Bar;\n```\n", encoding="utf-8")

        p0, _ = quality_gate.run_checks(b)
        check("quality_gate 捕获缺调用括号", any(i["rule_id"] == "CODE-03" for i in p0),
              str(p0)[:300])

        (b / "units" / "C01-S1.md").write_text(
            "# 节\n\n## 小节\n\n<!-- illustrative -->\n\n```csharp\nfoo.Bar;\n```\n",
            encoding="utf-8")
        p0, _ = quality_gate.run_checks(b)
        check("illustrative 代码可豁免", not any(i["rule_id"] == "CODE-03" for i in p0),
              str(p0)[:300])

        (b / "workflow" / "01_读者报告.md").write_text(
            "# 读者报告\n\n评审对象：第 1 章\n日期：2026-10-22\n读完了，整体可读。\n",
            encoding="utf-8")
        p0, _ = quality_gate.run_checks(b)
        check("4 行报告必须红", any(i["rule_id"] in ("RPT-02", "RPT-04") for i in p0),
              str(p0)[:300])

        (b / "workflow" / "00_阶段状态.json").write_text(json.dumps({
            "phase": "P2", "human_in_loop": True, "rule_conflict_status": "confirmed",
            "rule_conflict_decision": "人已确认", "reader_persona_confirmed_by_human": False,
            "human_confirmations": {},
        }, ensure_ascii=False), encoding="utf-8")
        p0, _ = quality_gate.run_checks(b)
        check("P1 未签字不得进 P2", any(i["rule_id"] == "WF-11" for i in p0),
              str(p0)[:400])

        (b / "04_ledger.csv").write_text(
            "id,claim,level,source_title,url,version,locator,cmd,exit_code,output_hash,date,unit\n"
            "E-001,claim,with,comma,E0,本机,1,run,dotnet --version,0,abc,2026-01-01,C01-S1\n",
            encoding="utf-8")
        ev = quality_gate.check_evidence(b, outline)
        check("坏 CSV 台账必须红", any(i["rule_id"] in ("EVD-02", "EVD-04") for i in ev),
              str(ev)[:300])

    print("== 工具误报与崩溃回归（F# 案例） ==（raw 读取，避免 GBK 解码误伤）")

    def run_json(args):
        rr = subprocess.run(args, capture_output=True)
        raw = rr.stdout.decode("utf-8", errors="replace")
        try:
            return rr.returncode, json.loads(raw), raw, rr.stderr.decode("utf-8", errors="replace")
        except Exception:
            return rr.returncode, None, raw, rr.stderr.decode("utf-8", errors="replace")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        f = td / "unicode.md"
        f.write_text("# t\n\n雪人符号 \u2603 与制表符\t测试。\n", encoding="utf-8")
        rc, d, raw, err = run_json([sys.executable, str(LINT), str(f),
                                    "--profile", "manuscript", "--json"])
        check("spec_lint --json 不因非常用字符崩溃",
              rc in (0, 1, 2) and d is not None, raw[:200] + err[:200])

        f2 = td / "noise.md"
        f2.write_text(
            "# t\n\n"
            "<!-- src: fsharp-book-examples/src/Ch01/HelloCs/Program.cs:1-1 -->\n\n"
            "> This is an intentionally very long English quotation line that should "
            "never be counted as a Chinese sentence at all.\n\n"
            "短句。\n",
            encoding="utf-8")
        rc, d2, raw, _ = run_json([sys.executable, str(LINT), str(f2),
                                   "--profile", "manuscript", "--json"])
        check("注释行/西文引文不报 LANG-05",
              d2 is not None and not any(i.get("rule_id") == "LANG-05" for i in d2.get("P1", [])),
              raw[:400])

        f3 = td / "label2.md"
        f3.write_text("# t\n\n## 机制\n\n正文一句。\n\n## 小结\n\n又一句。\n\n"
                      "## 小结与官方锚点\n\n人话标题不该命中。\n", encoding="utf-8")
        rc, d3, raw, _ = run_json([sys.executable, str(LINT), str(f3),
                                   "--profile", "manuscript", "--json"])
        labels = [i for i in (d3 or {}).get("P0", []) if i.get("rule_id") == "L-FORM-01"]
        check("去冒号挂牌（## 机制/## 小结）必须红", len(labels) == 2, str(labels)[:300])

    print("== quality_gate 代码误报回归 ==")
    with tempfile.TemporaryDirectory() as td:
        b = Path(td) / "cb"
        (b / "units").mkdir(parents=True)
        (b / "units" / "C01-S1.md").write_text(
            "# 节\n\n## 小节\n\n```csharp\nvar text = Text.Corpus;\n```\n", encoding="utf-8")
        p0, _ = quality_gate.run_checks(b)
        check("属性读取赋值不报 CODE-03",
              not any(i["rule_id"] == "CODE-03" for i in p0), str(p0)[:300])
        (b / "units" / "C01-S1.md").write_text(
            "# 节\n\n## 小节\n\n```csharp\nfoo.Bar;\n```\n", encoding="utf-8")
        p0, _ = quality_gate.run_checks(b)
        hit = [i for i in p0 if i["rule_id"] == "CODE-03"]
        check("裸语句 foo.Bar; 必须红且带文件定位",
              bool(hit) and hit[0].get("file", "").endswith("C01-S1.md"), str(hit)[:300])

    print("== 合同与衰减检测（F# 案例） ==")
    with tempfile.TemporaryDirectory() as td:
        b = Path(td) / "decay"
        (b / "units").mkdir(parents=True)

        def wu(stem, body, spec_eids=True):
            (b / "units" / f"{stem}.md").write_text(body, encoding="utf-8")
            (b / "units" / f"{stem}.spec.md").write_text(
                "# spec\n\n## claims\n\n| 项 | 内容 |\n|---|---|\n"
                + ("| 断言 | E-001 |\n" if spec_eids else "| 断言 | 无 |\n"),
                encoding="utf-8")

        for ch in range(1, 10):
            thin = ch >= 7
            for s in (1, 2):
                if thin:
                    wu(f"C{ch:02d}-S{s}", "# 节\n\n## 小节\n\n" + "注意" * 8 + "。\n", False)
                else:
                    wu(f"C{ch:02d}-S{s}", "# 节\n\n## 小节\n\n" + "这一节讲真实内容。" * 12 + "\n", True)
        dec = quality_gate.check_decay(b, {})
        check("批量衰减必须红（体量/证据）",
              any(i["rule_id"] == "DECAY-01" and i["level"] == "P0" for i in dec)
              and any(i["rule_id"] == "DECAY-03" for i in dec), str(dec)[:400])

        # 合同交付物清单
        contract = {"deliverables": ["typst/chapters/appendix-*.typ"], "figures_min": 1}
        cd = quality_gate.check_contract_deliverables(b, contract)
        check("交付物缺失必须红", any(i["rule_id"] == "CTR-01" for i in cd)
              and any(i["rule_id"] == "CTR-02" for i in cd), str(cd)[:300])
        (b / "typst" / "chapters").mkdir(parents=True)
        (b / "typst" / "chapters" / "appendix-a.typ").write_text("#appendix[速查]\n", encoding="utf-8")
        (b / "typst" / "chapters" / "ch1.typ").write_text("#fig(image(\"a.png\"))\n", encoding="utf-8")
        cd = quality_gate.check_contract_deliverables(b, contract)
        check("交付物齐备不报", not cd, str(cd)[:300])

        # 章块检查：C01 有块、其余缺 → CTR-03；全书都缺 → CTR-04（命名不符）
        p1 = b / "units" / "C01-S1.md"
        p1.write_text(p1.read_text(encoding="utf-8") + "\n## 动手练习\n\n做一遍。\n", encoding="utf-8")
        cb = quality_gate.check_chapter_blocks(b, {"chapter_blocks_required": ["动手练习"]})
        check("缺合同骨架块必须报 CTR-03", any(i["rule_id"] == "CTR-03" for i in cb),
              str(cb)[:300])
        cb = quality_gate.check_chapter_blocks(b, {"chapter_blocks_required": ["动手练习"],
                                                   "chapter_blocks_aliases": {"动手练习": ["做一遍"]}})
        check("配别名后不再报 CTR-04", not any(i["rule_id"] == "CTR-04" for i in cb),
              str(cb)[:300])
        cb4 = quality_gate.check_chapter_blocks(b, {"chapter_blocks_required": ["七段"]})
        check("全书零命中的块报 CTR-04", any(i["rule_id"] == "CTR-04" for i in cb4),
              str(cb4)[:300])

        # 证据策略
        (b / "04_ledger.csv").write_text(
            "id,claim,level,source_title,url,version,locator,cmd,exit_code,output_hash,date,unit\n"
            "E-001,claim,E1,doc,local,1,x,,,,2026-01-01,实验\n", encoding="utf-8")
        ev = quality_gate.check_evidence(b, {}, {"evidence_policy": "spec-mapping"})
        check("台账 unit='实验' 与 url='local' 必须报",
              any(i["rule_id"] == "EVD-14" for i in ev)
              and any(i["rule_id"] == "EVD-15" for i in ev), str(ev)[:400])
        check("spec-mapping 下正文无 E-xxx 不报 EVD-13",
              not any(i["rule_id"] == "EVD-13" for i in ev), str(ev)[:300])
        ev2 = quality_gate.check_evidence(b, {}, {})
        check("默认 body-e-tags 报 EVD-13", any(i["rule_id"] == "EVD-13" for i in ev2),
              str(ev2)[:300])

        # notes_brief 单字符污染
        st = {"notes_brief": ["6", "8", "C42 完成。"]}
        nb = quality_gate.check_state_sanity(b, b, st)
        check("notes_brief 单字符污染必须报", any(i["rule_id"] == "WF-23" for i in nb),
              str(nb)[:300])

    print("== spec_lint 证据策略 ==")
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "claim.md"
        f.write_text("# t\n\n实测结果显示体积下降 3.7%。\n", encoding="utf-8")

        def claim_issue(policy):
            rr = subprocess.run([sys.executable, str(LINT), str(f), "--profile", "manuscript",
                                 "--json", "--evidence-policy", policy], capture_output=True)
            d = json.loads(rr.stdout.decode("utf-8", errors="replace"))
            return [i for i in d.get("P0", []) + d.get("P1", []) if i.get("rule_id") == "L-CLAIM-01"]

        hit = claim_issue("body-e-tags")
        check("body-e-tags 数字无 E-xxx 仍 P0", hit and hit[0]["level"] == "P0", str(hit)[:200])
        hit = claim_issue("spec-mapping")
        check("spec-mapping 降为 P1", hit and hit[0]["level"] == "P1", str(hit)[:200])
        hit = claim_issue("visible-markers")
        check("visible-markers 无标记仍 P0", hit and hit[0]["level"] == "P0", str(hit)[:200])
        f.write_text("# t\n\n无法验证（未实测）：实测结果显示体积下降 3.7%。\n", encoding="utf-8")
        hit = claim_issue("visible-markers")
        check("visible-markers 有标记即合规", not hit, str(hit)[:200])

    print("== 门禁单调与交付契约 ==")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # G4 默认 SKIP，不再永久 HAS_FAIL
        r = run([sys.executable, str(ROOT / "writing-rules" / "tools" / "run_gates.py"),
                 str(BOOK), "--skip", "G0,G1,G2,G3,G5,G6,G7,G8"])
        check("G4 未实现默认 SKIP 且不拖累退出码",
              r.returncode == 0 and "G4 SKIP" in r.stdout, r.stdout[:300])
        # G7 依赖 G8：G8 未过时 G7 不得 PASS（门禁单调）
        r = run([sys.executable, str(ROOT / "writing-rules" / "tools" / "run_gates.py"),
                 str(BOOK), "--skip", "G0,G1,G2,G3,G4,G5,G6"])
        check("G8 未过时 G7 必须 FAIL",
              "G7 FAIL" in r.stdout and "G8 FAIL" in r.stdout, r.stdout[:400])

        # --write-check 门禁回执
        bb = td / "rcpt"
        (bb / "handoff").mkdir(parents=True)
        (bb / "02_outline.json").write_text("{}", encoding="utf-8")
        r = run([sys.executable, str(ROOT / "writing-rules" / "tools" / "run_gates.py"),
                 str(bb), "--skip", "G0,G1,G2,G3,G4,G5,G6,G7,G8", "--write-check"])
        rec = bb / "handoff" / "04_check.json"
        ok_rec = rec.is_file() and "gates" in rec.read_text(encoding="utf-8")
        check("run_gates --write-check 写门禁回执", ok_rec, r.stdout[:300])

        # RPT-11：报告写门禁结论须带回执；声称 P0=0 与实测不符须红
        wf = bb / "workflow"
        wf.mkdir(exist_ok=True)
        rp = wf / "01_读者报告-第1章.md"
        base_report = ("# 读者报告\n\n评审对象：第 1 章\n日期：2026-10-27\n"
                       "读完了。工具核对：quality_gate.py P0=0 P1=0。\n\n"
                       "`units/C01-S1.md:2`：「结论句」\n\n"
                       "<!-- reviewed_revision: deadbeefdeadbeef -->\n")
        rp.write_text(base_report, encoding="utf-8")
        iss = quality_gate.check_report_file(rp, bb)
        check("门禁结论无回执必须 RPT-11", any(i["rule_id"] == "RPT-11" for i in iss),
              str(iss)[:300])
        rp.write_text(base_report.replace(
            "P1=0。", "P1=0。<!-- gate_check: run_gates --write-check → handoff/04_check.json -->"),
            encoding="utf-8")
        iss = quality_gate.check_report_file(rp, bb)
        check("有回执不再报 RPT-11(P1)", not any(i["rule_id"] == "RPT-11" for i in iss),
              str(iss)[:300])
        gc = quality_gate.check_gate_claims(wf, p0_total=3)
        check("声称 P0=0 与实测不符必须 P0",
              any(i["rule_id"] == "RPT-11" and i["level"] == "P0" for i in gc), str(gc)[:300])

        # revision 链：登记迁移后旧报告降为可追溯 P1
        bb2 = td / "chain"
        (bb2 / "units").mkdir(parents=True)
        u = bb2 / "units" / "C01-S1.md"
        u.write_text("# 节\n\n结论句在这里。\n", encoding="utf-8")
        cur = quality_gate.revision_hash(bb2, [u])
        rp2 = bb2 / "workflow" / "01_读者报告-第1章.md"
        rp2.parent.mkdir(exist_ok=True)
        rp2.write_text(
            "# 读者报告\n\n评审对象：第 1 章\n日期：2026-10-27\n读完了。\n\n"
            "`units/C01-S1.md:3`：「结论句在这里。」\n\n"
            "<!-- reviewed_revision: deadbeefdeadbeef -->\n", encoding="utf-8")
        iss = quality_gate.check_report_file(rp2, bb2)
        check("无迁移登记的旧报告仍是 RPT-09 P0",
              any(i["rule_id"] == "RPT-09" and i["level"] == "P0" for i in iss), str(iss)[:300])
        (bb2 / "workflow" / "revision_log.jsonl").write_text(
            json.dumps({"from": "deadbeefdeadbeef", "to": cur,
                        "reason": "标识清理后重排"}, ensure_ascii=False) + "\n",
            encoding="utf-8")
        iss = quality_gate.check_report_file(rp2, bb2)
        hit = [i for i in iss if i["rule_id"] == "RPT-09"]
        check("revision_log 登记后旧报告可追溯（P1）",
              hit and hit[0]["level"] == "P1", str(iss)[:300])

        # 交付命名护栏：未人终审签字禁「终版/final/ready」
        bk = td / "naming"
        bk.mkdir()
        (bk / "02_outline.json").write_text(
            json.dumps({"book": {"title": "命名", "target_words": 2000, "pages": 10},
                        "chapters": []}, ensure_ascii=False), encoding="utf-8")
        pkg = ROOT / "writing-rules" / "tools" / "package_book.py"
        r = run([sys.executable, str(pkg), str(bk), "--engine", str(ROOT / "techbook-typst"),
                 "--out", str(td / "终版包.tar.gz"), "--dry-run", "--skip-quality"])
        check("未签字用「终版」命名必须拒绝",
              r.returncode != 0 and "--force-name" in r.stdout + r.stderr,
              (r.stdout + r.stderr)[:300])
        r = run([sys.executable, str(pkg), str(bk), "--engine", str(ROOT / "techbook-typst"),
                 "--out", str(td / "终版包.tar.gz"), "--dry-run", "--skip-quality",
                 "--force-name"])
        check("--force-name 可显式放行", r.returncode == 0, (r.stdout + r.stderr)[:300])
        out_tar = td / "book-draft.tar.gz"
        r = run([sys.executable, str(pkg), str(bk), "--engine", str(ROOT / "techbook-typst"),
                 "--out", str(out_tar), "--skip-quality"])
        import tarfile
        man = ""
        if out_tar.is_file():
            with tarfile.open(out_tar, "r:gz") as tar:
                for m in tar.getnames():
                    if m.endswith("MANIFEST.txt"):
                        man = tar.extractfile(m).read().decode("utf-8", errors="replace")
        check("MANIFEST 带 delivery_status", "delivery_status: draft" in man,
              man[:300] + (r.stdout + r.stderr)[:200])

    print("== Avalonia 案例回归（repo:落地/阶段守恒/固定块裁决/多行 new） ==")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # EVD-17：repo: 引用悬空必须红（聚合），落地后干净
        bb = td / "ev"
        (bb / "units").mkdir(parents=True)
        (bb / "04_ledger.csv").write_text(
            "id,claim,level,source_title,url,version,locator,cmd,exit_code,output_hash,date,unit\n"
            "E-001,c,E0,本机,repo:bookvault,1,x,dotnet run,0,abc,2026-01-01,C01-S1\n"
            "E-002,c,E0,本机,repo:bookvault,1,x,dotnet run,0,abc,2026-01-01,C01-S1\n",
            encoding="utf-8")
        ev = quality_gate.check_evidence(bb, {})
        hit = [i for i in ev if i["rule_id"] == "EVD-17"]
        check("repo: 引用悬空必须红且聚合", hit and "2 条" in hit[0]["msg"], str(ev)[:300])
        (bb / "bookvault").mkdir()
        ev = quality_gate.check_evidence(bb, {})
        check("repo: 落地后不报 EVD-17", not any(i["rule_id"] == "EVD-17" for i in ev),
              str(ev)[:300])

        # WF-24：P1 未签字却全书量产
        bb = td / "wf24"
        (bb / "units").mkdir(parents=True)
        wf = bb / "workflow"
        wf.mkdir()
        for i in range(1, 6):
            (bb / "units" / f"C{i+1:02d}-S1.md").write_text("# 节\n\n" + "正文。" * 120,
                                                            encoding="utf-8")
        st = {"phase": "P1", "human_in_loop": True,
              "human_confirmations": {"pilot": {"confirmed": False}, "final": {"confirmed": False}},
              "pilot": {"chapter": "C01", "units": []}, "rule_conflict_status": "pending",
              "reader_persona_confirmed_by_human": False}
        (wf / "00_阶段状态.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        iss = quality_gate.check_phase(bb, wf, {}, {})
        check("P1 未签字全书量产必须 WF-24 P0",
              any(i["rule_id"] == "WF-24" and i["level"] == "P0" for i in iss), str(iss)[:400])

        # QG-05/06 三态：未裁决/标题承载/行文承载
        bb = td / "qg6"
        (bb / "units").mkdir(parents=True)
        outline = {"chapters": [{"id": "C01", "title": "t",
                                 "sections": [{"id": "C01-S1"}, {"id": "C01-S2"}]}]}
        body = "# 节\n\n## 小节\n\n正文讲机制。\n\n## 本章标尺\n\n带走三条判断。\n"
        (bb / "units" / "C01-S1.md").write_text(body, encoding="utf-8")
        (bb / "units" / "C01-S2.md").write_text(body, encoding="utf-8")
        iss = quality_gate.check_structure(bb, outline, {})
        check("固定块标题未裁决必须 QG-06", any(i["rule_id"] == "QG-06" for i in iss),
              str(iss)[:300])
        iss = quality_gate.check_structure(bb, outline, {"chapter_blocks_as_headings": True})
        check("合同裁定标题承载即豁免",
              not any(i["rule_id"] in ("QG-05", "QG-06") for i in iss), str(iss)[:300])
        iss = quality_gate.check_structure(bb, outline, {"chapter_blocks_as_headings": False})
        check("合同裁定行文承载则 QG-05", any(i["rule_id"] == "QG-05" for i in iss),
              str(iss)[:300])

        # CODE-04：多行 new（对象初始化器）不误报；单行 new 仍报
        bb = td / "c04"
        (bb / "units").mkdir(parents=True)
        (bb / "units" / "C01-S1.md").write_text(
            "# 节\n\n## 小节\n\n```csharp\nbooks.Add(new Book\n{\n    Id = \"x\",\n});\n```\n",
            encoding="utf-8")
        p0, _ = quality_gate.run_checks(bb)
        check("多行 new 对象初始化器不报 CODE-04",
              not any(i["rule_id"] == "CODE-04" for i in p0), str(p0)[:300])
        (bb / "units" / "C01-S1.md").write_text(
            "# 节\n\n## 小节\n\n```csharp\nvar b = new Book\n```\n", encoding="utf-8")
        p0, _ = quality_gate.run_checks(bb)
        check("单行 new 缺括号仍报 CODE-04",
              any(i["rule_id"] == "CODE-04" for i in p0), str(p0)[:300])

        # spec_lint --allow-block-headings
        f = td / "block.md"
        f.write_text("# t\n\n## 本章标尺\n\n正文一句。\n\n## 机制\n\n又一句。\n", encoding="utf-8")

        def form_labels(extra):
            rr = subprocess.run([sys.executable, str(LINT), str(f), "--profile", "manuscript",
                                 "--json"] + extra, capture_output=True)
            d = json.loads(rr.stdout.decode("utf-8", errors="replace"))
            return [i for i in d.get("P0", []) if i.get("rule_id") == "L-FORM-01"]

        check("默认固定块词也拦", len(form_labels([])) == 2, str(form_labels([]))[:300])
        hit = form_labels(["--allow-block-headings"])
        check("--allow-block-headings 只豁免固定块词",
              len(hit) == 1 and "机制" in (hit[0].get("quote") or ""), str(hit)[:300])

        # 门禁回执版本化
        bb = td / "rcpt2"
        (bb / "handoff").mkdir(parents=True)
        (bb / "02_outline.json").write_text("{}", encoding="utf-8")
        r = run([sys.executable, str(ROOT / "writing-rules" / "tools" / "run_gates.py"),
                 str(bb), "--skip", "G0,G1,G2,G3,G4,G5,G6,G7,G8", "--write-check"])
        rec = (bb / "handoff" / "04_check.json").read_text(encoding="utf-8")
        check("门禁回执带 git_rev 与工具版本",
              '"git_rev"' in rec and '"toolchain"' in rec, rec[:300])

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

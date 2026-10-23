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
            "# 节\n\n## 小节\n\n```csharp\nvar x = foo.Bar;\n```\n", encoding="utf-8")

        p0, _ = quality_gate.run_checks(b)
        check("quality_gate 捕获缺调用括号", any(i["rule_id"] == "CODE-03" for i in p0),
              str(p0)[:300])

        (b / "units" / "C01-S1.md").write_text(
            "# 节\n\n## 小节\n\n<!-- illustrative -->\n\n```csharp\nvar x = foo.Bar;\n```\n",
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

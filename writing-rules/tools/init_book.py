#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_book.py — 按 kit 模板脚手架一个写作工程，保证目录名与 G0–G7 一致。

产出：
  books/<slug>/
    01_立项卡.json  02_outline.json  04_ledger.csv  05_state.json
    06_glossary.json  07_style.kernel.md  08_读者假设.md
    conflicts.jsonl  units/  handoff/

用法：
  python3 init_book.py my-book --title "书名" --claim "可证伪承诺"
  python3 init_book.py my-book --from-golden books/how-to-write-a-tech-book
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "writing-rules" / "kit"

# 书稿工程标准文件名（与 spec_lint GATE_FILES / 金样板一致）
BOOK_FILES = [
    "01_立项卡.json",
    "02_outline.json",
    "04_ledger.csv",
    "05_state.json",
    "06_glossary.json",
    "07_style.kernel.md",
    "08_读者假设.md",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scaffold(slug: str, title: str, claim: str, dest_root: Path) -> Path:
    book = dest_root / slug
    if book.exists():
        raise SystemExit(f"错误：目录已存在 {book}")
    (book / "units").mkdir(parents=True)
    (book / "handoff").mkdir()

    # 立项卡：从 kit 模板填 title/claim，并给最小合法占位（请改写）
    card = load_json(KIT / "01_立项卡.json")
    card["title"] = title or slug
    card["claim"] = claim or "待改写：在条件 C 下机制 M 导致结果 R，反例是 X"
    card["increment"] = card.get("increment") or "系统化"
    card["increment_note"] = "待改写：具体多在哪里"
    card["reader_before"] = card.get("reader_before") or "待改写：读者进入时的可观测能力"
    card["reader_after"] = [
        "写出一句可证伪的书稿承诺",
        "交出通过门禁的一个写作单元",
    ]
    card["prerequisites"] = [{"item": "待改写：前置动作", "fallback": "先补某技能"}]
    card["scope_in"] = ["待改写：承诺覆盖点"]
    card["scope_out"] = [
        {"item": "待改写：不写 A", "reason": "与承诺无关"},
        {"item": "待改写：不写 B", "reason": "另一条交付链"},
        {"item": "待改写：不写 C", "reason": "读者成本过高"},
    ]
    card["sources"] = [
        {"title": "写作规范", "url": "repo:writing-rules/spec", "version": "1.0",
         "locator": "§0–§9", "type": "E1"},
        {"title": "待改写来源 2", "url": "repo:writing-rules/spec/02-立项.md", "version": "1.0",
         "locator": "§1.3", "type": "E1"},
        {"title": "待改写来源 3", "url": "repo:books/how-to-write-a-tech-book", "version": "1.0",
         "locator": "handoff/00_README.md", "type": "E1"},
    ]
    card["risk"] = [{"item": "待改写：易过期内容", "review_by": "2027-01"}]
    card["kill_criteria"] = [
        "待改写：可判定的停写条件 1",
        "待改写：可判定的停写条件 2",
    ]
    dump_json(book / "01_立项卡.json", card)

    # outline：最小合法骨架（一章三节），字段名与 schema 一致
    outline = {
        "_说明": "结构的唯一真源（§3.3）。G2 依据。字段名与层级不得改动。",
        "book": {
            "title": title or slug,
            "type": "实战书",
            "claim": claim or "",
            "target_words": 35000,
            "family": "C",
            "review_by": "2027-01",
        },
        "volumes": [],
        "chapters": [
            {
                "id": "C01",
                "title": "待定章名",
                "purpose": "读完能完成的一件可验证的事",
                "produces": "本章产出的可见物",
                "role": {"phenomenon": "C01-S1", "mechanism": "C01-S2", "cost": "C01-S3"},
                "requires": [],
                "words": 7500,
                "sections": [
                    {
                        "id": "C01-S1", "title": "现象节", "question": "这一节回答什么？",
                        "produces": "读者拿到的东西", "bridge": "开篇，承接书名承诺",
                        "layer": "现象", "concepts": [], "deps": [], "words": 2500, "status": "planned",
                    },
                    {
                        "id": "C01-S2", "title": "机制节", "question": "这一节回答什么？",
                        "produces": "读者拿到的东西", "bridge": "上一节留下了什么",
                        "layer": "机制", "concepts": [], "deps": ["C01-S1"], "words": 2500, "status": "planned",
                    },
                    {
                        "id": "C01-S3", "title": "代价节", "question": "这一节回答什么？",
                        "produces": "读者拿到的东西", "bridge": "上一节留下了什么未解问题？",
                        "layer": "代价", "concepts": [], "deps": ["C01-S2"], "words": 2500, "status": "planned",
                    },
                ],
            }
        ],
        "paths": [{"name": "线性通读", "order": ["C01"]}],
        "concepts": [],
    }
    dump_json(book / "02_outline.json", outline)

    shutil.copy2(KIT / "04_ledger.csv", book / "04_ledger.csv")
    shutil.copy2(KIT / "07_style.kernel.md", book / "07_style.kernel.md")

    state = load_json(KIT / "05_state.json")
    state["book"] = title or slug
    state["stage"] = "S0"
    dump_json(book / "05_state.json", state)

    shutil.copy2(KIT / "06_glossary.json", book / "06_glossary.json")
    shutil.copy2(KIT / "03_单元spec.md", book / "03_单元spec.md")

    # 读者假设：从模板骨架，避免 G1 缺文件
    reader = (
        "# 读者假设表（S1 / §2）\n\n"
        "每条标 `given / inferred / assumed`。`assumed` 不得支撑比较级。\n\n"
        "## 1. 假设表\n\n"
        "| # | 假设 | 标记 | 依据 | 能支撑的写法 |\n"
        "|---|---|---|---|---|\n"
        "| A1 | 示例假设（请改写） | given | 用户说明 | 可直陈 |\n\n"
        "## 2. 起点能力清单\n\n"
        "开始读第 1 章之前，你应该能：\n\n"
        "- 用一句话说出你要解决的问题\n"
        "- 在终端执行脚本并读退出码\n\n"
        "## 3. 未验证声明\n\n"
        "未做真实读者试读；A1 假设待确认。\n"
    )
    (book / "08_读者假设.md").write_text(reader, encoding="utf-8")
    (book / "conflicts.jsonl").write_text("", encoding="utf-8")
    (book / "units" / ".gitkeep").write_text("", encoding="utf-8")
    (book / "handoff" / ".gitkeep").write_text("", encoding="utf-8")

    # 写作工作流目录（三角色 / 四阶段）——见 writing-rules/workflow/WORKFLOW.md
    wf_src = ROOT / "writing-rules" / "workflow" / "templates"
    wf_dst = book / "workflow"
    wf_dst.mkdir(exist_ok=True)
    (wf_dst / "memory").mkdir(exist_ok=True)
    (wf_dst / "archive").mkdir(exist_ok=True)
    for name in ("00_阶段状态.json", "01_读者报告.md", "02_编辑审校.md",
                 "03_作者改进方案.md", "04_写作宪法.md", "05_章节滚动评估.md",
                 "06_终审报告包说明.md", "07_项目反哺报告.md"):
        src = wf_src / name
        if src.is_file():
            shutil.copy2(src, wf_dst / name)
    st_p = wf_dst / "00_阶段状态.json"
    if st_p.is_file():
        st = load_json(st_p)
        st["book"] = title or slug
        dump_json(st_p, st)

    readme = (
        f"# {title or slug}\n\n"
        f"新建写作工程（init_book）。\n\n"
        f"**开工必读** `writing-rules/workflow/WORKFLOW.md`（作者/读者/编辑 + 人，四阶段）。\n"
        f"门禁：`python3 writing-rules/tools/spec_lint.py --gate G0 {book}`\n"
        f"装配：`python3 writing-rules/tools/assemble_book.py {book}`\n"
    )
    (book / "README.md").write_text(readme, encoding="utf-8")
    return book


def clone_golden(slug: str, golden: Path, dest_root: Path) -> Path:
    book = dest_root / slug
    if book.exists():
        raise SystemExit(f"错误：目录已存在 {book}")
    shutil.copytree(golden, book)
    # 清掉金样板专属 handoff 快照，保留结构
    for name in ("01_outline.json", "02_outline.json", "02_glossary.json",
                 "03_ledger.csv", "04_check.json", "05_unverified.md", "00_README.md"):
        p = book / "handoff" / name
        if p.is_file():
            p.unlink()
    state_p = book / "05_state.json"
    if state_p.is_file():
        st = load_json(state_p)
        st["book"] = slug
        st["done_units"] = []
        st["last_unit"] = None
        st["stage"] = "S0"
        dump_json(state_p, st)
    return book


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", help="书稿目录名，如 my-book")
    ap.add_argument("--title", default="")
    ap.add_argument("--claim", default="")
    ap.add_argument("--dest", default=str(ROOT / "books"), help="父目录（默认 books/）")
    ap.add_argument("--from-golden", default="", help="从金样板拷贝结构（不拷贝进度）")
    a = ap.parse_args()

    dest_root = Path(a.dest).resolve()
    dest_root.mkdir(parents=True, exist_ok=True)
    if a.from_golden:
        golden = Path(a.from_golden).resolve()
        if not golden.is_dir():
            raise SystemExit(f"错误：金样板不存在 {golden}")
        book = clone_golden(a.slug, golden, dest_root)
    else:
        book = scaffold(a.slug, a.title, a.claim, dest_root)

    print(f"inited {book}")
    print("标准文件：", ", ".join(BOOK_FILES))
    print(f"下一步：G0  python3 writing-rules/tools/spec_lint.py --gate G0 {book}")
    print(f"        出书  python3 writing-rules/tools/assemble_book.py {book} --compile")
    return 0


if __name__ == "__main__":
    sys.exit(main())

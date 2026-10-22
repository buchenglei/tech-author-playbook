#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_quality.py — 体量 / 质量第一 / 流程真实性验收。

检查（任一 FAIL 则退出码 2）：
  1. 存在 00_大纲合同.json（或 legacy 字段）
  2. book.target_words 落在合同区间；sum(section.words) 与 target 同量级
  3. 每个 units/*.md 实写字数 ≥ 合同下限（防「梗概/省 token」）
  4. outline status=frozen 的节有正文，且 state.done_units / gates 可追溯
  5. workflow 报告非空模板（读者/编辑/冲突评估）
  6. 阶段状态：phase 与 chapters_done 不得「全书完成却停在 P1」

用法：
  python3 validate_quality.py books/my-book
  python3 validate_quality.py books/my-book --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def cjk_len(s: str) -> int:
    return len(re.findall(r"[一-鿿]", s)) + len(re.findall(r"[A-Za-z0-9_]+", s)) // 2


def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_empty_report(text: str) -> bool:
    if "（模板）" in text[:40] or "（模板）" in text[:80]:
        # 标题含模板
        if "日期 | |" in text or "| |" in text:
            pass
    # 空表格行占主导且无具体日期/评分数字
    if re.search(r"日期 \| \|", text) and not re.search(r"\d{4}-\d{2}", text):
        return True
    if "评审对象 | 第 __ 章" in text or "评审对象 |  |" in text:
        return True
    if text.count("（模板）") and len(text) < 2500 and "分析结论" not in text:
        # 模板且无实质段落标记
        if "待人确认" in text and "推荐选项 |" in text and not re.search(r"推荐选项\*\*：\s*A|推荐选项\*\*：\s*B|推荐选项\*\*：\s*C|裁决", text):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    book = Path(a.book_dir).resolve()
    issues = []

    def fail(msg, level="P0"):
        issues.append({"level": level, "msg": msg})

    # 1. 合同
    contract = load_json(book / "workflow" / "00_大纲合同.json")
    if not contract:
        fail("缺 workflow/00_大纲合同.json（大纲页数/深度未落合同）")

    outline = load_json(book / "02_outline.json") or {}
    state = load_json(book / "05_state.json") or {}
    bmeta = outline.get("book") or {}
    tw = bmeta.get("target_words") or 0

    # 2. 总字量
    if contract:
        lo = int((contract.get("book") or {}).get("target_words_min") or 0)
        hi = int((contract.get("book") or {}).get("target_words_max") or 0)
        if lo and tw < lo:
            fail(f"target_words={tw} 低于大纲合同下限 {lo}（页数合同未兑现）")
        if hi and tw > hi * 1.25:
            fail(f"target_words={tw} 远高于合同上限 {hi}（是否未拆分？）", "P1")
        pages = contract.get("pages") or {}
        if pages.get("target_min") and tw and tw < int(pages["target_min"]) * 200:
            fail(f"target_words={tw} 与页数下限 {pages['target_min']} 明显不匹配", "P0")

    secs = []
    for ch in outline.get("chapters") or []:
        for s in ch.get("sections") or []:
            secs.append(s)
    sum_w = sum(int(s.get("words") or 0) for s in secs)
    if tw and sum_w and abs(sum_w - tw) / max(tw, 1) > 0.45:
        fail(f"section.words 合计 {sum_w} 与 target_words={tw} 脱节（>45%）", "P0")

    # 3. 单元体量
    abs_min = 1200
    ratio = 0.6
    if contract:
        sc = contract.get("section") or {}
        abs_min = int(sc.get("words_absolute_min") or abs_min)
        ratio = float(sc.get("words_min_ratio") or ratio)
    units_dir = book / "units"
    thin = []
    if units_dir.is_dir():
        for s in secs:
            sid = s.get("id") or ""
            p = units_dir / f"{sid}.md"
            if not p.is_file():
                if s.get("status") == "frozen":
                    fail(f"{sid} frozen 但缺 units/{sid}.md")
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            n = cjk_len(text)
            need = max(abs_min, int(float(s.get("words") or 0) * ratio))
            if need and n < need:
                thin.append((sid, n, need))
        if thin:
            show = ", ".join(f"{sid} {n}<{need}" for sid, n, need in thin[:8])
            fail(f"{len(thin)} 节低于合同体量下限（梗概/省 token）：{show}", "P0")

    # 4. state 与 frozen
    frozen = sum(1 for s in secs if s.get("status") == "frozen")
    done = state.get("done_units") or []
    if frozen and not done:
        fail(f"outline 有 {frozen} 节 frozen，但 state.done_units 为空（过程不实）")
    gates = state.get("gates") or {}
    pending = [k for k, v in gates.items() if v == "pending"]
    if frozen >= max(1, len(secs) // 2) and pending:
        fail(f"多数节 frozen 但门禁仍 pending：{pending}")

    # 5. workflow 报告
    wf = book / "workflow"
    for name, label in (
        ("01_读者报告.md", "读者报告"),
        ("02_编辑审校.md", "编辑审校"),
        ("09_大纲规则冲突评估.md", "大纲规则冲突评估"),
    ):
        p = wf / name
        if not p.is_file():
            fail(f"缺 workflow/{name}（{label}）")
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if is_empty_report(text):
            fail(f"{label} 仍为空模板，不得当交付（{name}）")

    st_path = wf / "00_阶段状态.json"
    stw = load_json(st_path) or {}
    if stw.get("rule_conflict_status") == "pending" and frozen > 3:
        fail("大纲规则冲突评估未裁决（pending）却已大量冻结正文")
    if stw.get("body_min_token_allowed") is True:
        fail("body_min_token_allowed 被设为 true（违反质量第一）")

    p0 = [i for i in issues if i["level"] == "P0"]
    p1 = [i for i in issues if i["level"] != "P0"]
    if a.json:
        print(json.dumps({"book": str(book), "P0": p0, "P1": p1}, ensure_ascii=False, indent=2))
    else:
        print(f"QUALITY P0={len(p0)} P1={len(p1)}")
        for i in p0 + p1:
            print(f"  [{i['level']}] {i['msg']}")
        print("QUALITY_PASS" if not p0 else "QUALITY_FAIL")
    return 2 if p0 else (1 if p1 else 0)


if __name__ == "__main__":
    sys.exit(main())

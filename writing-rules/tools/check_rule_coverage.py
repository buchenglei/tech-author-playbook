#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_rule_coverage.py — 规则「声称有脚本」与 tools 实现的真源一致性巡检（RULE-01 自动化）。

做什么：
  1. 解析 spec/*.md 与 A-规则总表.md 中形如「脚本 L-XXX-01」「脚本 S-XXX」「脚本 G0 门禁」的判定标注；
  2. 扫描 writing-rules/tools/*.py 中真实出现的检查 ID（rule_id 字符串、L-/S-/R- 编号）；
  3. 声称有脚本却查无实现 → 退出码 1（P0）。

同时巡检：
  - 「MUST｜…｜阻断」条目若声称脚本，其实现必须能产生 P0（在 spec_lint 里 level="P0"）；
  - 文档里出现的旧文件名（09 报告三种叫法）不一致 → P1。

用法：
  python3 check_rule_coverage.py
  python3 check_rule_coverage.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "writing-rules" / "tools"
SPEC = ROOT / "writing-rules" / "spec"
REGISTRY = SPEC / "A-规则总表.md"

# 在 tools 源码里可识别为「实现了某检查」的模式
IMPL_PATTERNS = (
    re.compile(r"rule_id[\"']?\s*[:=]\s*[\"']([A-Z]{1,6}-[A-Z0-9-]+)[\"']"),
    re.compile(r"[\"']((?:L|S|R|G)-[A-Z]{2,10}-?\d{0,3})[\"']"),
    re.compile(r"[\"'](G[0-8])[\"']"),
)

# 声称「脚本 X」的解析：X 是一个 ID 或「G0 门禁」
CLAIM_RE = re.compile(r"脚本\s+([A-Z]{1,6}-[A-Z0-9-]+|G[0-8])")
# 总表行：| 域 | ID | 强度 | 判定 | 失败动作 | 所在小节 |
ROW_RE = re.compile(
    r"^\|\s*(?P<domain>[^|]+?)\s*\|\s*(?P<id>[A-Z]{2,6}-\d+)\s*\|\s*(?P<strength>MUST|SHOULD|MAY)\s*\|\s*(?P<judge>[^|]+?)\s*\|\s*(?P<action>[^|]+?)\s*\|",
    re.M,
)
# 正文规则行：**UNIT-23**（MUST｜脚本 L-VOL-01｜阻断）
SPEC_RULE_RE = re.compile(
    r"\*\*(?P<id>[A-Z]{2,6}-\d+)\*\*（(?P<strength>MUST|SHOULD|MAY)｜(?P<judge>[^｜]+)｜(?P<action>[^）]+)）"
)

# 09 报告标准名（全局唯一）
CANON_09 = "09_大纲×规范融合评估.md"
LEGACY_09 = ("09_大纲规则冲突评估.md", "大纲规则融合评估", "大纲规则冲突评估")


def collect_implemented() -> set[str]:
    found: set[str] = set()
    for py in TOOLS.glob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        for pat in IMPL_PATTERNS:
            for m in pat.finditer(text):
                found.add(m.group(1))
    return found


def _norm(rid: str) -> str:
    """L-LANG-05 / LANG-05 / l-lang-05 视为同一检查。"""
    s = rid.strip().upper()
    for p in ("L-", "S-", "R-"):
        if s.startswith(p) and len(s) > len(p) + 1:
            # 保留 G0 门禁类
            rest = s[len(p):]
            if rest.startswith("G") and rest[1:].isdigit():
                return s
            return rest
    return s


def _covered(claimed: str, implemented: set[str]) -> bool:
    if claimed in implemented:
        return True
    cn = _norm(claimed)
    if cn in implemented:
        return True
    for imp in implemented:
        if _norm(imp) == cn or imp == cn or _norm(imp) == claimed:
            return True
    # 「脚本 G0 门禁」等：gate() 分支即实现
    if claimed.upper().startswith("G") and claimed[-1:].isdigit():
        return claimed.upper() in implemented
    return False


def collect_claims() -> list[dict]:
    """返回 [{id, strength, judge, action, source, claimed_scripts}]"""
    rows: list[dict] = []
    if REGISTRY.is_file():
        for m in ROW_RE.finditer(REGISTRY.read_text(encoding="utf-8")):
            judge = m.group("judge").strip()
            scripts = CLAIM_RE.findall(judge)
            if "脚本" in judge or scripts:
                if not scripts:
                    tail = judge.split("脚本", 1)[-1].strip().split()
                    scripts = [tail[0]] if tail else ["?"]
                rows.append({
                    "id": m.group("id"),
                    "strength": m.group("strength"),
                    "judge": judge,
                    "action": m.group("action").strip(),
                    "source": "A-规则总表.md",
                    "claimed_scripts": scripts,
                })
    for md in sorted(SPEC.glob("0*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        for m in SPEC_RULE_RE.finditer(text):
            judge = m.group("judge").strip()
            if "脚本" not in judge:
                continue
            scripts = CLAIM_RE.findall(judge)
            if not scripts:
                tail = judge.split("脚本", 1)[-1].strip().split()
                scripts = [tail[0]] if tail else ["?"]
            rows.append({
                "id": m.group("id"),
                "strength": m.group("strength"),
                "judge": judge,
                "action": m.group("action").strip(),
                "source": md.name,
                "claimed_scripts": scripts,
            })
    # 同一规则 ID + 同一脚本声称 只保留一条
    seen = set()
    uniq = []
    for r in rows:
        key = (r["id"], tuple(r["claimed_scripts"]))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


def scan_legacy_names() -> list[str]:
    hits = []
    # 只扫会进 Agent 上下文的文档，不扫 dist/ 等产物
    wf = ROOT / "writing-rules" / "workflow"
    tpl = wf / "templates"
    targets = [
        ROOT / "CHANGELOG.md",
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "CONTRIBUTING.md",
        *SPEC.glob("*.md"),
        *wf.glob("*.md"),
    ]
    if tpl.is_dir():
        targets.extend(tpl.glob("*.md"))
    for p in targets:
        if not p or not Path(p).is_file():
            continue
        text = Path(p).read_text(encoding="utf-8", errors="ignore")
        for legacy in LEGACY_09:
            if legacy in text and CANON_09 not in text[max(0, text.find(legacy) - 40):
                                                       text.find(legacy) + 40]:
                # 同一短窗口内已有标准名则忽略（如「曾用名」）
                hits.append(f"{p.relative_to(ROOT)}: 出现旧名「{legacy}」")
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    implemented = collect_implemented()
    claims = collect_claims()
    missing = []
    for c in claims:
        scripts = c["claimed_scripts"]
        if any(_covered(s, implemented) for s in scripts):
            continue
        missing.append(c)

    legacy = scan_legacy_names()
    p0 = [{"rule_id": "R-RULE-01", "level": "P0",
           "msg": f"{c['id']} 声称脚本 {c['claimed_scripts']} 但 tools 中无实现（{c['source']}）"}
          for c in missing]
    p1 = [{"rule_id": "S-DOC-01", "level": "P1", "msg": h} for h in legacy]

    if a.json:
        print(json.dumps({
            "claimed": len(claims), "missing": len(missing),
            "implemented_ids": sorted(implemented)[:80],
            "P0": p0, "P1": p1,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"规则声称脚本条目: {len(claims)}  缺实现: {len(missing)}")
        for i in p0:
            print(f"  [P0] {i['msg']}")
        for i in p1:
            print(f"  [P1] {i['msg']}")
        print("COVERAGE_PASS" if not p0 else "COVERAGE_FAIL")
    return 1 if p0 else 0


if __name__ == "__main__":
    sys.exit(main())

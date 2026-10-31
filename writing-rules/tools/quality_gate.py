#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quality_gate.py — 质量优先硬门禁（阶段 / 报告 / 证据 / 代码 / 结构）。

它补的是“内容是否真的好、过程是否真的发生”，不是再加一条文风规则：
  * 阶段：P1 试点章未人签字，不得进入 P2；无人值守只能 draft；
  * 报告：读者/编辑报告必须有“文件:行号 + 原文引句”，4 行报告不再能过；
  * 证据：04_ledger.csv 必须 schema 合法；spec claims 与正文 E-id 必须能回溯；
  * 代码：C# 片段做明显语法/缺括号检查（未标 `illustrative` 即红）；书稿带 `code/` 时再跑一次真实 `dotnet build`；
  * 结构：章末块、重复段落、质量预算。

用法：
  python3 quality_gate.py books/my-book
  python3 quality_gate.py books/my-book --json
  python3 quality_gate.py books/my-book --print-revision

退出码：0 通过 / 1 仅 P1 / 2 有 P0。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wordcount import cjk_len, chinese_len  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]  # playbook 仓库根：repo: 的「本库」

PLACEHOLDER = (
    "待改写", "待定", "TODO", "占位", "请改写", "示例假设",
    "这一节回答什么", "待定章名", "待填",
)

REPORT_QUOTE_RE = re.compile(r"(?P<file>[A-Za-z0-9_./-]+\.md):(?P<line>\d+)")
QUOTE_RE = re.compile(r"「([^」]{4,160})」|“([^”]{4,160})”|\"([^\"]{4,160})\"")
REV_RE = re.compile(r"<!--\s*reviewed_revision:\s*([0-9a-fA-F]{8,64})\s*-->")
CODE_LANGS = {"csharp", "cs", "c#"}
# 门禁结论声称 vs 回执（RPT-11）：报告写「P0=0/零命中/违规 0 处」须能被复跑
GATE_CLAIM_RE = re.compile(r"(?:spec_lint|quality_gate|run_gates|门禁)[^\n]{0,80}?"
                           r"(P0\s*=\s*0|零命中|违规\s*0\s*处|全部通过)")
RECEIPT_RE = re.compile(r"(gate_check|04_check\.json|门禁回执)")
CHAPTER_BLOCK_WORDS = ("本章标尺", "落地", "避坑", "小结")
# 裸语句 `foo.Bar;` 在 C# 方法体内不合法；但 `var x = foo.Bar;`（属性读取赋值）
# 是合法写法，不得误报（F# 案例 `var text = Text.Corpus;`）。
SMELL_STATEMENT = re.compile(r"^\s*[A-Za-z_][\w.]*\s*;\s*$")
KEYWORD_STATEMENTS = {
    "return", "break", "continue", "throw", "yield", "await", "goto",
    "this", "base", "null", "true", "false", "default",
}


def _issue(level: str, rule_id: str, msg: str, path: Path | None = None,
           line: int | None = None) -> dict:
    out = {"level": level, "rule_id": rule_id, "msg": msg}
    if path is not None:
        out["file"] = str(path)
    if line:
        out["line"] = line
    return out


def load_contract(wf: Path) -> dict:
    """`00_大纲合同.json`（可选）。字段：
    word_count_metric（cjk_len|chinese_len）、evidence_policy、deliverables（glob 列表）、
    figures_min、chapter_blocks_required、chapter_blocks_aliases、decay_thresholds。
    """
    return load_json(wf / "00_大纲合同.json") or {}


def count_chars(text: str, metric: str = "cjk_len") -> int:
    if metric == "chinese_len":
        return chinese_len(text)
    return cjk_len(text)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        return ""


def resolve_root(book: Path) -> Path:
    """扁平书根或交付包（manuscript/）布局。"""
    if (book / "02_outline.json").is_file() or (book / "units").is_dir():
        return book
    man = book / "manuscript"
    if man.is_dir() and ((man / "02_outline.json").is_file() or (man / "units").is_dir()):
        return man
    return book


def workflow_dir(book: Path, root: Path) -> Path:
    for cand in (root / "workflow", book / "workflow", root.parent / "workflow"):
        if cand.is_dir():
            return cand
    return root / "workflow"


def unit_files(root: Path) -> list[Path]:
    units = root / "units"
    if not units.is_dir():
        return []
    return sorted(p for p in units.glob("*.md") if not p.name.endswith(".spec.md"))


def revision_hash(root: Path, targets: list[Path] | None = None) -> str:
    """报告审阅版本：默认全书；传 targets 时只 hash 该报告引用的单元。

    章节报告不能因为后一章新增而失效（并行 N+1），所以优先用报告实际引用的
    单元文件；最终报告引用全书，自然 hash 全书。
    """
    h = hashlib.sha256()
    if targets is None:
        units = root / "units"
        files = [p for p in sorted(units.glob("*.md")) if not p.name.endswith(".spec.md")] if units.is_dir() else []
    else:
        expanded: set[Path] = set()
        for p in targets:
            if not p.is_file():
                continue
            expanded.add(p)
            spec = p.with_name(p.stem + ".spec.md")
            if spec.is_file():
                expanded.add(spec)
        files = sorted(expanded)
    for p in files:
        h.update(p.relative_to(root).as_posix().encode("utf-8"))
        h.update(p.read_bytes())
    outline = root / "02_outline.json"
    if targets is None and outline.is_file():
        h.update(b"02_outline.json")
        h.update(outline.read_bytes())
    return h.hexdigest()[:16]


def _looks_empty_template(text: str) -> bool:
    if len(text.strip()) < 200:
        return True
    if "（模板）" in text and "| |" in text:
        return True
    if text.count("待填") + text.count("待确认") >= 3:
        return True
    return False


def revision_chain(root: Path, start: str, want: str) -> bool:
    """revision_log.jsonl（workflow/ 或书根）：每行 {"from": h, "to": h, "reason": "..."}。
    合法修订（标识清理、温度修订）登记迁移链后，旧报告的 reviewed_revision 仍可追溯。"""
    edges: list[tuple[str, str]] = []
    pkg = root.parent if root.name == "manuscript" else None
    cands = [root / "workflow" / "revision_log.jsonl", root / "revision_log.jsonl"]
    if pkg is not None:
        cands += [pkg / "workflow" / "revision_log.jsonl"]
    for cand in cands:
        if not cand.is_file():
            continue
        for ln in read(cand).splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
                edges.append((str(d.get("from")), str(d.get("to"))))
            except Exception:
                continue
    seen, queue = {start}, [start]
    while queue:
        cur = queue.pop()
        if cur == want:
            return True
        for a, b in edges:
            if a == cur and b not in seen:
                seen.add(b)
                queue.append(b)
    return False


def check_gate_claims(wf: Path, p0_total: int) -> list[dict]:
    """报告声称 quality_gate P0=0 而本次实测有 P0 → 声称与实测不符（F# 案例实证）。"""
    if p0_total <= 0 or not wf.is_dir():
        return []
    issues: list[dict] = []
    pat = re.compile(r"quality_gate[^\n]{0,80}?P0\s*=\s*0")
    reports = sorted(wf.glob("01_读者报告*.md")) + sorted(wf.glob("02_编辑审校*.md"))
    final = wf / "06_终审"
    if final.is_dir():
        reports += sorted(final.glob("*.md"))
    for p in reports:
        if pat.search(read(p)):
            issues.append(_issue("P0", "RPT-11",
                                 f"{p.name} 声称 quality_gate P0=0，与本次实测 P0={p0_total} 不符"
                                 "（旧结论须重跑或加 revision/回执）", p))
    return issues


def check_phase(root: Path, wf: Path, outline: dict, state: dict) -> list[dict]:
    issues: list[dict] = []
    p = wf / "00_阶段状态.json"
    if not p.is_file():
        return [_issue("P1", "WF-00", "缺 workflow/00_阶段状态.json（无法证明阶段发生）", p)]
    wf_state = load_json(p) or {}
    phase = str(wf_state.get("phase") or "")
    if phase not in ("P1", "P2", "P3", "P4"):
        return [_issue("P0", "WF-01", f"phase 非法：{phase!r}（只允许 P1–P4）", p)]
    n = int(phase[1])
    human_in_loop = wf_state.get("human_in_loop", True)
    conf = wf_state.get("human_confirmations") or {}
    pilot = conf.get("pilot") or {}
    final = conf.get("final") or {}

    frozen = [
        s for ch in (outline.get("chapters") or [])
        for s in (ch.get("sections") or []) if s.get("status") == "frozen"
    ]
    done = state.get("done_units") or []

    if n >= 2:
        if human_in_loop is False:
            issues.append(_issue("P0", "WF-10",
                                 "human_in_loop=false 时不得进入 P2；无人值守只能停在 P1 并标 draft", p))
        if not (pilot.get("confirmed") is True and str(pilot.get("by") or "").strip()
                and str(pilot.get("at") or "").strip()):
            issues.append(_issue("P0", "WF-11",
                                 "P1 试点章未人签字（human_confirmations.pilot），不得进入 P2", p))
        if wf_state.get("reader_persona_confirmed_by_human") is not True:
            issues.append(_issue("P0", "WF-12", "读者人设未经人确认，不得进入 P2", p))
        decision = str(wf_state.get("rule_conflict_decision") or "")
        if "默示" in decision:
            issues.append(_issue("P0", "WF-13",
                                 "rule_conflict_decision 使用「默示确认」——人工确认不可默示", p))
        if wf_state.get("rule_conflict_status") != "confirmed":
            issues.append(_issue("P0", "WF-14", "大纲×规范融合未 confirmed，不得进入 P2", p))
        for name, label in (("03_作者改进方案.md", "P1 作者改进方案"),
                            ("04_写作宪法.md", "写作宪法"),
                            ("09_大纲×规范融合评估.md", "大纲×规范融合评估"),
                            ("05_章节滚动评估.md", "章节滚动评估")):
            rp = wf / name
            if not rp.is_file():
                issues.append(_issue("P0", "WF-15", f"缺 {name}（{label}）", rp))
                continue
            text = read(rp)
            if _looks_empty_template(text):
                issues.append(_issue("P0", "WF-16", f"{name} 仍是空模板，不能作为 P1/P2 证据", rp))
        plan = read(wf / "03_作者改进方案.md")
        if "- [x]" not in plan.lower() and "已签字" not in plan and "已确认" not in plan:
            issues.append(_issue("P0", "WF-16b",
                                 "03_作者改进方案 确认栏未勾选「人已阅读并同意」",
                                 wf / "03_作者改进方案.md"))
        roll = read(wf / "05_章节滚动评估.md")
        if not re.search(r"^(?:章：|##\s*轮次\s*R)", roll, re.M):
            issues.append(_issue("P0", "WF-16c",
                                 "05_章节滚动评估 没有任何 3 行卡/详评轮次",
                                 wf / "05_章节滚动评估.md"))
        constitution = read(wf / "04_写作宪法.md")
        if "待确认" in constitution and not pilot.get("confirmed"):
            issues.append(_issue("P0", "WF-17",
                                 "04_写作宪法 的确认栏仍是「待确认」，没有人签字",
                                 wf / "04_写作宪法.md"))
        if re.search(r"\|\s*待确认\s*\|", constitution):
            issues.append(_issue("P0", "WF-17b",
                                 "04_写作宪法 的确认行仍为空（| 待确认 | |）",
                                 wf / "04_写作宪法.md"))
        for name in ("09_大纲×规范融合评估.md", "10_篇幅偏差裁定.md"):
            rp = wf / name
            if rp.is_file() and ("待作者复核" in read(rp) or "待复核" in read(rp)):
                issues.append(_issue("P0", "WF-18",
                                     f"{name} 仍是「待复核」，不能作为已确认合同", rp))
        if frozen and not done:
            issues.append(_issue("P0", "WF-19",
                                 f"outline 有 {len(frozen)} 节 frozen，但 05_state.done_units 为空",
                                 root / "05_state.json"))
        elif frozen and set(done) != {s.get("id") for s in frozen}:
            issues.append(_issue("P0", "WF-20",
                                 f"05_state.done_units 与 outline frozen 不一致：{len(done)} vs {len(frozen)}",
                                 root / "05_state.json"))
        stage = str(state.get("stage") or "")
        if n >= 3 and stage in ("S0", "S1", "S2"):
            issues.append(_issue("P0", "WF-21",
                                 f"phase={phase} 但 05_state.stage={stage}，真源不一致",
                                 root / "05_state.json"))
        if n >= 3:
            final_dir = wf / "06_终审"
            files = sorted(final_dir.glob("*.md")) if final_dir.is_dir() else []
            if len(files) < 2:
                issues.append(_issue("P0", "WF-22",
                                     "阶段 3 缺 workflow/06_终审/ 的读者终审与编辑终审",
                                     final_dir))
    if n >= 4:
        if not (final.get("confirmed") is True and str(final.get("by") or "").strip()
                and str(final.get("at") or "").strip()):
            issues.append(_issue("P0", "WF-30", "P4 定稿未人签字（human_confirmations.final）", p))
        feedback = wf / "07_项目反哺报告.md"
        if not feedback.is_file() or _looks_empty_template(read(feedback)):
            issues.append(_issue("P0", "WF-31", "P4 缺实填的 07_项目反哺报告.md", feedback))
        if str(wf_state.get("delivery_status") or "") == "ready" and not final.get("confirmed"):
            issues.append(_issue("P0", "WF-32", "delivery_status=ready 但没有最终人签字", p))

    # 阶段-进度守恒（Avalonia 案例实证）：P1 未人签字只允许试点范围内完稿。
    # 「phase 老实写 P1 但 69 节全写完」是未签字量产的第三种形态，必须拦。
    if n <= 1 and not pilot.get("confirmed"):
        pilot_ch = str((wf_state.get("pilot") or {}).get("chapter") or "").strip()
        allowed = {str(x) for x in ((wf_state.get("pilot") or {}).get("units") or [])}
        out_of_scope = []
        for up in unit_files(root):
            if up.stem in allowed or (pilot_ch and up.stem.startswith(pilot_ch)):
                continue
            if len(read(up).strip()) >= 300:
                out_of_scope.append(up.stem)
        if len(out_of_scope) > 2:
            issues.append(_issue("P0", "WF-24",
                                 f"phase=P1 且试点未人签字，但已有 {len(out_of_scope)} 个试点外单元完稿"
                                 f"（{', '.join(out_of_scope[:5])}…）——P1 只写试点章，禁止未签字量产", p))
        elif out_of_scope:
            issues.append(_issue("P1", "WF-24",
                                 f"phase=P1 试点外已起草 {', '.join(out_of_scope)}（签字前不得继续量产）", p))
    return issues


def _quote_targets(root: Path, rel: str) -> list[Path]:
    rel = rel.replace("\\", "/")
    cands = [root / rel, root / "units" / Path(rel).name, root / "manuscript" / rel]
    return [p for p in cands if p.is_file()]


def check_report_file(path: Path, root: Path, min_quotes: int = 3) -> list[dict]:
    issues: list[dict] = []
    text = read(path)
    if not text.strip():
        return [_issue("P0", "RPT-01", f"{path.name} 为空", path)]
    if len(text) < 800:
        issues.append(_issue("P0", "RPT-02",
                             f"{path.name} 过短（{len(text)} 字符），视为未审阅", path))
    if "（模板）" in text or "评审对象 | 第 __ 章" in text or "日期 | |" in text:
        issues.append(_issue("P0", "RPT-03", f"{path.name} 仍是模板", path))
    matches = list(REPORT_QUOTE_RE.finditer(text))
    if len(matches) < min_quotes:
        issues.append(_issue("P0", "RPT-04",
                             f"{path.name} 只有 {len(matches)} 条「文件:行号」，至少 {min_quotes} 条",
                             path))
    for m in matches:
        rel, no = m.group("file"), int(m.group("line"))
        targets = _quote_targets(root, rel)
        if not targets:
            issues.append(_issue("P1", "RPT-05", f"{path.name} 引用的 {rel} 不在书稿内", path))
            continue
        target = targets[0]
        lines = read(target).splitlines()
        if no < 1 or no > len(lines):
            issues.append(_issue("P0", "RPT-06", f"{path.name} 引用的 {rel}:{no} 行号越界", path))
            continue
        window = "\n".join(lines[max(0, no - 2):no + 1])
        quotes = [q for q in m.groups() if q]
        tail = text[m.end():m.end() + 200]
        qm = QUOTE_RE.search(tail)
        if qm:
            quotes.append(next(g for g in qm.groups() if g))
        if not quotes:
            issues.append(_issue("P1", "RPT-07", f"{path.name} 的 {rel}:{no} 缺原文引句", path))
            continue
        norm = lambda s: re.sub(r"\s+", "", s)
        if not any(norm(q) in norm(window) for q in quotes):
            issues.append(_issue("P0", "RPT-08",
                                 f"{path.name} 的引句在 {rel}:{no} 找不到：{quotes[0][:30]}",
                                 path))
    rev = REV_RE.search(text)
    if rev:
        targets: list[Path] = []
        for m in matches:
            targets.extend(_quote_targets(root, m.group("file")))
        want = revision_hash(root, targets or None)
        if rev.group(1) != want:
            # 合法的后期修订（标识清理、温度修订…）应在 revision_log.jsonl 登记迁移链
            if revision_chain(root, rev.group(1), want):
                issues.append(_issue("P1", "RPT-09",
                                     f"{path.name} 是旧报告，但已登记 revision_log 迁移链（可追溯）",
                                     path))
            else:
                issues.append(_issue("P0", "RPT-09",
                                     f"{path.name} 的 reviewed_revision 与当前稿不一致（旧报告）"
                                     "且无 revision_log 迁移登记", path))
    else:
        issues.append(_issue("P1", "RPT-10",
                             f"{path.name} 缺 reviewed_revision，无法判断是否审的是当前稿", path))
    # 门禁结论可复核：报告写「P0=0/零命中」必须带可重跑回执
    if GATE_CLAIM_RE.search(text) and not RECEIPT_RE.search(text):
        issues.append(_issue("P1", "RPT-11",
                             f"{path.name} 写了门禁结论但无回执；附 <!-- gate_check: … --> 或"
                             "引用 handoff/04_check.json（run_gates --write-check 生成）", path))
    return issues


def check_reports(root: Path, wf: Path) -> list[dict]:
    issues: list[dict] = []
    found = 0
    for pat in ("01_读者报告*.md", "02_编辑审校*.md"):
        for p in sorted(wf.glob(pat)):
            found += 1
            issues.extend(check_report_file(p, root))
    final = wf / "06_终审"
    if final.is_dir():
        for p in sorted(final.glob("*.md")):
            if p.name.startswith(("01_", "02_")):
                found += 1
                issues.extend(check_report_file(p, root))
    if found == 0:
        issues.append(_issue("P1", "RPT-00", "尚无读者/编辑报告（阶段 1 未开始）", wf))
    return issues


def check_evidence(root: Path, outline: dict, contract: dict | None = None) -> list[dict]:
    issues: list[dict] = []
    policy = (contract or {}).get("evidence_policy") or "body-e-tags"
    spec_eids_total = 0
    ledger_p = root / "04_ledger.csv"
    ids: set[str] = set()
    if not ledger_p.is_file():
        issues.append(_issue("P1", "EVD-00", "缺 04_ledger.csv（断言台账）", ledger_p))
    else:
        text = read(ledger_p)
        rows = list(csv.DictReader(text.splitlines()))
        required = {"id", "claim", "level", "source_title", "url", "version",
                    "locator", "cmd", "exit_code", "output_hash", "date", "unit"}
        header = set(rows[0].keys()) if rows else set()
        missing = sorted(required - header)
        if missing:
            issues.append(_issue("P0", "EVD-01", f"台账缺列：{','.join(missing)}", ledger_p))
        repo_hits: dict[str, int] = {}
        for i, r in enumerate(rows, 2):
            rid = str(r.get("id") or "").strip()
            if not re.match(r"^E-\d{3}$", rid):
                issues.append(_issue("P0", "EVD-02",
                                     f"台账第 {i} 行 id 非法/为空（CSV 可能被未转义逗号破坏）",
                                     ledger_p, i))
                continue
            if rid in ids:
                issues.append(_issue("P0", "EVD-03", f"台账 id 重复：{rid}", ledger_p, i))
            ids.add(rid)
            level = str(r.get("level") or "").strip()
            if level not in ("E0", "E1", "E2", "E3"):
                issues.append(_issue("P0", "EVD-04",
                                     f"{rid} 的 level={level!r} 非法（检查未转义逗号）",
                                     ledger_p, i))
                continue
            if level == "E0":
                if not str(r.get("cmd") or "").strip() or not str(r.get("exit_code") or "").strip():
                    issues.append(_issue("P0", "EVD-05", f"{rid} 是 E0 但缺 cmd/exit_code",
                                         ledger_p, i))
                if not str(r.get("output_hash") or "").strip():
                    issues.append(_issue("P1", "EVD-06", f"{rid} 是 E0 但缺 output_hash",
                                         ledger_p, i))
            elif level == "E1":
                for k in ("source_title", "url", "version", "locator"):
                    if not str(r.get(k) or "").strip():
                        issues.append(_issue("P0", "EVD-07", f"{rid} 是 E1 但缺 {k}",
                                             ledger_p, i))
            elif level == "E3":
                blob = " ".join(str(r.get(k) or "") for k in
                                ("claim", "source_title", "locator"))
                if not any(x in blob for x in ("推断", "推测", "未实测")):
                    issues.append(_issue("P0", "EVD-08", f"{rid} 是 E3 但无推断标记",
                                         ledger_p, i))
            # unit 必须能回指写作单元/章（F# 案例 51 行 unit='实验' 无法回溯）
            unit = str(r.get("unit") or "").strip()
            if unit and not re.match(r"^(C\d{1,3}(-S\d{1,2})?|A-?\d+|ch\d+)$", unit):
                issues.append(_issue("P1", "EVD-14",
                                     f"{rid} 的 unit={unit!r} 无法回指单元（应为 C01-S1 / C01 / A1）",
                                     ledger_p, i))
            # url 只接受 https:// 或 repo:（AGENTS §2），且不得泄漏本机路径。
            # E0 证据自带 cmd/exit/hash 可复跑，url 只是辅助 → 非法降 P1；
            # E1/E2 的 url 是来源真源 → P0；本机路径泄漏一律 P0。
            url = str(r.get("url") or "").strip()
            if url:
                if url.startswith("repo:"):
                    repo_hits[url[5:].lstrip("/") or "."] = repo_hits.get(url[5:].lstrip("/") or ".", 0) + 1
                elif re.match(r"^[A-Za-z]:[\\/]", url) or url.startswith("/") or "\\" in url:
                    issues.append(_issue("P0", "EVD-15",
                                         f"{rid} 的 url 是本机路径（泄漏且不可核）：{url[:60]}",
                                         ledger_p, i))
                elif not (url.startswith("https://") or url.startswith("repo:")):
                    issues.append(_issue("P0" if level in ("E1", "E2") else "P1", "EVD-15",
                                         f"{rid} 的 url 须 https:// 或 repo:（现为 {url[:40]}）",
                                         ledger_p, i))
            elif level in ("E1", "E2"):
                issues.append(_issue("P0", "EVD-15", f"{rid} 是 {level} 但缺 url",
                                     ledger_p, i))
        # repo: 引用必须落地（Avalonia 案例：366 条 repo:bookvault 悬空）。
        # 契约上 repo: 指 playbook 本库（REPO_ROOT）；随书工程则解析在书稿内。
        # 交付包布局（root=manuscript/）下 code/ 等在包根，需多解析一跳。
        pkg = root.parent if root.name == "manuscript" else None
        for rel, cnt in sorted(repo_hits.items()):
            cands = [REPO_ROOT / rel, root / rel, root / "manuscript" / rel,
                     root / "code" / rel, root / "manuscript" / "code" / rel]
            if pkg is not None:
                cands += [pkg / rel, pkg / "code" / rel]
            if not any(c.exists() for c in cands):
                issues.append(_issue("P0", "EVD-17",
                                     f"{cnt} 条台账以 repo:{rel} 引用随书文件，但书稿内不存在该路径"
                                     "（可复核性断链：随书工程必须随包交付）", ledger_p))

    units = unit_files(root)
    missing_spec = []
    body_eids: set[str] = set()
    for p in units:
        spec = p.with_name(p.stem + ".spec.md")
        if not spec.is_file():
            missing_spec.append(p.stem)
            continue
        stext = read(spec)
        spec_ids = set(re.findall(r"E-\d{3}", stext))
        spec_eids_total += len(spec_ids)
        if not spec_ids:
            issues.append(_issue("P0", "EVD-09", f"{p.stem}.spec.md 没有任何 E-xxx", spec))
        unknown = spec_ids - ids
        if unknown:
            issues.append(_issue("P0", "EVD-10",
                                 f"{p.stem}.spec.md 引用了台账不存在的 {sorted(unknown)[:5]}",
                                 spec))
        body = read(p)
        beids = set(re.findall(r"E-\d{3}", body))
        body_eids |= beids
        unknown_b = beids - ids
        if unknown_b:
            issues.append(_issue("P0", "EVD-11",
                                 f"{p.stem}.md 引用了台账不存在的 {sorted(unknown_b)[:5]}", p))
    if missing_spec:
        issues.append(_issue("P0", "EVD-12",
                             f"{len(missing_spec)} 个单元缺 spec：{', '.join(missing_spec[:8])}",
                             root / "units"))
    if units and not body_eids:
        # 证据承载策略由 00_大纲合同.evidence_policy 声明、人在融合评估里裁决：
        #   body-e-tags   基线：正文 E-xxx 同句（CLAIM-01 口径）
        #   spec-mapping  证据只进台账，正文/段落经 spec claims 映射
        #   visible-markers 正文用中文可见标记（【已验证】/「无法验证（未实测）」）
        if policy == "body-e-tags":
            issues.append(_issue("P1", "EVD-13",
                                 "全书正文没有 E-xxx；若采用「章末证据表/脚注」，请显式提供映射，否则读者无法复核数字",
                                 root / "units"))
        elif policy == "spec-mapping":
            if not spec_eids_total:
                issues.append(_issue("P1", "EVD-13",
                                     "policy=spec-mapping：正文无 E-xxx，spec claims 也无 E-id，证据无任何映射",
                                     root / "units"))
        elif policy == "visible-markers":
            markers = (contract or {}).get("evidence_markers") or \
                ["无法验证（未实测）", "本机实测", "官方", "推断", "未实测"]
            blob = "".join(read(p) for p in units)
            if not any(m in blob for m in markers):
                issues.append(_issue("P1", "EVD-13",
                                     f"policy=visible-markers：正文未见任何可见证据标记 {markers[:3]}",
                                     root / "units"))
        else:
            issues.append(_issue("P0", "EVD-16",
                                 f"evidence_policy 非法：{policy!r}（可选 body-e-tags|spec-mapping|visible-markers）",
                                 root / "units"))
    return issues


def _strip_strings(line: str) -> str:
    return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', line)


def _code_block_issues(block: list[str], start: int,
                       path: Path | None = None) -> list[dict]:
    issues: list[dict] = []
    clean = "\n".join(_strip_strings(x) for x in block)
    for op, cl in (("{", "}"), ("(", ")"), ("[", "]")):
        if clean.count(op) != clean.count(cl):
            issues.append(_issue("P1", "CODE-01", f"代码块括号不平衡：{op}{cl}", path, start))
            break
    for idx, raw in enumerate(block):
        j = start + idx
        s = raw.strip()
        if not s or s.startswith("//") or s.startswith("#"):
            continue
        if re.search(r"\(\s*=>", s):
            issues.append(_issue("P0", "CODE-02", "lambda 缺形参（形如 `( => ...`）", path, j))
        if SMELL_STATEMENT.match(s):
            head = s.split(";")[0].strip()
            word = re.split(r"[.\s]", head)[0]
            if word not in KEYWORD_STATEMENTS and not head.startswith(("using ", "return ", "throw ")):
                issues.append(_issue("P0", "CODE-03",
                                     f"裸语句缺调用括号（形如 `foo.Bar;`）：{s[:60]}", path, j))
        if re.search(r"\bnew\s+[A-Z]\w*\s*$", s):
            # 多行 new（下一行以 { 或 ( 开头的对象初始化器/换行构造实参）合法
            nxt = ""
            for nx in block[idx + 1:]:
                if nx.strip():
                    nxt = nx.strip()
                    break
            if not nxt.startswith(("{", "(")):
                issues.append(_issue("P0", "CODE-04", f"new 缺构造括号：{s[:60]}", path, j))
    return issues


def check_code(root: Path) -> list[dict]:
    issues: list[dict] = []
    for p in unit_files(root):
        lines = read(p).splitlines()
        in_code = False
        lang = ""
        block: list[str] = []
        start = 0
        illustrative = False
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("```"):
                if not in_code:
                    in_code = True
                    lang = s[3:].strip().lower()
                    block = []
                    start = i
                    ctx = "\n".join(lines[max(0, i - 3):i])
                    illustrative = lang not in CODE_LANGS or any(
                        x in ctx for x in ("illustrative", "示意", "未在本机运行", "伪代码", "不可运行")
                    )
                else:
                    in_code = False
                    if lang in CODE_LANGS and not illustrative:
                        issues.extend(_code_block_issues(block, start, p))
                continue
            if in_code:
                block.append(line)
    return issues


def check_code_project(root: Path) -> list[dict]:
    """书稿若带 code/ 工程，跑一次真实 dotnet build；无 code/ 则跳过。"""
    code = root / "code"
    if not code.is_dir():
        return []
    projects = sorted(list(code.glob("*.sln")) + list(code.glob("*.slnx"))
                      + list(code.glob("*.csproj")))
    if not projects:
        return []
    dotnet = shutil.which("dotnet")
    if not dotnet:
        return [_issue("P1", "CODE-00", "书稿有 code/ 但本机无 dotnet，未做真实编译", code)]
    r = subprocess.run([dotnet, "build", str(projects[0]), "--nologo"],
                       cwd=code, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        tail = "\n".join((r.stdout + r.stderr).splitlines()[-8:])
        return [_issue("P0", "CODE-05", f"code/ 编译失败：{tail}", code)]
    return []


def check_structure(root: Path, outline: dict, contract: dict | None = None) -> list[dict]:
    issues: list[dict] = []
    metric = (contract or {}).get("word_count_metric") or "cjk_len"
    units = unit_files(root)
    seen: dict[str, str] = {}
    for p in units:
        text = read(p)
        heads = re.findall(r"^(#{1,3})\s+\S", text, re.M)
        if not heads or len(heads) < 2:
            issues.append(_issue("P1", "QG-01", f"{p.stem} 缺一级/二级标题结构", p))
        for para in re.split(r"\n\s*\n", text):
            s = re.sub(r"\s+", "", para)
            if len(s) >= 100 and not para.lstrip().startswith(("#", "|", "```", ">")):
                if s in seen and seen[s] != p.stem:
                    issues.append(_issue("P1", "QG-02",
                                         f"{p.stem} 与 {seen[s]} 存在重复长段落", p))
                seen[s] = p.stem
    last = {}
    for ch in (outline.get("chapters") or []):
        secs = ch.get("sections") or []
        if secs:
            last[ch.get("id")] = secs[-1].get("id")
    unruled: list[str] = []
    for p in units:
        if p.stem not in last.values():
            continue
        text = read(p)
        miss = [w for w in CHAPTER_BLOCK_WORDS if w not in text]
        if miss:
            issues.append(_issue("P1", "QG-03",
                                 f"{p.stem} 作为章末节缺：{', '.join(miss)}", p))
        # 章末固定块的承载形态必须由合同显式裁决（09 融合评估 + 人签字）：
        #   chapter_blocks_as_headings: true  → 允许「## 本章标尺/## 落地/## 避坑」检查点小节
        #   false                             → 必须行文承载（F# 案例裁定）
        #   未声明却在用标题                    → QG-06 未裁决（Avalonia 案例实证）
        # form_freedom=true（申报制）时 QG-05/06 降 P1，好坏由人签字裁决。
        if any(re.search(rf"^#{{2,4}}\s*{re.escape(w)}\s*[:：]?\s*$", text, re.M)
               for w in CHAPTER_BLOCK_WORDS):
            as_head = (contract or {}).get("chapter_blocks_as_headings")
            soft = "P1" if (contract or {}).get("form_freedom") is True else "P0"
            if as_head is False:
                w = next(w for w in CHAPTER_BLOCK_WORDS
                         if re.search(rf"^#{{2,4}}\s*{re.escape(w)}\s*[:：]?\s*$", text, re.M))
                issues.append(_issue(soft, "QG-05",
                                     f"{p.stem} 把章末四件事写成挂牌标题「## {w}」（合同裁定行文承载）",
                                     p))
            elif as_head is True:
                pass
            else:
                unruled.append(p.stem)
    if unruled:
        soft = "P1" if (contract or {}).get("form_freedom") is True else "P0"
        issues.append(_issue(soft, "QG-06",
                             f"{len(unruled)} 个单元把章末固定块写成小节标题，但 00_大纲合同 未声明 "
                             "chapter_blocks_as_headings——须在 09 融合评估裁决「标题承载（true）」或"
                             f"「行文承载（false）」并由人签字（{', '.join(unruled[:5])}…）",
                             root / "units"))
    words = {s.get("id"): int(s.get("words") or 0)
             for ch in (outline.get("chapters") or []) for s in (ch.get("sections") or [])}
    for p in units:
        budget = words.get(p.stem, 0)
        if budget:
            n = count_chars(read(p), metric)
            if n < int(budget * 0.8):
                issues.append(_issue("P1", "QG-04",
                                     f"{p.stem} 仅 {n} 字（口径 {metric}），低于质量预算 0.8×{budget}",
                                     p))
    return issues


def check_contract_deliverables(root: Path, contract: dict | None = None) -> list[dict]:
    """合同交付物清单：`deliverables`（glob 列表）与 `figures_min`。
    F# 案例：合同承诺 48 章 + 附录 A–J，交付只有一份 80 字节占位——缺项必须红。
    """
    issues: list[dict] = []
    pkg = root.parent if root.name == "manuscript" else None
    for g in (contract or {}).get("deliverables") or []:
        hit = list(root.glob(str(g))) or (pkg is not None and list(pkg.glob(str(g))))
        if not hit:
            issues.append(_issue("P0", "CTR-01", f"合同交付物缺失：{g}", root))
            continue
        # P22：glob 存在 ≠ 齐备——空目录/0 字节文件是空壳（Avalonia 实证：探针
        # 复制脚本挂了，空目录却被 glob「撞中」判齐备）
        def _alive(x: Path) -> bool:
            if x.is_file():
                return x.stat().st_size > 0
            return x.is_dir() and any(f.is_file() for f in x.rglob("*"))
        if not any(_alive(x) for x in hit):
            issues.append(_issue("P0", "CTR-01", f"合同交付物是空壳（无有效内容）：{g}", root))
    figs_min = (contract or {}).get("figures_min")
    if figs_min:
        n = 0
        for base in [root] + ([pkg] if pkg is not None else []):
            if n:
                break
            for d in ("typst/chapters", "typst", "chapters"):
                p = base / d
                if p.is_dir():
                    n = sum(read(f).count("#fig(") for f in p.glob("*.typ"))
                    break
        if n < int(figs_min):
            issues.append(_issue("P0", "CTR-02", f"图数量 {n} 低于合同下限 {figs_min}", root))
    return issues


def check_chapter_blocks(root: Path, contract: dict | None = None) -> list[dict]:
    """合同骨架块（`chapter_blocks_required`）按章核查；
    `chapter_blocks_aliases` 允许融合后的别名（如「来源对照 → 验证清单」）。"""
    req = (contract or {}).get("chapter_blocks_required") or []
    if not req:
        return []
    aliases = (contract or {}).get("chapter_blocks_aliases") or {}
    issues: list[dict] = []
    bych: dict[str, list[Path]] = {}
    for p in unit_files(root):
        m = re.match(r"^(C\d{1,3})", p.stem)
        bych.setdefault(m.group(1) if m else "_", []).append(p)
    hit: dict[str, int] = {str(b): 0 for b in req}
    missing: list[tuple[str, str]] = []
    for ch in sorted(bych):
        if ch == "_":
            continue
        blob = "\n".join(read(p) for p in bych[ch])
        heads = "\n".join(re.findall(r"^#{2,4}\s*(.+?)\s*$", blob, re.M))
        for b in req:
            alts = [str(b)] + [str(x) for x in (aliases.get(b) or [])]
            if any(a in heads or a in blob for a in alts):
                hit[str(b)] += 1
            else:
                missing.append((ch, str(b)))
    # 全书无命中 = 命名与融合方案不一致（配置 chapter_blocks_aliases），单点报告；
    # 有命中但个别章缺 = 真缺块，逐章报告（封顶，防刷屏）
    for b, n in hit.items():
        if n == 0:
            issues.append(_issue("P1", "CTR-04",
                                 f"合同骨架块「{b}」全书零命中（疑与融合后命名不符；配置 chapter_blocks_aliases）",
                                 root))
    real_missing = [(c, b) for c, b in missing if hit.get(b, 0) > 0]
    for ch, b in real_missing[:20]:
        issues.append(_issue("P1", "CTR-03",
                             f"{ch} 缺合同骨架块「{b}」（该块在其他章存在，属本章漏写）",
                             bych[ch][0]))
    if len(real_missing) > 20:
        issues.append(_issue("P1", "CTR-03",
                             f"其余 {len(real_missing) - 20} 处骨架块缺失已省略", root))
    return issues


def check_decay(root: Path, contract: dict | None = None) -> list[dict]:
    """批量衰减检测：按章聚合体量/纪律/spec 完整度，首 ⅓ 与末 ⅓ 对比。
    质量优先要求「尾章不得加速」——量产到后半程的松劲必须被工具抓住（F# 案例
    C18 起挂牌、C27 起无练习、C42 起 spec 塌缩全部漏检）。
    """
    issues: list[dict] = []
    try:
        from spec_lint import WORD2CAT, LABEL_HEAD_RE, LABEL_BLOCK_HEAD_RE  # 同一真源
    except Exception:
        return issues
    metric = (contract or {}).get("word_count_metric") or "cjk_len"
    th = (contract or {}).get("decay_thresholds") or {}
    drop_ratio = float(th.get("length_drop_ratio", 0.55))
    defect_growth = float(th.get("defect_growth", 2.0))
    cov_drop = float(th.get("spec_cov_drop", 0.3))
    bych: dict[str, list[Path]] = {}
    for p in unit_files(root):
        m = re.match(r"^(C\d{1,3})", p.stem)
        if m:
            bych.setdefault(m.group(1), []).append(p)
    chs = sorted(bych, key=lambda x: int(x[1:]))
    if len(chs) < 6:
        return issues
    k = max(2, len(chs) // 3)
    agg: list[tuple[str, float, float, float]] = []
    for ch in chs:
        lens, defects, cov = [], 0, 0
        for p in bych[ch]:
            t = read(p)
            lens.append(count_chars(t, metric))
            defects += sum(t.count(w) for w in WORD2CAT)
            defects += len(LABEL_HEAD_RE.findall(t)) + len(LABEL_BLOCK_HEAD_RE.findall(t))
            sp = p.with_name(p.stem + ".spec.md")
            if sp.is_file() and re.search(r"E-\d{3}", read(sp)):
                cov += 1
        agg.append((ch, sum(lens) / len(lens), defects / len(lens), cov / len(lens)))

    def avg(idx: int, rows) -> float:
        return sum(r[idx] for r in rows) / len(rows)

    first_len, last_len = avg(1, agg[:k]), avg(1, agg[-k:])
    if first_len > 0 and last_len < first_len * drop_ratio:
        issues.append(_issue("P0", "DECAY-01",
                             f"体量衰减：前 {k} 章均 {first_len:.0f} 字 → 末 {k} 章均 {last_len:.0f} 字"
                             f"（<{drop_ratio:.0%}，口径 {metric}）", root))
    elif first_len > 0 and last_len < first_len * min(0.75, drop_ratio + 0.2):
        issues.append(_issue("P1", "DECAY-01",
                             f"体量走低：前 {k} 章均 {first_len:.0f} 字 → 末 {k} 章均 {last_len:.0f} 字"
                             f"（<{min(0.75, drop_ratio + 0.2):.0%}）", root))
    first_def, last_def = avg(2, agg[:k]), avg(2, agg[-k:])
    if last_def > first_def * defect_growth + 2:
        issues.append(_issue("P0", "DECAY-02",
                             f"纪律衰减：禁用词/挂牌前 {k} 章均 {first_def:.1f} → 末 {k} 章均 {last_def:.1f}",
                             root))
    elif last_def > first_def + 1:
        issues.append(_issue("P1", "DECAY-02",
                             f"纪律走低：禁用词/挂牌前 {k} 章均 {first_def:.1f} → 末 {k} 章均 {last_def:.1f}",
                             root))
    first_cov, last_cov = avg(3, agg[:k]), avg(3, agg[-k:])
    if first_cov - last_cov > cov_drop:
        issues.append(_issue("P0", "DECAY-03",
                             f"证据衰减：spec 带 E-id 比例前 {k} 章 {first_cov:.0%} → 末 {k} 章 {last_cov:.0%}",
                             root))
    elif first_cov - last_cov > cov_drop * 0.5:
        issues.append(_issue("P1", "DECAY-03",
                             f"证据走低：spec 带 E-id 比例前 {k} 章 {first_cov:.0%} → 末 {k} 章 {last_cov:.0%}",
                             root))
    return issues


def check_state_sanity(root: Path, wf: Path, state: dict) -> list[dict]:
    """阶段状态 sanity：notes_brief 被逐字符污染是记忆脚本/append 误用的指纹；
    workflow 提到工具自改/自造而 07 反哺未登记（F#、Avalonia 两案的工具漂移指纹）。"""
    issues: list[dict] = []
    for i, nb in enumerate(state.get("notes_brief") or []):
        if isinstance(nb, str) and 0 < len(nb.strip()) < 2:
            issues.append(_issue("P1", "WF-23",
                                 f"notes_brief[{i}] 是单字符 {nb!r}（疑似字符串被逐字符写入）",
                                 wf / "00_阶段状态.json"))
            break
    drift_re = re.compile(r"修工具|工具缺陷|自造工具|自建工具|prose_check|工具补丁")
    drift_hits = [rp.name for rp in sorted(wf.glob("*.md"))
                  if drift_re.search(read(rp))]
    if drift_hits:
        fb = wf / "07_项目反哺报告.md"
        if not fb.is_file() or _looks_empty_template(read(fb)):
            issues.append(_issue("P1", "WF-25",
                                 f"workflow 提到工具修改/自造（{', '.join(drift_hits[:3])}）"
                                 "但 07_项目反哺报告.md 仍是空模板——工具改动须登记并回流本仓库",
                                 fb))
    return issues


def _signoff_covers(entry: dict, unit: str) -> bool:
    """签字条目覆盖某单元：units 显式列出，或 chapters 以章前缀覆盖。"""
    if unit in {str(x) for x in (entry.get("units") or [])}:
        return True
    return any(unit.startswith(f"{c}-") for c in (entry.get("chapters") or []))


def check_signoffs(root: Path, wf: Path, outline: dict) -> list[dict]:
    """章循环批量：frozen 单元必须有人签字覆盖（WF-26），空签字无效（WF-27）。
    这是「超长任务切短 + 每批人校准」的执行保障。"""
    issues: list[dict] = []
    wf_state = load_json(wf / "00_阶段状态.json") or {}
    signoffs = [s for s in (wf_state.get("chapter_signoffs") or []) if isinstance(s, dict)]
    frozen = {s.get("id") for ch in (outline.get("chapters") or [])
              for s in (ch.get("sections") or []) if s.get("status") == "frozen"}
    if not frozen:
        frozen = {str(x) for x in (wf_state.get("done_units") or [])}
    for i, s in enumerate(signoffs):
        if not str(s.get("by") or "").strip() or not str(s.get("at") or "").strip():
            issues.append(_issue("P0", "WF-27",
                                 f"chapter_signoffs[{i}] 缺签字人/时间", wf / "00_阶段状态.json"))
        if not str(s.get("notes") or "").strip():
            issues.append(_issue("P0", "WF-27",
                                 f"chapter_signoffs[{i}] 签字记录为空——必须写明"
                                 "「改了什么/裁了什么」，空签字无效", wf / "00_阶段状态.json"))
    uncovered = sorted(u for u in frozen if u and
                       not any(_signoff_covers(s, u) for s in signoffs))
    if uncovered:
        issues.append(_issue("P0", "WF-26",
                             f"{len(uncovered)} 个 frozen 单元无人签字覆盖"
                             f"（{', '.join(uncovered[:5])}…）——章循环批量：人签的批次才能冻结",
                             wf / "00_阶段状态.json"))
    return issues


def check_deviations(root: Path, wf: Path) -> list[dict]:
    """偏离申报制：有意的形式发挥登记 deviations.jsonl，人签字时逐条裁决。
    未裁决 → P1 待人；已签字覆盖却未裁决 → P0（签字走过场）。"""
    issues: list[dict] = []
    p = wf / "deviations.jsonl"
    if not p.is_file():
        return issues
    entries = []
    for ln in read(p).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            entries.append(json.loads(ln))
        except Exception:
            issues.append(_issue("P1", "DEV-00", f"deviations.jsonl 行不是合法 JSON：{ln[:40]}", p))
    wf_state = load_json(wf / "00_阶段状态.json") or {}
    signoffs = [s for s in (wf_state.get("chapter_signoffs") or []) if isinstance(s, dict)]
    for e in entries:
        eid = str(e.get("id") or "?")
        unit = str(e.get("unit") or "")
        if not str(e.get("rule") or "").strip() or not str(e.get("reason") or "").strip():
            issues.append(_issue("P1", "DEV-01", f"{eid} 缺 rule/reason（偏离须说明为什么）", p))
            continue
        if e.get("ruled") in ("追认", "收敛"):
            continue
        covering = [s for s in signoffs if _signoff_covers(s, unit)]
        ruled_ids = " ".join(str(x) for s in covering
                             for x in (s.get("deviations_ruled") or []))
        if covering and eid not in ruled_ids:
            issues.append(_issue("P0", "DEV-02",
                                 f"{eid}（{unit}）所在批次已签字，但偏离未裁决"
                                 "——签字时必须逐条写「追认/收敛」，否则是走过场", p))
        else:
            issues.append(_issue("P1", "DEV-01",
                                 f"{eid}（{unit}）待人裁决（追认=入宪法 / 收敛=记反例）", p))
    return issues


def check_spec_and_blocks(root: Path) -> list[dict]:
    """P23 两查：spec↔ledger 错挂对账（EVD-18/19）+ 片段示意注记后缺代码块（QG-07）。

    Avalonia 内容审校实证：spec 主张整表 +10 错挂 E 号三处（主张与台账 claim
    逐字相同却挂错行，肉眼全对、机器可查）；「片段示意：下方代码块…」注记在而
    代码块丢失 7+ 处。EVD-18（挂不存在的 E 号）P0；EVD-19（主张与台账 claim
    不像，疑似错挂）P1 提示。
    """
    import difflib
    issues: list[dict] = []
    ledger_claims: dict[str, str] = {}
    lp = root / "04_ledger.csv"
    if lp.is_file():
        for r in csv.DictReader(read(lp).splitlines()):
            rid = str(r.get("id") or "").strip()
            if rid:
                ledger_claims[rid] = str(r.get("claim") or "")
    for p in unit_files(root):
        # ① 片段示意注记后 12 行内必须出现代码块
        lines = read(p).splitlines()
        in_code = False
        for i, ln in enumerate(lines):
            if ln.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if "片段示意" in ln and "代码块" in ln:
                window = lines[i + 1: i + 13]
                if not any(s.strip().startswith("```") for s in window):
                    issues.append(_issue("P0", "QG-07",
                                         f"片段示意注记后缺代码块（{p.name}:{i + 1}）",
                                         p, i + 1))
        # ② spec 主张行的 E 号必须存在，且与台账 claim 对得上
        spec = p.with_name(p.stem + ".spec.md")
        if not spec.is_file():
            continue
        for j, ln in enumerate(read(spec).splitlines(), 1):
            m = re.match(r"^\|\s*A\d+\s*\|(.+?)\|(?:[^|]*)\|(?:[^|]*)\|([^|]*)\|", ln)
            if not m:
                continue
            em = re.search(r"E-\d{3}", m.group(2))
            if not em:
                continue
            eid = em.group(0)
            if eid not in ledger_claims:
                issues.append(_issue("P0", "EVD-18",
                                     f"{spec.name}:{j} 挂了台账不存在的 {eid}",
                                     spec, j))
                continue
            claim = m.group(1).strip()
            lc = ledger_claims[eid]
            if claim and lc and difflib.SequenceMatcher(None, claim, lc).ratio() < 0.5:
                # 收紧口径（P23-5 调优）：只有当主张明显更像另一条台账时才提示
                # 错挂并给出应挂 E 号；措辞近似不足不打扰
                best_eid, best_ratio = "", 0.0
                for cand, cl in ledger_claims.items():
                    ratio = difflib.SequenceMatcher(None, claim, cl).ratio()
                    if ratio > best_ratio:
                        best_eid, best_ratio = cand, ratio
                if best_eid and best_eid != eid and best_ratio >= 0.7:
                    issues.append(_issue(
                        "P1", "EVD-19",
                        f"{spec.name}:{j} 疑似错挂 {eid}：主张与 {best_eid} 的台账 claim "
                        f"几乎相同（相似度 {best_ratio:.2f}）", spec, j))
    return issues


def run_checks(book: Path) -> tuple[list[dict], list[dict]]:
    book = book.resolve()
    root = resolve_root(book)
    wf = workflow_dir(book, root)
    outline = load_json(root / "02_outline.json") or {}
    state = load_json(root / "05_state.json") or {}
    contract = load_contract(wf) if wf.is_dir() else {}
    issues: list[dict] = []
    if outline:
        issues += check_structure(root, outline, contract)
    if wf.is_dir():
        issues += check_phase(root, wf, outline, state)
        issues += check_reports(root, wf)
        issues += check_state_sanity(root, wf, state)
        issues += check_signoffs(root, wf, outline)
        issues += check_deviations(root, wf)
    if (root / "04_ledger.csv").is_file() or unit_files(root):
        issues += check_evidence(root, outline, contract)
        issues += check_spec_and_blocks(root)
    issues += check_code(root)
    issues += check_code_project(root)
    issues += check_contract_deliverables(root, contract)
    issues += check_chapter_blocks(root, contract)
    issues += check_decay(root, contract)
    issues += check_gate_claims(wf, len([i for i in issues if i["level"] == "P0"]))
    p0 = [i for i in issues if i["level"] == "P0"]
    p1 = [i for i in issues if i["level"] != "P0"]
    return p0, p1


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--print-revision", action="store_true",
                    help="打印 reviewed_revision（默认全书；可用 --units 限定章节）")
    ap.add_argument("--units", default="",
                    help="逗号分隔的单元 ID，如 C01-S1,C01-S2；用于章节报告")
    a = ap.parse_args()
    if a.print_revision:
        root = resolve_root(Path(a.book_dir).resolve())
        targets = []
        for sid in (x.strip() for x in a.units.split(",")):
            if sid:
                targets.append(root / "units" / f"{sid}.md")
        print(revision_hash(root, targets or None))
        return 0
    p0, p1 = run_checks(Path(a.book_dir))
    if a.json:
        print(json.dumps({"P0": p0, "P1": p1}, ensure_ascii=False, indent=2))
    else:
        print(f"QUALITY_GATE P0={len(p0)} P1={len(p1)}")
        for i in p0 + p1:
            loc = f" {i.get('file')}" if i.get("file") else ""
            print(f"  [{i['level']}] {i['rule_id']}: {i['msg']}{loc}")
        print("QUALITY_GATE_PASS" if not p0 else "QUALITY_GATE_FAIL")
    return 2 if p0 else (1 if p1 else 0)


if __name__ == "__main__":
    sys.exit(main())

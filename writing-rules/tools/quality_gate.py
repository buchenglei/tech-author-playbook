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
from wordcount import cjk_len  # noqa: E402

PLACEHOLDER = (
    "待改写", "待定", "TODO", "占位", "请改写", "示例假设",
    "这一节回答什么", "待定章名", "待填",
)

REPORT_QUOTE_RE = re.compile(r"(?P<file>[A-Za-z0-9_./-]+\.md):(?P<line>\d+)")
QUOTE_RE = re.compile(r"「([^」]{4,160})」|“([^”]{4,160})”|\"([^\"]{4,160})\"")
REV_RE = re.compile(r"<!--\s*reviewed_revision:\s*([0-9a-fA-F]{8,64})\s*-->")
CODE_LANGS = {"csharp", "cs", "c#"}
CHAPTER_BLOCK_WORDS = ("本章标尺", "落地", "避坑", "小结")
SMELL_STATEMENT = re.compile(
    r"^\s*(?:var\s+[A-Za-z_]\w*\s*=\s*)?[A-Za-z_][\w.]*\s*;\s*$"
)
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


def _nonempty_data_rows(text: str) -> int:
    n = 0
    for ln in text.splitlines():
        s = ln.strip()
        if not s.startswith("|"):
            continue
        if set(s.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len([c for c in cells if c]) >= 2 and cells[0] not in ("项", "维度", "#", "文件名"):
            n += 1
    return n


def _looks_empty_template(text: str) -> bool:
    if len(text.strip()) < 200:
        return True
    if "（模板）" in text and "| |" in text:
        return True
    if text.count("待填") + text.count("待确认") >= 3:
        return True
    return False


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
            issues.append(_issue("P0", "RPT-09",
                                 f"{path.name} 的 reviewed_revision 与当前稿不一致（旧报告）", path))
    else:
        issues.append(_issue("P1", "RPT-10",
                             f"{path.name} 缺 reviewed_revision，无法判断是否审的是当前稿", path))
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


def check_evidence(root: Path, outline: dict) -> list[dict]:
    issues: list[dict] = []
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
        issues.append(_issue("P1", "EVD-13",
                             "全书正文没有 E-xxx；若采用「章末证据表/脚注」，请显式提供映射，否则读者无法复核数字",
                             root / "units"))
    return issues


def _strip_strings(line: str) -> str:
    return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', line)


def _code_block_issues(block: list[str], start: int) -> list[dict]:
    issues: list[dict] = []
    clean = "\n".join(_strip_strings(x) for x in block)
    for op, cl in (("{", "}"), ("(", ")"), ("[", "]")):
        if clean.count(op) != clean.count(cl):
            issues.append(_issue("P1", "CODE-01", f"代码块括号不平衡：{op}{cl}", None, start))
            break
    for j, raw in enumerate(block, start):
        s = raw.strip()
        if not s or s.startswith("//") or s.startswith("#"):
            continue
        if re.search(r"\(\s*=>", s):
            issues.append(_issue("P0", "CODE-02", "lambda 缺形参（形如 `( => ...`）", None, j))
        if SMELL_STATEMENT.match(s):
            head = s.split(";")[0].strip()
            word = re.split(r"[.\s]", head)[0]
            if word not in KEYWORD_STATEMENTS and not head.startswith(("using ", "return ", "throw ")):
                issues.append(_issue("P0", "CODE-03",
                                     f"语句像属性访问、缺调用括号：{s[:60]}", None, j))
        if re.search(r"\bnew\s+[A-Z]\w*\s*$", s):
            issues.append(_issue("P0", "CODE-04", f"new 缺构造括号：{s[:60]}", None, j))
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
                        issues.extend(_code_block_issues(block, start))
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


def check_structure(root: Path, outline: dict) -> list[dict]:
    issues: list[dict] = []
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
    for p in units:
        if p.stem not in last.values():
            continue
        text = read(p)
        miss = [w for w in CHAPTER_BLOCK_WORDS if w not in text]
        if miss:
            issues.append(_issue("P1", "QG-03",
                                 f"{p.stem} 作为章末节缺：{', '.join(miss)}", p))
    words = {s.get("id"): int(s.get("words") or 0)
             for ch in (outline.get("chapters") or []) for s in (ch.get("sections") or [])}
    for p in units:
        budget = words.get(p.stem, 0)
        if budget and cjk_len(read(p)) < int(budget * 0.8):
            issues.append(_issue("P1", "QG-04",
                                 f"{p.stem} 仅 {cjk_len(read(p))} 字，低于质量预算 0.8×{budget}",
                                 p))
    return issues


def run_checks(book: Path) -> tuple[list[dict], list[dict]]:
    book = book.resolve()
    root = resolve_root(book)
    wf = workflow_dir(book, root)
    outline = load_json(root / "02_outline.json") or {}
    state = load_json(root / "05_state.json") or {}
    issues: list[dict] = []
    if outline:
        issues += check_structure(root, outline)
    if wf.is_dir():
        issues += check_phase(root, wf, outline, state)
        issues += check_reports(root, wf)
    if (root / "04_ledger.csv").is_file() or unit_files(root):
        issues += check_evidence(root, outline)
    issues += check_code(root)
    issues += check_code_project(root)
    p0 = [i for i in issues if i["level"] == "P0"]
    p1 = [i for i in issues if i["level"] != "P0"]
    return p0, p1


def main() -> int:
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

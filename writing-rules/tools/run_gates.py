#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_gates.py — 一次跑完 G0–G8（G8 含 quality_gate），只打印紧凑结果（省 Token）。

门禁语义：
  - G4（A/B/C 条件实验证据）未实现：默认 SKIP 并注明；--require-g4 强制执行。
  - 门禁单调：G8 有 P0 时 G7 强制 FAIL（禁止「G7 PASS + G8 FAIL」）。
  - --write-check 把本次回执写 handoff/04_check.json（报告写门禁结论时须引用）。

用法：
  python3 run_gates.py books/my-book
  python3 run_gates.py books/my-book --json
  python3 run_gates.py books/my-book --write-check
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINT = ROOT / "writing-rules" / "tools" / "spec_lint.py"
QUALITY = ROOT / "writing-rules" / "tools" / "validate_quality.py"


def run_gate(which: str, base: Path, evidence_policy: str = "body-e-tags",
             allow_block_headings: bool = False, soft_form: bool = False) -> dict:
    cmd = [sys.executable, str(LINT), "--gate", which, str(base), "--json",
           "--evidence-policy", evidence_policy]
    if allow_block_headings:
        cmd.append("--allow-block-headings")
    if soft_form:
        cmd.append("--soft-form")
    rr = subprocess.run(cmd, capture_output=True)
    # 子进程输出是 UTF-8；text=True 在 GBK 机器上会解码崩溃（stdout 变 None）
    out = rr.stdout.decode("utf-8", errors="replace") if rr.stdout else ""
    err = rr.stderr.decode("utf-8", errors="replace") if rr.stderr else ""
    try:
        data = json.loads(out)
    except Exception:
        return {"gate": which, "ok": False, "issues": [{"msg": (out + err)[:200]}]}
    p0, p1 = data.get("P0") or [], data.get("P1") or []
    return {"gate": which, "ok": not p0, "P0": len(p0), "P1": len(p1),
            "issues": (p0 + p1)[:5]}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip", default="", help="跳过门禁，逗号分隔，如 G4")
    ap.add_argument("--require-g4", action="store_true",
                    help="强制执行未实现的 G4（默认 SKIP：诚实标注，不再永久 HAS_FAIL）")
    ap.add_argument("--write-check", action="store_true",
                    help="把本次门禁回执写入 handoff/04_check.json（报告引用门禁结论时必须有）")
    a = ap.parse_args()
    book = Path(a.book_dir).resolve()
    skip = {s.strip().upper() for s in a.skip.split(",") if s.strip()}
    # 书稿合同声明的证据承载策略/固定块标题裁决透传给 spec_lint
    policy = "body-e-tags"
    allow_block_headings = False
    soft_form = False
    for cand in (book / "workflow" / "00_大纲合同.json",
                 book / "manuscript" / "workflow" / "00_大纲合同.json"):
        try:
            c = json.loads(cand.read_text(encoding="utf-8-sig"))
            policy = c.get("evidence_policy") or policy
            allow_block_headings = c.get("chapter_blocks_as_headings") is True
            soft_form = c.get("form_freedom") is True
            break
        except Exception:
            continue
    results = []
    worst = 0
    for g in ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"):
        if g in skip:
            results.append({"gate": g, "ok": True, "skipped": True})
            continue
        if g == "G4" and not a.require_g4:
            results.append({"gate": g, "ok": True, "skipped": True,
                            "why": "G4（A/B/C 条件实验证据）未实现：默认 SKIP；--require-g4 强制执行"})
            continue
        res = run_gate(g, book, evidence_policy=policy,
                       allow_block_headings=allow_block_headings, soft_form=soft_form)
        results.append(res)
        if not res.get("ok"):
            worst = 2
    # G8 质量/体量/流程真实性
    if "G8" not in skip:
        rr = subprocess.run(
            [sys.executable, str(QUALITY), str(book), "--json"],
            capture_output=True,
        )
        out = rr.stdout.decode("utf-8", errors="replace") if rr.stdout else ""
        err = rr.stderr.decode("utf-8", errors="replace") if rr.stderr else ""
        try:
            q = json.loads(out)
        except Exception:
            q = {"P0": [{"msg": (out + err)[:200]}], "P1": []}
        p0, p1 = q.get("P0") or [], q.get("P1") or []
        res = {"gate": "G8", "ok": not p0, "P0": len(p0), "P1": len(p1),
               "issues": (p0 + p1)[:6]}
        results.append(res)
        if not res.get("ok"):
            worst = 2
        # 门禁单调性：G8（质量/流程）未过时，G7 不得报 PASS（发布门禁不成立）
        if p0:
            for r in results:
                if r.get("gate") == "G7" and r.get("ok") and not r.get("skipped"):
                    r["ok"] = False
                    r.setdefault("issues", []).append({
                        "level": "P0", "rule_id": "G7",
                        "msg": "依赖 G8：质量/流程门禁未过，发布门禁不成立（门禁单调性）"})
                    worst = 2
    if a.write_check:
        try:
            git_rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                     capture_output=True, cwd=ROOT)
            git_rev = git_rev.stdout.decode("utf-8", errors="replace").strip() or None
        except Exception:
            git_rev = None
        rec = {
            "generated_by": "writing-rules/tools/run_gates.py",
            "command": f"run_gates.py {book}" + (" --require-g4" if a.require_g4 else ""),
            "checked_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            # 回执必须能复现：记 git rev 与工具版本（Avalonia 案例：无版本的门禁结论事后无法对账）
            "git_rev": git_rev,
            "toolchain": {"python": sys.version.split()[0]},
            "evidence_policy": policy,
            "chapter_blocks_as_headings": allow_block_headings,
            "form_freedom": soft_form,
            "gates": [{"gate": r.get("gate"), "ok": bool(r.get("ok")),
                       "skipped": bool(r.get("skipped")),
                       "P0": r.get("P0", 0), "P1": r.get("P1", 0)} for r in results],
            "summary": {"all_pass": worst == 0},
        }
        target = book / "handoff" / "04_check.json"
        if not target.parent.is_dir():
            target = book / "manuscript" / "handoff" / "04_check.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {target}")
    if a.json:
        print(json.dumps({"book": str(book), "results": results}, ensure_ascii=False, indent=2))
        return worst
    for res in results:
        if res.get("skipped"):
            print(f"{res['gate']} SKIP" + (f"（{res['why']}）" if res.get("why") else ""))
            continue
        mark = "PASS" if res.get("ok") else "FAIL"
        extra = f"P0={res.get('P0', 0)} P1={res.get('P1', 0)}" if "P0" in res else ""
        print(f"{res['gate']} {mark} {extra}")
        for i in res.get("issues") or []:
            print(f"    [{i.get('level', '?')}] {i.get('rule_id', i.get('msg', ''))}: {i.get('msg', '')[:80]}")
    print("ALL_PASS" if worst == 0 else "HAS_FAIL")
    return worst


if __name__ == "__main__":
    sys.exit(main())

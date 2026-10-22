#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_gates.py — 一次跑完 G0–G7，只打印紧凑结果（省 Token）。

用法：
  python3 run_gates.py books/my-book
  python3 run_gates.py books/my-book --json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINT = ROOT / "writing-rules" / "tools" / "spec_lint.py"


def run_gate(which: str, base: Path) -> dict:
    r = subprocess.run(
        [sys.executable, str(LINT), "--gate", which, str(base), "--json"],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(r.stdout)
    except Exception:
        return {"gate": which, "ok": False, "issues": [{"msg": (r.stdout + r.stderr)[:200]}]}
    p0, p1 = data.get("P0") or [], data.get("P1") or []
    return {"gate": which, "ok": not p0, "P0": len(p0), "P1": len(p1),
            "issues": (p0 + p1)[:5]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book_dir")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip", default="", help="跳过门禁，逗号分隔，如 G4")
    a = ap.parse_args()
    book = Path(a.book_dir).resolve()
    skip = {s.strip().upper() for s in a.skip.split(",") if s.strip()}
    results = []
    worst = 0
    for g in ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"):
        if g in skip:
            results.append({"gate": g, "ok": True, "skipped": True})
            continue
        res = run_gate(g, book)
        results.append(res)
        if not res.get("ok"):
            worst = 2
    if a.json:
        print(json.dumps({"book": str(book), "results": results}, ensure_ascii=False, indent=2))
        return worst
    for res in results:
        if res.get("skipped"):
            print(f"{res['gate']} SKIP")
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

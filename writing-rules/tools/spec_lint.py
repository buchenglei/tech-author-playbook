#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""spec_lint.py — 《技术书籍写作规范 v1》配套校验器

设计原则（对应规范）：
  1. 校验由脚本执行，不由 Agent 自评（§7.1 L0）。
  2. 规则总表由正文派生，不手写（BOOK-08：单一真源）。
  3. 每条 MUST 必须有判定方式，否则降级（RULE-01）。
  4. 输出机器可读（--json），便于按 rule_id 定位修复。

用法：
  python3 spec_lint.py <file.md> [--profile spec|manuscript] [--json] [--strict]
  python3 spec_lint.py <file.md> --registry --write     # 生成/更新附录 A 规则总表
  python3 spec_lint.py --gate G0|G1|G2|G3|G4|G6|G7 [dir]

退出码：0 通过 / 1 有 P1 / 2 有 P0
"""

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wordcount import chinese_len, cjk_len  # noqa: E402  统一字数口径

# ---------------------------------------------------------------- 规则数据

DOMAIN_ORDER = ["RULE", "ENG", "TOP", "AUD", "STR", "UNIT", "DEM",
                "LANG", "HUMOR", "FMT", "CITE", "TIME", "VER", "BOOK",
                "TEAM", "CLAIM", "B", "F"]

DOMAIN_NAME = {
    "RULE": "执行契约", "ENG": "作者能力", "TOP": "立项", "AUD": "读者",
    "STR": "结构", "UNIT": "单元", "DEM": "族别要求", "LANG": "语言",
    "HUMOR": "风趣", "FMT": "呈现", "CITE": "引用", "TIME": "时效",
    "VER": "校验", "BOOK": "书稿工程", "TEAM": "交接", "CLAIM": "断言",
    "B": "资产", "F": "校准",
}

# 脚手架/模板占位：G1/G2/G3 不得把它们当真实内容放行。
PLACEHOLDER_TERMS = ("示例假设", "请改写", "待改写", "待定", "TODO", "占位",
                     "这一节回答什么", "待定章名", "待填")

# 禁用词（§6.3）。四类，命中即改。
FORBIDDEN = OrderedDict([
    ("空泛强调", ["注意", "重要", "务必", "千万", "显然", "众所周知", "不言而喻", "毋庸置疑"]),
    ("主观评价", ["强大", "优雅", "高效", "完美", "极致", "丰富", "灵活", "轻松", "简单", "容易"]),
    ("营销话术", ["一键", "开箱即用", "一站式", "业界领先", "最佳实践"]),
    ("填充过渡", ["首先", "其次", "接下来", "值得注意的是", "不难看出"]),
])

WORD2CAT = {w: c for c, ws in FORBIDDEN.items() for w in ws}

# 允许出现的上下文：定义规则、反例、词表本身
WHITELIST_MARKERS = ("禁止", "不得", "禁用", "反例", "不合格", "病句",
                     "白名单", "为什么禁", "替换", "词表")
WHITELIST_SECTIONS = ("禁用词", "句法病灶", "文风样例")
# 上下文白名单：反例常跨行（"**不合格**（...）：" 在上一行，例句在下一行）
CONTEXT_MARKERS = ("不合格", "反例", "病句", "禁止", "不得", "禁用")
# 词内误报：这些复合词里的"注意"不是强调词
EXEMPT_COMPOUNDS = ("注意力", "注意到")

# 风趣检查（§6.8）：技术书的幽默靠事实反差，不靠标点
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")
ECHO_RE = re.compile(r"[！!]{2,}")
ONOMATOPOEIA = ("啪", "嗖", "duang", "哇塞", "哈哈")

MAX_SENT = 60          # LANG-05（附录 F 待校准）
MAX_PARA_SENTS = 6     # LANG-11
MIN_PARA_AVG = 20      # LANG-12（低于此值提示碎片化）

RULE_RE = re.compile(r"\*\*([A-Z]{1,6}-\d{2})\*\*（([^）]*)）")
ID_TOKEN_RE = re.compile(r"(?<![A-Za-z-])([A-Z]{1,6}-\d{2})(?![0-9])")
ID_CELL_RE = re.compile(r"^([A-Z]{1,6}-\d{2})$")
XREF_RE = re.compile(r"§(\d+(?:\.\d+)*)")
HEAD_RE = re.compile(r"^(#{1,4})\s+(.*)$")
CODE_RE = re.compile(r"^\s*```")

# ---------------------------------------------------------------- 工具函数


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def split_lines(text):
    """返回 [(行号, 行, 是否在代码块内, 当前二级标题)]"""
    out = []
    in_code = False
    section = ""
    for i, line in enumerate(text.splitlines(), 1):
        if CODE_RE.match(line):
            out.append((i, line, True, section))
            in_code = not in_code
            continue
        m = HEAD_RE.match(line)
        if m and not in_code:
            # H1 也作为 section 兜底：附录 B/F 没有 H2，否则规则会被挂到上一分片的末节。
            if len(m.group(1)) in (1, 2):
                section = m.group(2).strip()
            out.append((i, line, False, section))
            continue
        out.append((i, line, in_code, section))
    return out


def sentences(text):
    """中文句子切分，去 markdown 标记。

    口径修正（F# 案例回归）：
      - HTML 注释（`<!-- src: ... -->` 之类）不参与句长/句数；
      - 双反引号 ``...`..`` 整体先折叠，再折单反引号；
      - 行内代码折算为单字符；
      - 纯西文/数字片段（无汉字）不算中文句子，避免英文引文误报 LANG-05/11/12。
    """
    t = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    t = re.sub(r"``.*?``", "X", t, flags=re.S)
    t = re.sub(r"`[^`]*`", "X", t)
    t = re.sub(r"\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"[*_#>]", "", t)
    out = []
    for p in re.split(r"[。！？；]", t):
        p = p.strip()
        if chinese_len(p) < 4:
            continue
        # 纯西文/数字片段不是中文句子
        if len(re.findall(r"[\u4e00-\u9fff]", p)) < 2:
            continue
        out.append(p)
    return out


def paragraphs(lines):
    """连续非空、非表格、非代码行视为一段。产出 (起始行号, 句列表, 所在小节)。"""
    buf, start, sec = [], None, ""
    for no, line, in_code, section in lines:
        s = line.strip()
        bullet = bool(re.match(r"^([-*+]\s|\d+[.)]\s)", s))
        is_rule = bool(re.match(r"^\*\*[A-Z]{1,6}-\d{2}\*\*", s))
        empty = (not s) or in_code or s.startswith("|") or is_rule \
            or bullet or s.startswith("---") and set(s) <= {"-", " "}
        if empty:
            if buf:
                yield start, buf, sec
                buf, start = [], None
            continue
        if start is None:
            start, sec = no, section
        buf.append(s)
    if buf:
        yield start, buf, sec


# ---------------------------------------------------------------- 规则注册


def collect_rules(text):
    """从正文收集规则定义。标准形式优先，表格登记作为补充。"""
    rules = OrderedDict()
    table_only = set()
    dup = []

    for no, line, in_code, section in split_lines(text):
        if in_code:
            continue
        for m in RULE_RE.finditer(line):
            rid, attrs = m.group(1), m.group(2)
            parts = [p.strip() for p in attrs.split("｜")]
            entry = {
                "id": rid,
                "domain": rid.split("-")[0],
                "strength": parts[0] if parts else "",
                "check": parts[1] if len(parts) > 1 else "",
                "action": parts[2] if len(parts) > 2 else "",
                "section": section,
                "line": no,
                "form": "standard",
            }
            if rid in rules:
                dup.append((rid, no))
            else:
                rules[rid] = entry

    # 表格里的 ID 单元（如 6.1 的规则表）：只证明"被提到过"，不给强度
    for no, line, in_code, section in split_lines(text):
        if in_code or not line.strip().startswith("|"):
            continue
        for cell in [c.strip() for c in line.strip().strip("|").split("|")]:
            if ID_CELL_RE.match(cell):
                rid = cell
                if rid not in rules:
                    table_only.add(rid)
                    rules[rid] = {
                        "id": rid, "domain": rid.split("-")[0],
                        "strength": "", "check": "", "action": "",
                        "section": section, "line": no, "form": "table",
                    }
    return rules, table_only, dup


# ---------------------------------------------------------------- 各类检查


def check_rules(text, rules, table_only, dup, extra_ids=frozenset(), profile="spec"):
    p0, p1, p2 = [], [], []

    for rid, e in rules.items():
        if e["form"] == "table":
            p2.append({
                "rule_id": "S-RULE-02", "level": "P2", "line": e["line"],
                "msg": f"{rid} 只在表格中出现，未按标准格式登记强度/判定/失败动作",
            })
            continue
        if not e["strength"]:
            p1.append({"rule_id": "S-RULE-02", "level": "P1", "line": e["line"],
                       "msg": f"{rid} 缺强度"})
        if e["strength"] == "MUST" and (not e["check"] or not e["action"]):
            p1.append({"rule_id": "RULE-01", "level": "P1", "line": e["line"],
                       "msg": f"{rid} 是 MUST 但缺判定或失败动作，应降级为 SHOULD"})

    # MUST 的失败动作只能是阻断：标了 MUST 却只"登记"，等于给自己留后门
    for rid, e in rules.items():
        if e["form"] == "standard" and e["strength"] == "MUST" and e["action"] == "登记":
            p1.append({"rule_id": "S-RULE-05", "level": "P1", "line": e["line"],
                       "msg": f"{rid} 标为 MUST 但失败动作是登记，应降为 SHOULD"})
        if e["form"] == "standard" and e["strength"] == "SHOULD" and e["action"] == "阻断":
            p2.append({"rule_id": "S-RULE-05", "level": "P2", "line": e["line"],
                       "msg": f"{rid} 标为 SHOULD 但失败动作是阻断，强度与动作不匹配"})

    for rid, no in dup:
        p1.append({"rule_id": "S-RULE-04", "level": "P1", "line": no,
                   "msg": f"{rid} 重复定义（第二次出现在第 {no} 行）"})

    # 正文提到但从未定义的 ID（仅规范正文需自洽；书稿引用规范 ID 不必自定义）
    if profile != "manuscript":
        for no, line, in_code, section in split_lines(text):
            if in_code:
                continue
            for m in ID_TOKEN_RE.finditer(line):
                rid = m.group(1)
                # 只把已知规范域当规则 ID；C-05 是宪法条款，不是规则。
                if rid.split("-", 1)[0] not in DOMAIN_NAME:
                    continue
                if rid.startswith(("S-", "L-", "E-", "LANG-")) and rid not in rules:
                    # S-/L- 是脚本内部编号；LANG- 若未定义仍需报
                    if not rid.startswith("LANG-"):
                        continue
                if rid not in rules and rid not in extra_ids:
                    p0.append({"rule_id": "S-RULE-01", "level": "P0", "line": no,
                               "msg": f"引用了不存在的规则 {rid}"})
    total = len([r for r in rules.values() if r["form"] == "standard"])
    must_n = len([r for r in rules.values() if r["strength"] == "MUST"])
    if total and must_n / total > 0.7:
        p2.append({"rule_id": "S-RULE-06", "level": "P2", "line": 0,
                   "msg": f"MUST 占比 {must_n}/{total}={must_n/total:.0%}，确认已区分单元级门禁与发布级红线（§7.4）"})
    return p0, p1, p2


def check_xref(text, headings):
    out = []
    for no, line, in_code, _ in split_lines(text):
        if in_code:
            continue
        for m in XREF_RE.finditer(line):
            ref = m.group(1)
            if ref not in headings:
                out.append({"rule_id": "L-XREF-01", "level": "P0", "line": no,
                            "msg": f"交叉引用 §{ref} 的目标不存在"})
    return out


def check_headings(text):
    out, last = [], 2
    for no, line, in_code, _ in split_lines(text):
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+", line)
        if not m:
            continue
        lvl = len(m.group(1))
        if lvl > last + 1:
            out.append({"rule_id": "S-HEAD-01", "level": "P1", "line": no,
                        "msg": f"标题层级从 H{last} 跳到 H{lvl}"})
        last = lvl
    return out


def check_forbidden(text):
    out = []
    lines = text.splitlines()
    for no, line, in_code, section in split_lines(text):
        if in_code or not line.strip():
            continue
        if any(s in section for s in WHITELIST_SECTIONS):
            continue
        # 上下文两行：反例的标签行在例句上一行
        ctx = "\n".join(lines[max(0, no - 3):no - 1])
        if any(m in line for m in WHITELIST_MARKERS) or any(m in ctx for m in CONTEXT_MARKERS):
            continue
        probe = line
        for ex in EXEMPT_COMPOUNDS:
            probe = probe.replace(ex, "")
        for w, cat in WORD2CAT.items():
            if w in probe:
                out.append({"rule_id": "L-LANG-01", "level": "P0", "line": no,
                            "msg": f"禁用词「{w}」（{cat}）",
                            "quote": line.strip()[:70]})
    return out


def check_humor(text):
    """§6.8：拟声词、emoji、连用感叹号。密度靠自检，形态靠脚本。"""
    out = []
    for no, line, in_code, section in split_lines(text):
        if in_code or exempt_section(section):
            continue
        if any(m in line for m in WHITELIST_MARKERS):
            continue
        if EMOJI_RE.search(line):
            out.append({"rule_id": "L-HUMOR-01", "level": "P0", "line": no,
                        "msg": "出现 emoji", "quote": line.strip()[:60]})
        if ECHO_RE.search(line):
            out.append({"rule_id": "L-HUMOR-01", "level": "P0", "line": no,
                        "msg": "感叹号连用", "quote": line.strip()[:60]})
        for w in ONOMATOPOEIA:
            if w in line:
                out.append({"rule_id": "L-HUMOR-01", "level": "P0", "line": no,
                            "msg": f"拟声词「{w}」", "quote": line.strip()[:60]})
    return out


def exempt_section(section):
    """文风样例是刻意展示的病句与长段，不参与语言检查。"""
    return section in WHITELIST_SECTIONS or bool(re.match(r"^H[.．]", section or ""))


def check_sentence_len(text):
    out = []
    for no, line, in_code, section in split_lines(text):
        if in_code or exempt_section(section):
            continue
        s = line.strip()
        if not s or s.startswith("|") or s.startswith("```"):
            continue
        for sent in sentences(s):
            n = chinese_len(sent)
            if n > MAX_SENT:
                out.append({"rule_id": "LANG-05", "level": "P1", "line": no,
                            "msg": f"句长 {n} 字（上限 {MAX_SENT}）",
                            "quote": sent[:80]})
    return out


def check_paragraphs(text, profile):
    out = []
    if profile != "manuscript" and profile != "spec":
        return out
    for start, buf, sec in paragraphs(split_lines(text)):
        if exempt_section(sec):
            continue
        body = "".join(buf)
        sents = sentences(body)
        if not sents:
            continue
        if len(sents) > MAX_PARA_SENTS:
            out.append({"rule_id": "LANG-11", "level": "P1", "line": start,
                        "msg": f"段落 {len(sents)} 句（上限 {MAX_PARA_SENTS}）"})
        avg = sum(chinese_len(s) for s in sents) / len(sents)
        if avg < MIN_PARA_AVG and chinese_len(body) > 80:
            out.append({"rule_id": "LANG-12", "level": "P2", "line": start,
                        "msg": f"段落均句长 {avg:.0f} 字，低于 {MIN_PARA_AVG}，疑为逗号碎片化"})
    return out


def check_tables(text):
    out = []
    header_cols, header_line = None, None
    for no, line, in_code, _ in split_lines(text):
        if in_code:
            continue
        s = line.strip()
        if not s.startswith("|"):
            header_cols, header_line = None, None
            continue
        cols = len([c for c in s.strip("|").split("|")])
        if set(s.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue  # 分隔行
        if header_cols is None:
            header_cols, header_line = cols, no
            continue
        if cols != header_cols:
            out.append({"rule_id": "L-FMT-01", "level": "P1", "line": no,
                        "msg": f"表格列数 {cols} 与表头 {header_cols} 不一致（表头在第 {header_line} 行）"})
    return out


def check_code_fences(text):
    out, opened = [], None
    for no, line, _, _ in split_lines(text):
        m = re.match(r"^\s*```(\S*)\s*$", line)
        if not m:
            continue
        if opened is None:
            opened = (no, m.group(1))
        else:
            if opened[1] == "":
                out.append({"rule_id": "L-FMT-02", "level": "P1",
                            "line": opened[0], "msg": "代码块未标语言"})
            opened = None
    if opened:
        out.append({"rule_id": "L-FMT-02", "level": "P1", "line": opened[0],
                    "msg": "代码块未闭合"})
    return out


SPEC_FIELDS = ("id", "question", "bridge", "layer", "produces", "claims",
               "evidence", "concepts_introduced", "concepts_used", "code", "word_budget")


def check_unit_files(path):
    """UNIT-01 / UNIT-02 / UNIT-14：spec 先于正文、十一项、代码块溯源标注。"""
    out = []
    p = Path(path)
    if not p.is_file() or p.suffix != ".md" or p.name.endswith(".spec.md"):
        return out
    # 只对 units/Cxx-Sxx.md 形态生效
    if not re.match(r"^[A-Za-z]{1,4}\d{0,3}-S\d+", p.stem):
        return out
    spec_p = p.with_name(p.stem + ".spec.md")
    if not spec_p.is_file():
        out.append({"rule_id": "S-UNIT-01", "level": "P0", "line": 0,
                    "msg": f"缺 {spec_p.name}（UNIT-01：spec 必须先于正文）"})
    else:
        stext = spec_p.read_text(encoding="utf-8", errors="ignore")
        missing = [f for f in SPEC_FIELDS if f not in stext]
        if missing:
            out.append({"rule_id": "S-SPEC-01", "level": "P0", "line": 0,
                        "msg": f"{spec_p.name} 缺十一项字段：{','.join(missing)}"})
    # UNIT-14：代码块须 src:/path: 或同节 E-xxx 台账锚
    text = p.read_text(encoding="utf-8", errors="ignore")
    fences = list(re.finditer(r"^```(\w+)", text, re.M))
    if fences and "src:" not in text and "path:" not in text and not re.search(r"E-\d{3}", text) \
            and "无代码" not in text:
        out.append({"rule_id": "S-CODE-01", "level": "P1", "line": 0,
                    "msg": "含代码块但无 src:/path: 与 E-xxx 溯源（UNIT-14）"})
    return out


def check_symmetry(text):
    """连续小节字数高度雷同 → 结构对称填充（UNIT-09）。"""
    out, blocks = [], []
    cur, cnt = None, 0
    for no, line, in_code, _ in split_lines(text):
        if in_code:
            continue
        if re.match(r"^#{2,3}\s+", line):
            if cur:
                blocks.append((cur[0], cur[1], cnt))
            cur, cnt = (no, line.strip("# ").strip()), 0
        elif cur:
            cnt += chinese_len(line)
    if cur:
        blocks.append((cur[0], cur[1], cnt))

    run = 0
    for i in range(1, len(blocks)):
        a, b = blocks[i - 1][2], blocks[i][2]
        if a > 400 and b > 400 and abs(a - b) / max(a, b) < 0.04:
            run += 1
            if run >= 2:
                out.append({"rule_id": "L-SYM-01", "level": "P2", "line": blocks[i][0],
                            "msg": f"连续 {run + 1} 节字数几乎相同（{blocks[i-2][2]} / {a} / {b}），疑为对称填充"})
        else:
            run = 0
    return out


# 手册腔：认知链挂牌标题（UNIT-21 / LANG-19）
# 含「去冒号」变体：`## 小结`、`## 机制` 这类裸词标题同样是表单腔
#（F# 案例 C42-S3 实证）。带后缀的人话标题（如「小结与官方锚点」「会踩的坑」）不命中。
LABEL_HEAD_RE = re.compile(
    r"^#{2,4}\s*(现象|机制|证据|代价|误区|收束|小结)\s*(?:[:：]\s*\S|\s*$)"
)
# 章末固定块词（本章标尺/落地/避坑）：默认也拦，但合同 chapter_blocks_as_headings=true
#（09 融合评估人签字）时豁免——大纲合同要求固定块的书可能合法地用检查点小节。
LABEL_BLOCK_HEAD_RE = re.compile(
    r"^#{2,4}\s*(本章标尺|落地|避坑)\s*(?:[:：]\s*\S|\s*$)"
)
# 附录/规范自身豁免
FORM_EXEMPT_SECTION = ("附录", "禁用词", "句法病灶", "文风样例", "规则总表", "速查", "模板索引",
                       "门禁", "故障", "三族", "待校准", "术语表")


def check_form_labels(text, profile="manuscript", allow_block_headings=False):
    """正文禁止「现象：…」式挂牌小节；附录/工具书豁免。
    allow_block_headings=True 时豁免章末固定块词（合同 chapter_blocks_as_headings=true）。"""
    out = []
    for no, line, in_code, section in split_lines(text):
        if in_code:
            continue
        if any(x in (section or "") for x in FORM_EXEMPT_SECTION):
            continue
        s = line.strip()
        hit = LABEL_HEAD_RE.match(s) or (not allow_block_headings and LABEL_BLOCK_HEAD_RE.match(s))
        if hit:
            out.append({"rule_id": "L-FORM-01", "level": "P0", "line": no,
                        "msg": "挂牌式小节标题（认知链应溶解在行文，不进标题）",
                        "quote": s[:60]})
    return out


def check_table_density(text, profile="manuscript"):
    """每节（一个正文文件）表格 ≤2 张（UNIT-22 / LANG-20）。附录/速查节豁免。"""
    out = []
    lines = split_lines(text)
    n = 0
    for i, (no, line, in_code, section) in enumerate(lines):
        s = line.strip()
        if in_code or not s.startswith("|"):
            continue
        prev_pipe = i > 0 and lines[i - 1][1].strip().startswith("|")
        if not prev_pipe:
            n += 1
    # 全文件若落在附录/速查等豁免标题下则不报
    if n > 2:
        heads = " ".join(l for _, l, _, _ in lines if re.match(r"^#\s+", l.strip()))
        if any(x in heads for x in FORM_EXEMPT_SECTION):
            return out
        out.append({"rule_id": "L-FORM-02", "level": "P2", "line": 0,
                    "msg": f"本节表格 {n} 张（建议 ≤2，自由区可偏离并登记；附录豁免）"})
    return out


NUM_UNIT_RE = re.compile(r"(?<![\d.])(\d{3,}|\d+\.\d+)\s*(ms|s|GB|MB|%|万|次|条)")
EID_RE = re.compile(r"E-\d{3}")


EVIDENCE_POLICIES = ("body-e-tags", "spec-mapping", "visible-markers")
# 注意：不要放裸「实测」二字（「实测结果显示」会被误当标记）；标记须是可判定短语
VISIBLE_MARKERS_RE = re.compile(r"已验证|待核实|无法验证|未实测|本机实测|官方文档|官方|推断")


def check_claims(text, ledger_ids=None, evidence_policy="body-e-tags"):
    """manuscript：带单位的数字必须与证据同句（CLAIM-01）。

    口径由 `00_大纲合同.evidence_policy` 决定（人在融合评估里裁决）：
      body-e-tags    基线：数字句必须带 E-xxx（P0）
      spec-mapping   证据只进台账/spec claims；数字句缺 E-xxx 降 P1（仍建议可回溯）
      visible-markers 正文用中文可见标记；数字句有「已验证/无法验证（未实测）/官方/推断…」即合规
    引用了不存在的 E-xxx 一律 P0（与策略无关）。
    """
    out = []
    for start, buf, _sec in paragraphs(split_lines(text)):
        body = "".join(buf)
        if "```" in body and not NUM_UNIT_RE.search(body):
            continue
        # 按句扫描，而不是整段跳过
        for sent in re.split(r"(?<=[。！？；\n])", body):
            nums = list(NUM_UNIT_RE.finditer(sent))
            if not nums:
                continue
            eids = EID_RE.findall(sent)
            if not eids:
                if evidence_policy == "spec-mapping":
                    out.append({"rule_id": "L-CLAIM-01", "level": "P1", "line": start,
                                "msg": f"policy=spec-mapping：数字「{nums[0].group(0)}」句内无 E-xxx（证据在台账，建议脚注/标记）"})
                elif evidence_policy == "visible-markers":
                    if not VISIBLE_MARKERS_RE.search(sent):
                        out.append({"rule_id": "L-CLAIM-01", "level": "P0", "line": start,
                                    "msg": f"policy=visible-markers：数字「{nums[0].group(0)}」句内无可见证据标记"})
                else:
                    out.append({"rule_id": "L-CLAIM-01", "level": "P0", "line": start,
                                "msg": f"数字「{nums[0].group(0)}」未关联台账 E-xxx"})
                continue
            if ledger_ids is not None:
                known = [e for e in eids if e in ledger_ids]
                if not known:
                    out.append({"rule_id": "L-CLAIM-01", "level": "P0", "line": start,
                                "msg": f"数字「{nums[0].group(0)}」引用的 {eids[0]} 不在台账中"})
    return out


def check_cite(text):
    out = []
    for no, line, in_code, _ in split_lines(text):
        if in_code or line.strip().startswith("|"):
            continue
        for m in re.finditer(r"(?<!\()https?://[^\s)\]，。]+", line):
            out.append({"rule_id": "L-CITE-01", "level": "P2", "line": no,
                        "msg": f"裸链接（缺标题/版本/locator）：{m.group(0)[:50]}"})
    return out


# ---------------------------------------------------------------- 规则总表


def render_registry(rules, path):
    rows = [r for r in rules.values() if r["form"] == "standard"]
    rows.sort(key=lambda r: (DOMAIN_ORDER.index(r["domain"]) if r["domain"] in DOMAIN_ORDER else 99,
                             int(r["id"].split("-")[1])))

    must = sum(1 for r in rows if r["strength"] == "MUST")
    should = sum(1 for r in rows if r["strength"] == "SHOULD")
    may = sum(1 for r in rows if r["strength"] == "MAY")

    lines = [
        f"共 **{len(rows)}** 条：MUST {must} / SHOULD {should} / MAY {may}。",
        "",
        f"本表由 `python3 tools/spec_lint.py spec/ --registry --write` 从正文生成。"
        "**修改规则只需改正文，不要改这里**——手改会在下一次生成时被覆盖，且脚本会报不一致。",
        "",
        "| 域 | ID | 强度 | 判定 | 失败动作 | 所在小节 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        name = DOMAIN_NAME.get(r["domain"], r["domain"])
        lines.append(f"| {name} | {r['id']} | {r['strength']} | {r['check']} | {r['action']} | {r['section']} |")

    lines += [
        "",
        "**读法**：",
        "",
        "- 按 `域` 过滤，只加载当前阶段的行（§0.5）。",
        "- `判定` 为 `脚本` 的，失败即阻断，不接受解释；为 `自检` 的，须按 §7.5 附证据。",
        "- `判定` 为 `交接` 的，不得由 Agent 标记通过（VER-01）。",
        "",
    ]
    return "\n".join(lines)


def write_registry(path, table):
    text = read(path)
    begin, end = "<!-- REGISTRY:BEGIN -->", "<!-- REGISTRY:END -->"
    if begin not in text or end not in text:
        print("!! 未找到 REGISTRY 标记，无法写入", file=sys.stderr)
        return False
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    new = f"{head}{begin}\n\n{table}\n{end}{tail}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return True


def registry_in_sync(text, table):
    begin, end = "<!-- REGISTRY:BEGIN -->", "<!-- REGISTRY:END -->"
    if begin not in text:
        return True
    cur = text.split(begin, 1)[1].split(end, 1)[0].strip()
    want = table.strip()
    return cur == want


# ---------------------------------------------------------------- 门禁

GATE_FILES = {
    "G0": ("01_立项卡.json", "00_立项卡.json", "立项卡.json"),
    "G1": ("08_读者假设.md", "09_读者假设.md", "01_读者.md", "读者假设.md", "reader.md"),
    "G2": ("02_outline.json", "01_outline.json", "outline.json"),
    "G6": ("00_README.md", "01_outline.json", "02_glossary.json",
           "03_ledger.csv", "04_check.json", "05_unverified.md"),
}


def _valid_source_url(url):
    """E1 来源定位：允许 http(s) 外链或 repo: 仓库内相对路径。不写死托管平台。"""
    u = str(url or "").strip()
    if not u:
        return False
    if u.startswith(("http://", "https://")):
        return True
    return u.startswith("repo:")


def gate(which, base, evidence_policy="body-e-tags", allow_block_headings=False):
    issues = []

    def need(name):
        p = os.path.join(base, name)
        return p if os.path.isfile(p) else None

    if which == "G0":
        p = None
        for c in GATE_FILES["G0"]:
            p = p or need(c)
        if not p:
            return [{"rule_id": "G0", "level": "P0", "msg": "缺立项卡（01_立项卡.json）"}]
        try:
            d = json.loads(read(p))
        except Exception as e:
            return [{"rule_id": "G0", "level": "P0", "msg": f"立项卡不是合法 JSON：{e}"}]
        for k in ("title", "claim", "increment", "reader_before",
                  "reader_after", "scope_in", "scope_out", "prerequisites",
                  "sources", "risk", "kill_criteria"):
            if k not in d:
                issues.append({"rule_id": "TOP-01", "level": "P0", "msg": f"立项卡缺字段 {k}"})
        # 空值不算填：模板能"看起来通过"是门禁最典型的失效
        if not str(d.get("claim", "")).strip():
            issues.append({"rule_id": "TOP-01", "level": "P0", "msg": "claim 为空"})
        if not str(d.get("title", "")).strip():
            issues.append({"rule_id": "TOP-01", "level": "P0", "msg": "title 为空"})
        if not d.get("reader_after"):
            issues.append({"rule_id": "AUD-09", "level": "P0", "msg": "reader_after 为空"})
        so = [x for x in d.get("scope_out", [])
              if str(x.get("item", "") if isinstance(x, dict) else x).strip()]
        if len(so) < 3:
            issues.append({"rule_id": "TOP-02", "level": "P0",
                           "msg": f"scope_out 有效条目 {len(so)} 条（需 ≥3 且不得为空）"})
        kc = [x for x in d.get("kill_criteria", []) if str(x).strip()]
        if len(kc) < 2:
            issues.append({"rule_id": "TOP-01", "level": "P0",
                           "msg": f"kill_criteria 有效条目 {len(kc)} 条（需 ≥2）"})
        e1 = [s for s in d.get("sources", [])
              if str(s.get("type", "")).upper() == "E1"
              and _valid_source_url(s.get("url", ""))
              and str(s.get("locator", "")).strip()]
        if len(e1) < 3:
            issues.append({"rule_id": "TOP-01", "level": "P0",
                           "msg": f"合格的 E1 来源 {len(e1)} 条（需 ≥3，且 url 与 locator 非空）"})
        # 占位假来源不得过 G0（根 AGENTS 禁止「占位过检后当真数据发布」）
        PLACEHOLDER = ("待改写", "待定", "TODO", "占位", "请改写", "示例假设")
        for s in d.get("sources", []):
            blob = " ".join(str(s.get(k, "")) for k in ("title", "url", "locator"))
            if any(p in blob for p in PLACEHOLDER):
                issues.append({"rule_id": "TOP-01", "level": "P0",
                               "msg": f"来源含占位文本，不得过 G0：{blob[:60]}"})
                break
        for k in ("claim", "increment_note", "reader_before"):
            v = str(d.get(k, "") or "").strip()
            if v == "待改写" or v.startswith("待改写：") or v.startswith("TODO"):
                issues.append({"rule_id": "TOP-01", "level": "P0",
                               "msg": f"立项卡 {k} 仍是占位文本"})
                break

    elif which == "G1":
        p = None
        for c in GATE_FILES["G1"]:
            p = p or need(c)
        if not p:
            return [{"rule_id": "G1", "level": "P0",
                     "msg": "缺读者假设表（08_读者假设.md）"}]
        text = read(p)
        # 脚手架/模板占位不得当真实读者假设。
        hit = [x for x in PLACEHOLDER_TERMS if x in text]
        if hit:
            issues.append({"rule_id": "AUD-01", "level": "P0",
                           "msg": f"读者假设表含占位文本：{','.join(hit[:3])}"})
        # AUD-01：假设表每一数据行都必须带 given/inferred/assumed 标记。
        markers = ("given", "inferred", "assumed")
        data_rows, unmarked = [], []
        for ln in text.splitlines():
            s = ln.strip()
            if not s.startswith("|") or set(s.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
                continue
            if "标记" in s and "假设" in s:  # 表头
                continue
            data_rows.append(s)
            if not any(m in s for m in markers):
                unmarked.append(s)
        if not data_rows:
            issues.append({"rule_id": "AUD-01", "level": "P0",
                           "msg": "假设表缺少数据行（given/inferred/assumed）"})
        if unmarked:
            issues.append({"rule_id": "AUD-01", "level": "P0",
                           "msg": f"假设表 {len(unmarked)} 行无来源标记（按 assumed 处理）"})
        # AUD-04：起点能力清单须是动作，能检的是存在性 + 每条非空
        if "起点" not in text:
            issues.append({"rule_id": "AUD-04", "level": "P0",
                           "msg": "缺「起点能力」清单"})
        else:
            # 起点小节后的列表项
            after = text.split("起点", 1)[-1]
            items = [ln.strip()[2:].strip() for ln in after.splitlines()
                     if ln.strip().startswith("- ") or ln.strip().startswith("* ")]
            # 只取到下一个标题前
            cut = []
            for ln in after.splitlines():
                if re.match(r"^#{2,3}\s+", ln) and cut:
                    break
                if ln.strip().startswith("- ") or ln.strip().startswith("* "):
                    cut.append(ln.strip()[2:].strip())
            items = cut or items
            if not items:
                issues.append({"rule_id": "AUD-04", "level": "P0",
                               "msg": "起点清单为空"})
            else:
                label_like = [it for it in items if len(it) < 8 and not re.search(r"[用读写给列写开跑]", it)]
                if len(label_like) == len(items):
                    issues.append({"rule_id": "AUD-04", "level": "P1",
                                   "msg": "起点清单疑为标签而非动作（每条应可自查）"})
        if "未验证" not in text and "assumed" not in text:
            issues.append({"rule_id": "AUD-03", "level": "P1",
                           "msg": "读者假设表未声明未验证项"})

    elif which == "G2":
        p = None
        for c in GATE_FILES["G2"]:
            p = need(c) or p
        if not p:
            return [{"rule_id": "G2", "level": "P0", "msg": "缺 outline.json"}]
        try:
            d = json.loads(read(p))
        except Exception as e:
            return [{"rule_id": "G2", "level": "P0", "msg": f"outline 不是合法 JSON：{e}"}]
        blob = json.dumps(d, ensure_ascii=False)
        hit = [x for x in PLACEHOLDER_TERMS if x in blob]
        if hit:
            issues.append({"rule_id": "STR-03", "level": "P0",
                           "msg": f"outline 含占位文本：{','.join(hit[:3])}"})
        types = {"原理书", "实战书", "案例书", "排错书", "工具书", "演进书", "通识书"}
        meta = d.get("book") or d.get("doc") or {}
        if meta.get("type") not in types:
            issues.append({"rule_id": "STR-01", "level": "P0",
                           "msg": f"book.type「{meta.get('type')}」不在 7 类之内"})
        if not meta.get("family"):
            issues.append({"rule_id": "DEM-01", "level": "P0", "msg": "book.family 未声明（A/B/C/mixed）"})
        if not str(meta.get("claim", "")).strip():
            issues.append({"rule_id": "TOP-01", "level": "P0", "msg": "book.claim 为空"})
        graph, ids = {}, set()
        for ch in d.get("chapters", []):
            role = ch.get("role") or {}
            if not all(role.get(k) for k in ("phenomenon", "mechanism", "cost")):
                issues.append({"rule_id": "STR-03", "level": "P0",
                               "msg": f"章 {ch.get('id', '?')} 的 role 三项不全（现象/机制/代价）"})
            if not str(ch.get("purpose", "")).strip():
                issues.append({"rule_id": "STR-06", "level": "P1",
                               "msg": f"章 {ch.get('id', '?')} 的 purpose 为空"})
            for sec in ch.get("sections", []):
                sid = sec.get("id", "")
                ids.add(sid)
                for f in ("id", "title", "question", "produces", "deps", "status"):
                    if f not in sec:
                        issues.append({"rule_id": "STR-03", "level": "P0",
                                       "msg": f"{sid or '?'} 缺字段 {f}"})
                if not sec.get("produces"):
                    issues.append({"rule_id": "STR-05", "level": "P1",
                                   "msg": f"{sid} 的 produces 为空"})
                if not sec.get("bridge"):
                    issues.append({"rule_id": "STR-06", "level": "P1",
                                   "msg": f"{sid} 的 bridge 为空"})
                if sec.get("status") not in ("planned", "drafting", "checking", "frozen"):
                    issues.append({"rule_id": "STR-03", "level": "P0",
                                   "msg": f"{sid} status 非法：{sec.get('status')}"})
                graph[sid] = list(sec.get("deps", []))
            # role 三项必须指向本章真实节
            for role_key, target in role.items():
                if target and target not in {s.get("id") for s in ch.get("sections", [])}:
                    issues.append({"rule_id": "STR-03", "level": "P1",
                                   "msg": f"章 {ch.get('id')} role.{role_key}={target} 不在本章 sections 中"})
        tw = meta.get("target_words")
        if not isinstance(tw, int) or tw < 30000:
            issues.append({"rule_id": "STR-11", "level": "P1",
                           "msg": f"target_words={tw}，schema 要求 ≥30000（全书预算）"})
        if not d.get("paths"):
            issues.append({"rule_id": "STR-10", "level": "P1",
                           "msg": "paths 为空（长篇应给 2–3 条阅读路径）"})
        else:
            idset = {s.get("id") for ch in d.get("chapters", []) for s in ch.get("sections", [])}
            chset = {ch.get("id") for ch in d.get("chapters", [])}
            for path in d.get("paths", []):
                for node in path.get("order", []):
                    if node not in idset and node not in chset:
                        issues.append({"rule_id": "STR-10", "level": "P1",
                                       "msg": f"路径「{path.get('name')}」含未知节点 {node}"})
        # 环检测
        state = {}

        def dfs(u, stack):
            state[u] = 1
            for v in graph.get(u, []):
                if v not in graph:
                    issues.append({"rule_id": "STR-04", "level": "P0",
                                   "msg": f"{u} 依赖不存在的节 {v}"})
                    continue
                if state.get(v) == 1:
                    issues.append({"rule_id": "STR-04", "level": "P0",
                                   "msg": f"依赖成环：{' → '.join(stack + [u, v])}"})
                elif state.get(v, 0) == 0:
                    dfs(v, stack + [u])
            state[u] = 2

        for sid in list(graph):
            if state.get(sid, 0) == 0:
                dfs(sid, [])

    elif which in ("G3", "G5", "G7"):
        targets = []
        if os.path.isdir(target := base):
            unit_dir = os.path.join(target, "units")
            if os.path.isdir(unit_dir):
                targets = [os.path.join(unit_dir, f) for f in sorted(os.listdir(unit_dir))
                           if f.endswith(".md") and not f.endswith(".spec.md")
                           and not f.endswith(".check.json")]
            if not targets:
                # 扁平书根兜底；排除模板/读者假设/文风基线，避免把模板自身当正文。
                targets = [os.path.join(target, f) for f in sorted(os.listdir(target))
                           if f.endswith(".md") and not f.startswith(("00_", "03_", "07_", "08_"))
                           and f != "README.md" and not f.endswith(".spec.md")]
            if not targets:
                return [{"rule_id": which, "level": "P1",
                         "msg": "尚未有可校验的单元正文（N/A：等 S3 第一单元）"}]
        elif os.path.isfile(base):
            targets = [base]
        else:
            return [{"rule_id": which, "level": "P0", "msg": f"找不到 {base}"}]
        for t in targets:
            issues.extend(run_checks(read(t), t, "manuscript", strict=False,
                                     evidence_policy=evidence_policy,
                                     allow_block_headings=allow_block_headings)[0])
        if which in ("G5", "G7"):
            # 装配级：outline 与 units 对齐、术语表存在
            outline_p = None
            for c in GATE_FILES["G2"]:
                outline_p = outline_p or need(c)
            if outline_p:
                try:
                    od = json.loads(read(outline_p))
                except Exception as e:
                    issues.append({"rule_id": "G5", "level": "P0", "msg": f"outline 无法解析：{e}"})
                    od = {}
                unit_ids = {os.path.splitext(os.path.basename(t))[0] for t in targets}
                for ch in od.get("chapters", []):
                    for sec in ch.get("sections", []):
                        sid = sec.get("id", "")
                        if sec.get("status") == "frozen" and sid not in unit_ids:
                            issues.append({"rule_id": "G5", "level": "P0",
                                           "msg": f"{sid} 标记 frozen 但 units/ 缺正文"})
            else:
                issues.append({"rule_id": "G5", "level": "P1", "msg": "无 outline，跳过装配对齐" })
            if which == "G7":
                base_dir = os.path.dirname(os.path.abspath(targets[0]))
                if not os.path.isdir(base_dir):
                    base_dir = base
                issues.extend(gate("G6", base if os.path.isdir(base) else base_dir))

    elif which == "G6":
        root = base
        if os.path.isdir(root):
            flat = any(os.path.isfile(os.path.join(root, f)) for f in GATE_FILES["G6"])
            if not flat and os.path.isdir(os.path.join(root, "handoff")):
                root = os.path.join(root, "handoff")

        def need6(name):
            p = os.path.join(root, name)
            return p if os.path.isfile(p) else None

        for f in GATE_FILES["G6"]:
            if not need6(f):
                issues.append({"rule_id": "TEAM-04", "level": "P0", "msg": f"交接包缺 {f}"})
        p = need6("05_unverified.md")
        if p and chinese_len(read(p)) < 80:
            issues.append({"rule_id": "TEAM-04", "level": "P0",
                           "msg": "05_unverified.md 内容过短（视为空洞声明）"})

    else:
        # 未实现的门禁不得假绿（宁可红/跳过，也不要显示 PASS）
        issues.append({"rule_id": which, "level": "P0",
                       "msg": f"未实现的门禁 {which}（规范 §7.2 已定义，不得静默跳过）"})
    return issues


# ---------------------------------------------------------------- 主流程


def run_checks(text, path, profile, strict, with_registry=True, ref_text="",
               evidence_policy="body-e-tags", allow_block_headings=False):
    headings = set()
    for _, line, in_code, _ in split_lines(text):
        if in_code:
            continue
        # 分部标题：# 第 N 部分 → 允许 §N 引用
        m = re.match(r"^#\s+第\s*(\d+)\s*部分", line)
        if m:
            headings.add(m.group(1))
        m = re.match(r"^#{2,3}\s+(\d+(?:\.\d+)*)", line)
        if m:
            headings.add(m.group(1))

    extra_ids = set()
    if ref_text:
        extra_rules, _, _ = collect_rules(ref_text)
        extra_ids = set(extra_rules)
        for _, line, in_code, _ in split_lines(ref_text):
            if in_code:
                continue
            m = re.match(r"^#\s+第\s*(\d+)\s*部分", line)
            if m:
                headings.add(m.group(1))
            m = re.match(r"^#{2,3}\s+(\d+(?:\.\d+)*)", line)
            if m:
                headings.add(m.group(1))

    rules, table_only, dup = collect_rules(text)
    p0, p1, p2 = check_rules(text, rules, table_only, dup, extra_ids, profile=profile)
    p0 += check_xref(text, headings)
    p0 += check_forbidden(text)
    p0 += check_humor(text)
    if profile == "manuscript":
        p0 += check_form_labels(text, profile, allow_block_headings=allow_block_headings)
        p2 += check_table_density(text, profile)
    p1 += check_headings(text)
    p1 += check_sentence_len(text)
    p1 += check_paragraphs(text, profile)
    p1 += check_tables(text)
    p1 += check_code_fences(text)
    p2 += check_symmetry(text)
    p2 += check_cite(text)
    if profile == "manuscript":
        p0 += check_claims(text, ledger_ids=None, evidence_policy=evidence_policy)
        unit_iss = check_unit_files(path)
        p0 += [i for i in unit_iss if i["level"] == "P0"]
        p1 += [i for i in unit_iss if i["level"] != "P0"]

    if with_registry:
        table = render_registry(rules, path)
        if not registry_in_sync(text, table):
            p1.append({"rule_id": "S-RULE-03", "level": "P1", "line": 0,
                       "msg": "附录 A 规则总表与正文不一致，请跑 --registry --write"})

    return p0, p1, p2, rules


def main():
    # GBK 控制台下 print(json) 会因非常用字符崩溃（C16-S1/C26-S4 实证）；固定 UTF-8。
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default="")
    ap.add_argument("--profile", default="spec", choices=["spec", "manuscript"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--registry", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--gate", default="")
    ap.add_argument("--evidence-policy", default="body-e-tags",
                    choices=list(EVIDENCE_POLICIES),
                    help="证据承载策略（默认 body-e-tags；书稿按 00_大纲合同.evidence_policy 声明）")
    ap.add_argument("--allow-block-headings", action="store_true",
                    help="豁免章末固定块挂牌词（合同 chapter_blocks_as_headings=true 时由 run_gates 自动带上）")
    ap.add_argument("--ref-spec", default="",
                    help="被引用规范的路径：其中的规则 ID 与章节号视为已知")
    a = ap.parse_args()

    if a.gate:
        issues = gate(a.gate, a.file or ".", evidence_policy=a.evidence_policy,
                      allow_block_headings=a.allow_block_headings)
        p0 = [i for i in issues if i["level"] == "P0"]
        p1 = [i for i in issues if i["level"] != "P0"]
        if a.json:
            print(json.dumps({"gate": a.gate, "P0": p0, "P1": p1}, ensure_ascii=False, indent=2))
        else:
            print(f"门禁 {a.gate}: P0={len(p0)} P1={len(p1)}")
            for i in p0 + p1:
                print(f"  [{i['level']}] {i['rule_id']}: {i['msg']}")
        return 2 if p0 else (1 if p1 and a.strict else 0)

    if not a.file:
        ap.error("需要文件路径")

    # 支持目录（writing-rules/spec/）：按分片拼接为单一检查文本
    target_path = a.file
    if os.path.isdir(a.file):
        try:
            from build_spec import load_spec_dir  # type: ignore
            text = load_spec_dir(Path(a.file))
        except Exception:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from build_spec import load_spec_dir  # type: ignore
            text = load_spec_dir(Path(a.file))
        target_path = os.path.join(a.file, "A-规则总表.md") if a.registry else a.file
    else:
        text = read(a.file)

    if a.registry:
        rules, _, _ = collect_rules(text)
        table = render_registry(rules, target_path)
        if a.write:
            # 写回目录内的附录 A，而不是拼接后的临时文件
            write_target = target_path
            if os.path.isdir(a.file):
                write_target = os.path.join(a.file, "A-规则总表.md")
            ok = write_registry(write_target, table)
            print("规则总表已写入" if ok else "写入失败")
            rows = [r for r in rules.values() if r["form"] == "standard"]
            must = sum(1 for r in rows if r["strength"] == "MUST")
            print(f"共 {len(rows)} 条（MUST {must}）")
            return 0
        print(table)
        return 0

    ref_text = read(a.ref_spec) if a.ref_spec else ""
    p0, p1, p2, rules = run_checks(text, a.file, a.profile, a.strict, ref_text=ref_text,
                                   evidence_policy=a.evidence_policy,
                                   allow_block_headings=a.allow_block_headings)
    must = sum(1 for r in rules.values() if r["strength"] == "MUST")

    if a.json:
        print(json.dumps({
            "file": a.file, "profile": a.profile, "rules": len(rules), "must": must,
            "P0": p0, "P1": p1, "P2": p2,
            "summary": {"P0": len(p0), "P1": len(p1), "P2": len(p2)},
        }, ensure_ascii=False, indent=2))
    else:
        print(f"文件: {a.file}")
        print(f"规则: {len(rules)} 条（MUST {must}）  字数: {chinese_len(text)}")
        print(f"结果: P0={len(p0)} P1={len(p1)} P2={len(p2)}")
        for tag, items in (("P0", p0), ("P1", p1), ("P2", p2)):
            if not items:
                continue
            print(f"\n{tag}:")
            for i in items:
                loc = f"L{i['line']}" if i.get("line") else ""
                print(f"  {loc:>6} [{i['rule_id']}] {i['msg']}")
                if i.get("quote"):
                    print(f"         → {i['quote']}")

    if p0:
        return 2
    if p1 and a.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

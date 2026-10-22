#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wordcount.py — 全仓库统一「字数」口径（G3 / G8 / 大纲合同共用）。

定义（单一真源，勿另起口径）：
  cjk_len(s) = 汉字字符数 + 字母/数字连续段个数 // 2
  chinese_len(s) = 去掉全部空白后的字符数（兼容 spec_lint 历史口径）

  - 代码块与表格计入正文体量（合同按实写折算页数）。
  - 不把 Markdown 标记符单独计为内容。

用法：
  from wordcount import cjk_len, chinese_len
"""
from __future__ import annotations

import re

_WS = re.compile(r"\s+")
_ALNUM_TOKEN = re.compile(r"[A-Za-z0-9_]+")
_CJK = re.compile(r"[一-鿿]")


def cjk_len(s: str) -> int:
    """汉字当量：与 validate_quality 历史口径一致（G8 体量锁）。"""
    return len(_CJK.findall(s)) + len(_ALNUM_TOKEN.findall(s)) // 2


def chinese_len(s: str) -> int:
    """去空白全字符计数（spec_lint 句长/段落指标沿用）。"""
    return len(_WS.sub("", s))

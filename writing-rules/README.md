# 技术书籍写作规范 v1

一份写给 AI Agent 的技术书籍生产规范。执行者是 Agent，验收标准由脚本与门禁判定。

## 它解决什么问题

Agent 写书稿有四类典型失效，人类写作规范一条都防不住：

| 失效 | 表现 | 本规范的应对 |
|---|---|---|
| 虚构 | 编 API、编输出、编版本号 | 断言分 E0–E3，等级决定句式（§1.3） |
| 自证 | "已检查"就等于检查过 | 三级校验，L2 禁止自判（§7.1） |
| 平铺 | 每节三个要点，读完记不住 | 三层剥法：现象 → 机制 → 代价（§0.1） |
| 拖沓 | 预告、复述、小结、堆评价 | 禁用词 + 段落指标 + 文风样例（§6） |

## 文件构成

```text
writing-rules/
├── 技术书籍写作规范_v1.md      导航入口（正文真源在 spec/）
├── README.md                   本文件
├── 如何改规范.md               改规则/阈值/门禁的贡献指南
├── workflow/                  # ★ 写书三角色 + 四阶段（外部 Agent 必读）
├── spec/                       规范分片（单一真源）
│   ├── README.md               按任务加载
│   ├── 00-overview.md … 10-交接.md
│   └── A-规则总表.md … H-文风样例.md
├── tools/
│   ├── spec_lint.py            L0 校验器 + 门禁 + 规则总表生成
│   ├── build_spec.py           分片拼接（调试/单页）
│   ├── init_book.py            新书脚手架（含 workflow/）
│   ├── assemble_book.py        units → chapters/chN.typ
│   ├── sync_handoff.py         交接包同步与时间戳
│   ├── run_gates.py            紧凑 G0–G8
│   ├── new_unit.py             单元 spec 预填
│   ├── memory_maint.py         阶段记忆清理
│   ├── validate_quality.py     G8 体量/报告/过程验收
│   ├── check_rule_coverage.py  规则声称 ↔ 脚本实现 一致性
│   ├── wordcount.py            统一字数口径（G3/G8/合同）
│   ├── package_book.py         tar.gz 交付打包
│   ├── progress_report.py      进度一页纸
│   └── tests/run_tests.py      工具回归
└── kit/                        9 份可填写资产
    ├── 01_立项卡.json
    ├── 02_outline.schema.json
    ├── 02_outline.json         可直接跑 G2 的示例（连接池选题）
    ├── 03_单元spec.md
    ├── 04_ledger.csv
    ├── 05_state.json
    ├── 06_glossary.json
    ├── 07_style.kernel.md      文风基线，4 段例句
    └── stage_prompts.md        S-1 到 S7 提示词
```

## 三种上手方式

**只想知道标准。** 读主文件第 0 部分（作者身份）与第 6 部分（语言与风格），再看附录 H 的六组对照。这是"写成什么样"的全部答案。

**要开始写一本书。** 先脚手架，再贴 `kit/stage_prompts.md` 的 S-1 人格段，按 S0 → S7 走：

```bash
python3 tools/init_book.py my-book --title "书名" --claim "可证伪承诺"
python3 tools/spec_lint.py --gate G0 books/my-book
# 写 units/ … 完成后
python3 tools/assemble_book.py books/my-book --engine ../techbook-typst --compile
```

标准目录与闭眼约定见根目录 `CONTRIBUTING.md`。每阶段有门禁，不过不许进下一阶段。

**已有书稿要体检。** 直接跑校验：

```bash
python3 tools/spec_lint.py 你的书稿.md --profile manuscript
python3 tools/spec_lint.py 你的书稿.md --json        # 机器可读，便于按 rule_id 修
python3 tools/spec_lint.py --gate G0 项目目录         # 立项卡完整性
python3 tools/spec_lint.py --gate G2 项目目录         # 结构合法性
```

退出码：0 通过 / 1 有 P1 / 2 有 P0。

## 规则规模

137 条，MUST 96 / SHOULD 41（以附录 A 实时计数为准）。附录 A 由脚本从正文派生，手改会被覆盖。

MUST 是单元级门禁（不过则该节不能冻结），附录 C 的十条红线是发布级门禁（不过则全书不能交）。两者不是一回事。

## 三条使用前提

1. **读者验证只能由人做。** 规范能给交接包与复现清单，给不了替代。声称"已验证读者能懂"而没有真人测试，属违规。
2. **附录 F 的数值待校准。** 节长、句长、幽默密度都来自经验，没有真实书稿样本。第一本书写完后按实际数据回填。
3. **这套规则偏重。** 规则集全跑一遍有成本。第一本书跑完后，删掉三成是正常结果。

# Changelog

本项目遵循「写清楚改了什么、为何改、如何验证」。格式参考 [Keep a Changelog](https://keepachangelog.com/)；语义化版本在首次公开 tag 时再启用。

## [Unreleased]

### Added
- **批量衰减检测**（F# 案例驱动）：`quality_gate` DECAY-01/02/03 按章聚合体量/纪律/证据完整度，首 ⅓ vs 末 ⅓ 对比；阈值走 `00_大纲合同.decay_thresholds`
- **合同增强**：`00_大纲合同.json` 新增 `word_count_metric`（字数口径钉死）、`evidence_policy`（body-e-tags|spec-mapping|visible-markers）、`evidence_markers`、`deliverables`、`figures_min`、`chapter_blocks_aliases`、`decay_thresholds`；CTR-01/02 交付物与图数量、CTR-03/04 合同骨架块按章核查
- **台账校验收紧**：EVD-14 `unit` 必须回指单元/章；EVD-15 `url` 须 `https://` 或 `repo:`，本机路径泄漏 P0；EVD-13 按证据策略分支；WF-23 `notes_brief` 单字符污染
- **门禁可复核**：RPT-11 报告写「P0=0/零命中」须带 `gate_check` 回执，与实测不符 P0；`run_gates --write-check` 生成 `handoff/04_check.json`；`workflow/revision_log.jsonl` 修订迁移链（登记后旧报告 RPT-09 降 P1 可追溯）
- **交付契约**：`package_book` MANIFEST/README 带 `delivery_status`（final 人签字前 draft）；「终版/final/ready」命名护栏（`--force-name`）；README 书籍化要求与 `tools/` 自造工具回流写入 `08_交付规范`
- `.github/workflows/ci.yml`：工具回归 + 规则总表同步 + 金样板硬门禁
- `spec_lint --evidence-policy`：L-CLAIM-01 口径随 `00_大纲合同.evidence_policy` 三态切换
- `tools/quality_gate.py`：质量优先硬门禁——P1 试点章未人签字不得进 P2、无人值守只能 draft、报告必须带 `文件:行号 + 原文引句 + reviewed_revision`、台账 schema、C# 片段缺括号/未标 illustrative、章末块/质量预算；接入 `validate_quality`（G8）
- `techbook-typst/tools/md2typ.py`：图片→`#fig/#image`、链接→`#link`、引用→`#quote`、分隔线、`<!-- caption -->` 表注、`--asset-dir` 资源复制
- `assemble_book.py`：默认生成书内 `books/<slug>/typst/`（main/config/src/chapters/assets/dist），`--compile` 在书内编译；拒绝写 `techbook-typst/`，除非 `--allow-engine`；保留 `--out` 兼容模式
- 规则解析器修正：支持 1–6 字母域（`CLAIM` / `HUMOR` / `B` / `F` 不再漏表）；A 总表 145 条 / MUST 103 / SHOULD 42
- `init_book --family/--target-words`：立项卡与 outline 同源，修复 B/C 混写；脚手架不再把 `03_单元spec.md` 当正文 lint
- `templates/00_阶段状态.json` 增加 `human_in_loop`、`human_confirmations.pilot/final`、`pilot`；`init_book` 生成 `workflow/06_终审/`
- `tools/check_rule_coverage.py`：规则「声称脚本」与 tools 实现的真源一致性巡检（RULE-01 自动化）；`run_tests.py` 挂入
- `tools/wordcount.py`：G3/G8/合同共用字数口径，spec_lint 与 validate_quality 统一 import
- `CLAUDE.md` 与根 `AGENTS.md`/`README.md` 顶部三行入口判别器（写书 / 维护 / 只用排版）
- 交付包布局支持：`validate_quality` 认 `manuscript/`+`workflow/`+`handoff/`；报告名兼容 `01_读者报告-第1章.md`
- 人工确认不可默示：拒绝「视为默示确认」；人设未确认 / pending_human 未清记 P1

### Fixed
- **工具误报与崩溃（F# 案例实证）**：`spec_lint --json` 非 GBK 字符崩溃（固定 UTF-8）；LANG-05 把 `<!-- src -->` 注释行/英文引文/双反引号当正文计句长（剥离+纯西文不计）；L-FORM-01 漏「去冒号挂牌」（`## 机制`/`## 小结`/`## 本章标尺`）；CODE-03 误报 `var x = a.B;` 属性读取（只报裸语句）；`run_gates`/`run_tests` 子进程输出按 UTF-8 解码；QG-03 关键词可被挂牌标题顶数（新增 QG-05 要求行文承载）
- **门禁单调性**：`run_gates` G4 未实现默认 SKIP（`--require-g4` 强制），不再永久 HAS_FAIL；G8 未过时 G7 强制 FAIL（禁止「G7 PASS + G8 FAIL」）
- **G4 未实现不得假绿**：`spec_lint --gate G4` 仍报 P0「未实现的门禁」（默认 `run_gates` 标 SKIP）
- **G0 拒占位**：立项卡来源/claim 含「待改写/TODO」时 G0 红
- **check_claims 收紧**：不再「段内见 E- 即整段免检」，改为逐句核对
- **L-VOL-01 落地**：`validate_quality` 以 `rule_id=L-VOL-01` 产出体量锁；其余悬空「脚本 X」降为「自检」或改指真实 ID
- **09 报告名单一**为 `09_大纲×规范融合评估.md`，清除旧名
- **G1/G2 占位不再假绿**：读者假设表/outline 含「示例假设/待定章名/这一节回答什么」等占位即 P0
- **G3 脚手架降噪**：无单元正文时返回 N/A（P1），不再把 `03_单元spec.md`/`07_style.kernel.md` 当正文
- **B-01/F-01 修正**：`MUST｜登记` 改为 `MUST｜自检｜阻断`，不再被规则解析器隐藏
- 金样板定位对齐：README/handoff 明确「结构示范、体量未达 G8」

### Changed
- UNIT-14 代码溯源接受 `src:`/`path:` **或** 同节台账 `E-xxx`（宪法 C-05）
- 根 `AGENTS.md` §2 同步清单纳入 `validate_quality` / `check_rule_coverage`
- `templates/08_交付规范.md` 写明双布局工具约定

### Added（此前批次）
- 质量第一与「基线+大纲融合」：WORKFLOW §0、UNIT-23/24、STR-12 改硬；`00_大纲合同.json`、`09_大纲×规范融合评估.md`、`validate_quality.py`（G8）、`progress_report.py`
- 正文严禁「最少 token」；冻结/交付查体量、空模板报告、state 与 frozen 一致
- 交付 README 开源项目化：书籍简介/承诺/读者/目录 + LICENSE 打入 tar.gz
- 交付物 tar.gz 规范（`templates/08_交付规范.md`）与 `package_book.py`：含 typst 源码/PDF/manuscript/handoff/workflow/README/MANIFEST，自动清理废弃项
- techbook：页边距约 3/4、表后间隙、封面/目录/版权左对齐
- techbook 书感版式：正文衬线/标题黑体、首行缩进 2em、对称版心、章首页留白、三线表、代码块通栏轻量、A4 预设；书眉改为章名+居中页码
- 提速/省 Token：`workflow/briefs/` 加载卡、`run_gates.py` 紧凑门禁、`new_unit.py` spec 预填、`memory_maint.py`；阶段 2 每章 3 行卡 + 每 N 章详评 + 并行 N+1
- 自由区：ENG-10 / WORKFLOW §8 叙述与修辞可发挥，每章 1–2 处实验并登记；读者报告增加「是否被规则绑死」
- `writing-rules/workflow/`：作者/读者/编辑 + 人 四阶段写书工作流、角色说明书、7+1 报告模板
- `init_book.py` 创建 `workflow/`（阶段状态与报告模板）；README 路由置顶 WORKFLOW
- 文风：ENG-09 带新人视角；UNIT-21/22、LANG-19/20 禁挂牌标题 + 每节表格 ≤2；lint L-FORM-01/02
- style.kernel 收录「原始 vs 优化」文风对照；金样板 12 单元按新文风整本重写
- 根目录 `AGENTS.md`：仓库维护契约（变更闭环、现场清理、变更说明、收尾检查表）。
- `writing-rules/tools/init_book.py`：按 kit 脚手架写作工程（文件名与 G0–G7 对齐）。
- `writing-rules/tools/assemble_book.py`：units → `chapters/chN.typ` → config.toml 一条命令；无正文也出章占位。
- `books/how-to-write-a-tech-book/`：按 writing-rules S0–S7 写成的金样板（12 冻结单元 + 交接包）。
- `writing-rules/tools/tests/run_tests.py`：spec_lint / md2typ / sync_handoff / 金样板门禁回归。
- `writing-rules/tools/sync_handoff.py`：交接包同步并在 README 写入拷贝时间点。
- `writing-rules/tools/build_spec.py`：规范分片拼接。
- `writing-rules/spec/`：规范正文拆为 00–10 与附录 A–H 分片（单一真源）。
- `writing-rules/如何改规范.md`：改规则/阈值/门禁的贡献指南。
- `CONTRIBUTING.md`、`CHANGELOG.md`、根 `.gitignore`、README English 入口。
- `techbook-typst/tools/md2typ.py`：写作单元 Markdown → Typst 章节装配。

### Changed（历史批次）
- 写作规则模型：**writing-rules MUST 为基线**，大纲要求作为项目特化层**融合**进宪法（09 改为融合评估：保留基线/大纲覆盖/合成新条/Waiver）
- 表格密度 UNIT-22/LANG-20 降为 SHOULD（L-FORM-02 → P2）；挂牌标题与假来源仍 P0
- README 路由补「新建标准写作工程 / 装配编译 / 维护本仓库」；S0 提示词要求先 `init_book.py`；金样板路径统一为 `how-to-write-a-tech-book/`。
- 章节装配约定：`chapters/chN.typ`（由 assemble_book 生成）；handoff 统一 `01_outline.json`/`02_glossary.json`。
- 台账/立项卡来源 URL 去掉写死的托管平台地址，改为 `https://…` 或 `repo:相对路径`；G0 接受 `repo:`。
- 版权与包作者统一为 **CodeBu**。
- 金样板目录：`books/如何写一本技术书/` → `books/how-to-write-a-tech-book/`。
- 根 `.gitignore`：图片改为只忽略 `dist/**/*.png`，避免挡住将来插图。

### Fixed（历史批次）
- `spec_lint.check_claims` 段落元组解包崩溃（P1）。
- G1 门禁未实现；G3/G5/G7 只扫第一个 `.md`。
- manuscript 模式误报「引用了不存在的规则」。
- G2 补 `bridge`/`status`/`role`/`target_words`/`paths` 检查。
- G6 支持 `handoff/` 回落。

### Removed（历史批次）
- 样书中越权的排版工具章（改为附录速查）；过时章节名引用；`.DS_Store`。

## [0.0.1] - 2026-10-20

### Added（历史批次）
- 初始仓库：writing-rules 规范与 kit、techbook-typst 引擎与样书骨架。

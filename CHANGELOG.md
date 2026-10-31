# Changelog

格式参考 [Keep a Changelog](https://keepachangelog.com/)；语义化版本在首次公开 tag 时再启用。每条保留「改了什么/为何」，验证细节见 `PROBLEMS.md` 对应条目。

## [Unreleased]

### Added
- `quality_gate` 三查（P22/P23 实证补缺）：`EVD-18` spec 挂不存在的 E 号（P0）、`EVD-19` 错挂提示（主张明显更像另一条台账时给应挂 E 号）、`QG-07`「片段示意」注记后缺代码块（P0）、`CTR-01` 交付物空壳判定（glob 存在≠齐备）。Avalonia 书稿实测抓到 2 组 +10 整表错挂与 1 处漏网缺块
- 引擎 `#appendix[标题, letter: "F"]` 显式字母参数：正文章题内嵌「附录 A–E」名号时防撞名（Avalonia 速查附录实证）；AGENTS 补「附录内小节会沿用上一章章号」的规避写法
- **章循环批量工作流**（长任务一致性）：批量期不再「Agent 一气呵成」——默认每 2–3 章一批（`review_every_n_chapters`），批内写作→三角色自审→《章审包》→**人签字（改了什么/裁了什么，空签字无效）**→该批才 frozen；人的调整回写宪法（规则更新而非一次性 patch）。新增模板 `10_章审包.md`、`11_写作者上下文包.md`（每批自包含上下文）与 `deviations.jsonl`
- **申报制自由度**（治死板）：合同 `form_freedom: true` + `freedom_scope` 4 项章级放开（引入方式/图表密度/句长段长软化/题材口吻幽默）；形式类检查（L-FORM-01/02、LANG-05/11/12）降 P1 提示，有意偏离登记 `deviations.jsonl` 由人逐条裁决（追认=入宪法/收敛=记反例）；硬线（真实性/证据/禁用词/代码可跑/冻结纪律）永不降级。书级结构（章末固定块、附录形态）不逐章放开，走 09 整书裁决
- **章签名校验**：WF-26 frozen 单元必须被人签字覆盖、WF-27 空签字无效、DEV-01 待裁偏离、DEV-02 签字了却未裁决（走过场）；`spec_lint --soft-form` 与 `run_gates` 合同透传
- `tools/quality_gate.py` 质量优先硬门禁（接入 `validate_quality` = G8）：P1 未签字不得进 P2、无人值守只能 draft、禁默示确认、报告须 `文件:行号+原句+reviewed_revision`、台账 schema、C# 片段、章末块、质量预算
- 合同字段钉死（`00_大纲合同.json`）：`word_count_metric`、`evidence_policy`（body-e-tags|spec-mapping|visible-markers）、`chapter_blocks_as_headings`、`deliverables`、`figures_min`、`decay_thresholds`、`chapter_blocks_aliases`
- 批量质量检查：DECAY-01/02/03（首⅓ vs 末⅓ 衰减）、CTR-01–04（交付物/图数/骨架块）、QG-05/06（章末固定块承载须裁决）
- 台账校验：EVD-13 按证据策略、EVD-14 unit 回指、EVD-15 url 须 `https://`|`repo:` 且禁本机路径、EVD-17 `repo:` 落地、WF-23/24/25（状态污染 / 阶段-进度守恒 / 工具自改未回流）
- 门禁可复核：RPT-11（声称须带 `gate_check` 回执）、`run_gates --write-check` 写 `handoff/04_check.json`（含 `git_rev`/工具版本）、`workflow/revision_log.jsonl` 修订迁移链
- 交付契约：`package_book` MANIFEST/README 带 `delivery_status`、「终版/final/ready」命名护栏（`--force-name`）、README 书籍化、`tools/` 自造工具回流
- `spec_lint --evidence-policy` / `--allow-block-headings`：L-CLAIM-01 与挂牌词表按合同裁决切换
- `techbook-typst/tools/md2typ.py`：图/链接/引用/分隔线/表注转换、`--asset-dir` 资源复制
- `assemble_book.py`：默认生成书内 `books/<slug>/typst/`（不写引擎，`--allow-engine` 例外）；`--out` 兼容模式
- 规则解析器支持 1–6 字母域（CLAIM/HUMOR/B/F 入表）；A 总表 145 条 / MUST 103 / SHOULD 42
- `init_book --family/--target-words`、`human_confirmations.pilot/final`、`workflow/06_终审/`、交付包双布局、`check_rule_coverage.py`、`wordcount.py`、`.github/workflows/ci.yml`
- 四阶段写书工作流 `writing-rules/workflow/`（角色/报告模板/加载卡）、`00_阶段状态.json` 人类闸门字段、CLAUDE/AGENTS/README 三行入口判别器

### Fixed
- `md2typ` 无 `--asset-dir` 时图片引用按「源文件真实位置 → 输出目录」重定位（此前沿用单元视角路径，装配产物落位 `chapters/` 后指错；Avalonia 重构 P23 实证）
- 引擎字链族名与代码高亮（Avalonia PDF 实证）：族名改规范名 `Noto Serif SC` 等 + mono 补 CJK 兜底（曾全书方块）；行内 raw 药丸规则不再吞掉主题着色、`csharp` 别名归一 `cs`（曾代码块全黑）
- `md2typ` 行内代码走字符串通道 `#code("...")` + `markup_escape()` 12 字符转义（Avalonia 案例 P17：`List<T>`、`x:DataType="vm:Boo"`、`_斜体_` 曾被 Typst 当 markup 再解析而编译失败）；加粗/链接文本/标题/表格单元分通道渲染；写书会话工具回流
- EVD-17 误报：`repo:` 按契约解析 playbook 本库（`REPO_ROOT`），金样板 `repo:writing-rules/spec/…` 不再判悬空；随书工程仍解析书稿内
- 工具误报与崩溃（三案实证）：GBK stdout 崩溃；LANG-05 把注释/英文引文/双反引号计句长；L-FORM-01 漏去冒号挂牌；CODE-03 误报属性读取 `var x = a.B;`；CODE-04 误报多行 `new`；子进程 UTF-8 解码
- 门禁单调性：G4 未实现默认 SKIP（`--require-g4` 强制）；G8 未过时 G7 强制 FAIL；G0/G1/G2 拒占位；G3 无正文返 N/A；B-01/F-01 改 MUST|自检|阻断
- `check_claims` 逐句核对；L-VOL-01 真实产出；09 报告名单一；金样板定位对齐「结构示范、体量未达 G8」

### Changed
- 章循环改造后的表述清扫：briefs（00 开工/CHECK/P2）、roles/author、templates/05、stage_prompts 的旧「每 3 章/滚动产出/人不参与」一律对齐批节奏（2–3 章/批人签）；修「阻立」错字；删未接线的 `demote_soft_form`；WORKFLOW §0.2 冗长条款收紧
- 写作规则模型：writing-rules MUST 为基线，大纲要求融合进宪法（09 融合评估 + 人签字）
- UNIT-14 代码溯源接受 `src:`/`path:` 或台账 `E-xxx`；表格密度降 SHOULD；URL 契约 `https://`|`repo:`；版权统一 CodeBu

### Removed
- 瘦身：删除导航重复文件 `writing-rules/技术书籍写作规范_v1.md`（并入 `spec/README.md`）；删除死函数 `package_book.copy_tree`、`quality_gate._nonempty_data_rows`；`progress_report.py` 去重并修 `state.get('state')`（改用 `wordcount.cjk_len`）；PROBLEMS/CHANGELOG 旧案压缩为索引

## [0.0.1] - 2026-10-20

初始仓库：writing-rules 规范与 kit、techbook-typst 引擎与样书骨架、S0–S7 工作流、`spec/` 分片真源、`init_book`/`assemble_book`/`sync_handoff`/`package_book`/`build_spec` 工具链、金样板 `books/how-to-write-a-tech-book/`。

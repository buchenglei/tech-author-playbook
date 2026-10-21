# Changelog

本项目遵循「写清楚改了什么、为何改、如何验证」。格式参考 [Keep a Changelog](https://keepachangelog.com/)；语义化版本在首次公开 tag 时再启用。

## [Unreleased]

### Added
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

### Changed
- README 路由补「新建标准写作工程 / 装配编译 / 维护本仓库」；S0 提示词要求先 `init_book.py`；金样板路径统一为 `how-to-write-a-tech-book/`。
- 章节装配约定：`chapters/chN.typ`（由 assemble_book 生成）；handoff 统一 `01_outline.json`/`02_glossary.json`。
- 台账/立项卡来源 URL 去掉写死的托管平台地址，改为 `https://…` 或 `repo:相对路径`；G0 接受 `repo:`。
- 版权与包作者统一为 **CodeBu**。
- 金样板目录：`books/如何写一本技术书/` → `books/how-to-write-a-tech-book/`。
- 根 `.gitignore`：图片改为只忽略 `dist/**/*.png`，避免挡住将来插图。

### Fixed
- `spec_lint.check_claims` 段落元组解包崩溃（P1）。
- G1 门禁未实现；G3/G5/G7 只扫第一个 `.md`。
- manuscript 模式误报「引用了不存在的规则」。
- G2 补 `bridge`/`status`/`role`/`target_words`/`paths` 检查。
- G6 支持 `handoff/` 回落。

### Removed
- 样书中越权的排版工具章（改为附录速查）；过时章节名引用；`.DS_Store`。

## [0.0.1] - 2026-10-20

### Added
- 初始仓库：writing-rules 规范与 kit、techbook-typst 引擎与样书骨架。

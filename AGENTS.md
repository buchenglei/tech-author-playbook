# AGENTS.md —— 本仓库维护契约（写给 Agent）

> **先判断你是来做什么的：**
> - **用本库写一本书** → 去读 [`README.md`](README.md) §3 路由表 → `writing-rules/workflow/WORKFLOW.md`，**不必读完本文件**
> - **维护 / 修改本仓库** → 继续读本文件
> - **只用排版引擎** → [`techbook-typst/AGENTS.md`](techbook-typst/AGENTS.md)

你正在**维护** tech-author-playbook，不是用它写书。每次改代码、文档、样例前先读本文件；本文件是变更的硬约束，与 `CONTRIBUTING.md`（协作礼仪）并行，冲突时以更严者为准。

> 用它写书请走 `README.md` 路由 + `writing-rules/kit/stage_prompts.md`。  
> 本文只管：**如何改这个仓库本身**。

---

## 0. 一次变更的固定闭环

```text
1. 定范围   只动一条线（写作 / 排版 / 仓库工程），除非机械重命名
2. 对契约   命名、目录、门禁、URL 约定见 §2
3. 做修改   代码 + 说明同步改（§3）
4. 清现场   删过时文件、忽略产物、不留半成品（§4）
5. 跑验证   测试 + 金样板门禁 +（若动排版）编译 PDF（§5）
6. 写变更   CHANGELOG + 必要时 PROBLEMS / 文档（§3）
7. 提交     一次一主题；说明里写清动机与验证（§6）
```

没有第 4–6 步的「改完了」不算完成。

---

## 1. 你维护的三条线

| 线 | 目录 | 真源 | 回归 |
| --- | --- | --- | --- |
| 写作方法与门禁 | `writing-rules/` | `writing-rules/spec/*.md` | `tools/tests/run_tests.py` + 金样板 G0–G8 |
| 成书排版引擎 | `techbook-typst/` | `src/` | `nu build.nu doctor && lint && book` |
| 金样板书稿 | `books/how-to-write-a-tech-book/` | `units/` + `02_outline.json` | 门禁 + `assemble_book.py` |

交叉点只有工具：`tools/spec_lint.py`、`init_book.py`、`assemble_book.py`、`sync_handoff.py`、`validate_quality.py`、`quality_gate.py`、`check_rule_coverage.py`、`md2typ.py`。改交叉点必须三线都回归。

---

## 2. 硬契约（违反即回滚级错误）

1. **命名对齐门禁**  
   - 写作工程：`01_立项卡.json` … `08_读者假设.md`、`units/`、`handoff/`  
   - 交接包六文件：`00_README.md` `01_outline.json` `02_glossary.json` `03_ledger.csv` `04_check.json` `05_unverified.md`  
   - 装配章节：`chapters/chN.typ`（N 为章序）  
   新增文件若进上述集合，必须同步 `spec_lint.GATE_FILES` / `init_book` / `sync_handoff` / `assemble_book` / `validate_quality` 与文档。

2. **不写死托管平台 URL**  
   来源用 `https://…`（外部）或 `repo:相对路径`（本库）。禁止 `github.com/<org>/<repo>` 写进台账、立项卡、测试夹具。

3. **版权与包署名**  
   对外身份为 **CodeBu**（`LICENSE`、`typst.toml`、`config.toml`）。书名/作者字段按书稿可不同，版权主体不漂。

4. **规则单一真源**  
   - 条文只写在 `writing-rules/spec/0x-*.md`  
   - `A-规则总表.md` 由 `spec_lint.py spec/ --registry --write` 生成，**禁止手改**  
   - 阈值改 `tools/spec_lint.py` 常量，并回填 `F-待校准项.md`

5. **产物不进库**  
   `dist/`、`*.pdf`、日志、`.DS_Store`、`__pycache__`、临时 `books/_*` 演示工程。用 `.gitignore`，不要 `git add -f`。

6. **handoff 不手改拷贝件**  
   改源文件后 `python3 writing-rules/tools/sync_handoff.py <book>`。

7. **正文不挂牌**：禁止「现象：/机制：/…」式小节标题；每节表格 ≤2；样章文风以 `07_style.kernel.md` 对照为准。

8. **章节不写样式**  
   `chapters/*.typ` 禁止 `#set page/text/par`；样式在 `src/` 或 `config.toml`。

---

## 3. 每次变更必须写说明（Agent 能读懂）

> **规则：凡改动可被他人/他 Agent 使用的行为或结构，必须留下机器之外可读的说明。**  
> 没有说明的变更，下一会话只能靠读 diff 猜意图，这是本仓库最贵的故障。

| 改了什么 | 必须同步写哪里 | 写到什么程度 |
| --- | --- | --- |
| 任何用户可见变更 | `CHANGELOG.md`（Unreleased） | 一句动机 + 影响面 |
| 工具/门禁行为 | 对应 `--help`、docstring、README/CONTRIBUTING 命令块 | 新命令可复制粘贴跑通 |
| 目录/命名约定 | `AGENTS.md`（本文件）+ `init_book` 产出清单 | 列出标准文件名 |
| 规范条文 | `spec/` 分片 + 规则 ID + 如何判定 | 不写空洞 MUST |
| 已知缺陷与修法 | `PROBLEMS.md` 四段：现象→根因→修法→验证 | 后人能补回归测试 |
| 样书/金样板结构 | `books/…/README.md` 或 handoff README | 指出与默认流水线差异 |

**说明写作标准**（照此写，不要写「已优化」）：

- 用命令、路径、字段名，不用比喻
- 写「对 Agent 何时有用」：入口一行（README 路由 / stage_prompts / --help）
- 破坏性变更写迁移：`旧路径 → 新路径`，并在 PR/commit 里可 grep
- 不写死仓库主页 URL；相对路径写 `repo:…` 或树内相对路径

---

## 4. 每次任务完成必须清理现场

> **规则：任务收尾 = 新增正确的 + 删除过时的。** 只增不删会积累「幽灵文件」，Agent 会把废弃路径当现行约定。

清理清单（收尾时逐项过）：

| 类 | 查什么 | 处理 |
| --- | --- | --- |
| 过时文档 | 章名/路径/命令与现状不一致 | 改到可 grep 的真源，或删段落 |
| 废弃文件 | 被 rename/取代的原件、`_demo`、`*.bak` | 删除；git 用 rename 保留历史 |
| 重复副本 | handoff 与源文件名字不一致、双份 outline | 改 `sync_handoff` 映射，删多余副本 |
| 编译产物 | `dist/`、日志、err、PDF | 不提交；确认 `.gitignore` 命中 |
| 系统垃圾 | `.DS_Store`、`.venv`、`__pycache__` | 删除并忽略 |
| 半成品 | 写了没接线的脚本/字段 | 接线或删除，禁止「以后再说」 |
| 测试夹具残留 | `/tmp` 复制进库的假项目 | 删除 |

**验收**：`git status` 干净或只剩有意变更；`rg '旧文件名|旧路径'` 无未解释命中。

---

## 5. 验证门槛（不过不许写「完成」）

```bash
# 工具与金样板
python3 writing-rules/tools/tests/run_tests.py
python3 writing-rules/tools/check_rule_coverage.py

# 写作门禁（金样板；G8 对结构示范书预期红）
python3 writing-rules/tools/spec_lint.py --gate G0 books/how-to-write-a-tech-book   # …G1 G2 G3 G5 G6 G7
python3 writing-rules/tools/run_gates.py books/how-to-write-a-tech-book
python3 writing-rules/tools/quality_gate.py books/how-to-write-a-tech-book

# 排版（若动了 techbook-typst 或 chapters）
cd techbook-typst && nu build.nu doctor && nu build.nu lint && nu build.nu book
```

- 修 bug：先加**负例测试**再修，禁止只修不测。  
- 改阈值/规则：金样板 12 单元必须能解释命中差异。  
- 禁止用「我觉得对了」代替退出码。

---

## 6. 提交

- 一次提交一个主题；脚手架/清理与功能特性可分开。  
- 信息格式：`type: 一句话动机` + 要点列表 + 验证摘要。  
- 不提交密钥、个人路径、`dist/*.pdf`。  
- 未要求 push 就不要 push。

---

## 7. 禁止事项

- 手改 `A-规则总表.md`、handoff 拷贝件、`dist/`  
- 在章节里 `#set` 或手写「第 N 章 / 图 N-M」编号  
- 把 L2（读者测试、领域正确性）标成自己已通过  
- 跳过门禁用叙述代替（「已检查」必须能指到命令与输出）  
- 一次 PR 搅动写作规范 + 排版引擎 + 大规模重命名（除非用户明确要求）  
- 用占位假来源过 G0 后当真数据发布

---

## 8. 收尾检查表（可直接打勾）

- [ ] 范围符合 §0，未顺手大重构  
- [ ] 命名/目录符合 §2，相关工具与文档已同步  
- [ ] `CHANGELOG.md` 有条目；必要时 `PROBLEMS.md` / 路由表已更新  
- [ ] 过时文件与重复副本已清（§4）  
- [ ] `run_tests.py` 全绿；必要时编译 PDF  
- [ ] `git status` 无意外产物  
- [ ] 说明写到「下一只 Agent 能直接用」（§3）
- [ ] 若是「写书」而非「改仓库」：已走 `writing-rules/workflow/WORKFLOW.md` 并留阶段状态

---

## 9. 快速入口

| 要… | 打开 |
| --- | --- |
| 任务路由 | [`README.md`](README.md) |
| 人类贡献说明 | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| 已知问题与修法史 | [`PROBLEMS.md`](PROBLEMS.md) |
| 改写作规范 | [`writing-rules/如何改规范.md`](writing-rules/如何改规范.md) |
| 排版契约 | [`techbook-typst/AGENTS.md`](techbook-typst/AGENTS.md) |
| 闭眼建书 | `writing-rules/tools/init_book.py` / `assemble_book.py` |
| 紧凑门禁 / 清记忆 | `writing-rules/tools/run_gates.py` / `memory_maint.py` |
| 质量体量验收 | `writing-rules/tools/validate_quality.py` / `quality_gate.py` |

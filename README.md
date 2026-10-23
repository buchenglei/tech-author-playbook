# tech-author-playbook

**技术书籍生产剧本**：写什么、怎么写成一本可读的书，以及如何排成 PDF。

> **先判断你是来做什么的：**
> - **用本库写一本书** → 读本文件 §3 路由表 → `writing-rules/workflow/WORKFLOW.md`
> - **维护 / 修改本仓库** → 根目录 [`AGENTS.md`](AGENTS.md)
> - **只用排版引擎** → [`techbook-typst/AGENTS.md`](techbook-typst/AGENTS.md)
>
> **人类：** 两条能力线可单独取用。写作规范见 `writing-rules/`，Typst 成书见 `techbook-typst/`。

---

## English

**tech-author-playbook** is a method + toolchain for writing technical books:

- `writing-rules/` — production rules (verifiable claims, outline schema, unit specs, E0–E3 evidence levels, gates G0–G8) and `spec_lint.py` / `validate_quality.py`
- `techbook-typst/` — Typst book engine (B5 layout, semantic components, `md2typ.py` assembly)
- `books/how-to-write-a-tech-book/` — golden sample written through the full S0–S7 flow

Quick checks: `python3 writing-rules/tools/tests/run_tests.py` · `cd techbook-typst && nu build.nu doctor && nu build.nu book`

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md). Copyright CodeBu, MIT.

---

## 1. 一分钟定位

| 问题 | 答案 |
| --- | --- |
| 这个仓库是什么 | 写技术书的**方法 + 工具**：内容质量规范 × 成书排版引擎 |
| 谁执行 | AI Agent 为主；人类做读者验证、终审与无法委托的判断 |
| 最终交付 | 一本可出版的技术书籍（正文 + 配套资产），排版产物为 PDF |
| 不是什么 | 不是通用排版引擎、不是 CMS、不是「聊天写稿」玩具 |

**分工一句话**：

- `writing-rules/` 管**写什么、写成什么样**（结构、断言、文风、门禁）
- `techbook-typst/` 管**怎么排成书、编出 PDF**（版式、组件、编译）

两条线职责不重叠。内容质量不过关，排版再好也不是书；排版契约不遵守，好内容也装不成书。

---

## 2. 仓库地图

```text
tech-author-playbook/
├── README.md                 ← 你在这里（AI 入口 / 任务路由）
├── AGENTS.md                 ← ★ 仓库维护契约（改本库前必读）
├── LICENSE
├── PROBLEMS.md               ← 真书流程暴露的问题与工程修法
├── books/                    # 金样板书稿（writing-rules 实战工程）
│   └── how-to-write-a-tech-book/
│       ├── 01_立项卡.json … 08_读者假设.md
│       ├── units/            # 12 个冻结写作单元（spec + 正文）
│       └── handoff/          # S7 交接包六文件
├── writing-rules/            # 内容生产：规范 + 门禁脚本 + 可填写 kit
│   ├── README.md             # 规范入口
│   ├── 技术书籍写作规范_v1.md  # 导航入口（正文在 spec/）
│   ├── spec/                 # 规范分片 00–10 + 附录 A–H
│   ├── 如何改规范.md          # 改规则/阈值/门禁指南
│   ├── workflow/             # ★ 作者/读者/编辑 + 人 四阶段工作流
│   ├── tools/                # spec_lint / validate_quality / run_gates / init_book / …
│   └── kit/                  # 立项卡、大纲、单元 spec、台账、术语、提示词…
└── techbook-typst/           # 排版成书：Typst 基础库 + 样书 + 构建
    ├── AGENTS.md             # ★ 排版作业契约（写书/改书必读）
    ├── README.md             # 人类快速上手
    ├── DESIGN.md / FONTS.md  # 设计取舍 / 字体
    ├── config.toml           # 书目元数据 + 版式
    ├── main.typ              # 编译入口（只装配）
    ├── chapters/             # 正文（样书《如何写一本技术书》）
    ├── tools/md2typ.py       # 写作单元 Markdown → Typst 装配
    ├── src/                  # 引擎（theme / component / cover / lib）
    ├── src/template/         # init 新书稿骨架
    ├── build.nu              # 构建 / init / install
    └── tests/smoke.typ       # 冒烟
```

---

## 3. 按任务路由（Agent 先查这张表）

| 你要做的事 | 进入 | 必读 | 不要先读 |
| --- | --- | --- | --- |
| **用本库写一本书（外部 Agent）** | `writing-rules/workflow/WORKFLOW.md` | 全文 + `roles/` | 先别写正文 |
| 第一次接手本仓库 | 本文件 | §1–§5 | 子模块源码 |
| **维护/修改本仓库** | 根目录 `AGENTS.md` | 全文（收尾检查表） | 先别改代码 |
| **看流程示范（结构骨架）** | `books/how-to-write-a-tech-book/` | `handoff/00_README.md` + `PROBLEMS.md` | 排版引擎；**注意体量未达 G8** |
| **新建标准写作工程（闭眼脚手架）** | `writing-rules/` | `tools/init_book.py` + `CONTRIBUTING.md` 闭眼节 | 排版引擎 |
| 为一本新书立项、定读者、定大纲 | `writing-rules/` | `kit/stage_prompts.md` S0–S2 + `spec/02-立项.md` | 排版引擎 |
| 写一节 / 改一节正文 | `writing-rules/` | 主规范 §4 + 该节 spec + `kit/stage_prompts.md` | 全书正文、排版细节 |
| 打磨语言、去 AI 腔 | `writing-rules/` | 主规范 §6 + 附录 H | 排版引擎 |
| 跑校验、过门禁 | `writing-rules/` | `README.md` 命令表 + 主规范 §7 | — |
| 把写作单元装成 Typst 章 | `techbook-typst/` | `tools/md2typ.py` + `AGENTS.md` | 写作规范长文 |
| 装配章节、出 PDF、改版式 | `techbook-typst/` | **`techbook-typst/AGENTS.md`** | 写作规范长文 |
| 装配写作工程并编译 | `writing-rules/` | `tools/assemble_book.py`（见 CONTRIBUTING 闭眼节） | — |
| 建 Typst 薄书稿/快照 | `techbook-typst/` | `AGENTS.md` §3 | — |
| 加图/表/清单、交叉引用、附录 | `techbook-typst/` | `AGENTS.md` §5–§6 | — |
| 改封面/页眉/编号/字体 | `techbook-typst/` | `AGENTS.md` §7、§10 + `DESIGN.md` | 章节正文 |
| 排查编译失败 | `techbook-typst/` | `AGENTS.md` §11 速查 | — |
| 查工具/规范被真书挊出的问题 | 根目录 | `PROBLEMS.md` | — |

**加载原则**：一次只加载当前任务需要的文件。长文规范按章取用，不要通读 1800+ 行再动手。

---

## 4. 出书全流程（两条线如何串）

```text
writing-rules                          techbook-typst
─────────────                          ─────────────
S0 立项 ──► S1 读者 ──► S2 大纲
                │
                ▼
        S3 样章 / 写作单元 ──► 正文（每节冻结）
                │                      │
                ▼                      ▼
        S4–S6 扩写、实验、语言      md2typ.py 装配 chapters/
                │                      │
                ▼                      ▼
        S7 校验门禁 ──────────►  编译 PDF（nu build.nu）
                │                      │
                ▼                      ▼
            交接 / 出版  ◄────  dist/book.pdf + 校验清单
```

流程示范书：`books/how-to-write-a-tech-book/`（**结构示范**；当前 G0–G3、G5–G7 通过，**G4 未实现、G8 未达合同下限**，不可当「写成这样就能交」的样例）→ `assemble_book.py` → `techbook-typst/chapters/chN.typ` → `dist/book.pdf`。完整交付形态见 `writing-rules/workflow/templates/08_交付规范.md` 与 `docs/eval/` 中的真实书稿复盘。

闭眼流水线：`init_book.py` 建工程 → 写 `units/` → `assemble_book.py --compile` 出 PDF。

| 阶段 | 内容线产出 | 排版线动作 |
| --- | --- | --- |
| 立项与结构 | 立项卡、读者表、`outline.json` | 可同步建书稿骨架（`init` / `init-linked`） |
| 写作 | 逐节 spec → 正文 → 冻结 | 章节落盘 `chapters/`，用语义组件 |
| 装配 | 全书结构、术语、台账一致 | 配目录章节清单、前言/附录、图表编号 |
| 交付 | 门禁通过、交接包 | `doctor` / `lint` / 目视 PDF |

**边界**：写作线不规定字号页边距；排版线不规定文风断言。不要把两套规则搅在同一段修改里。

---

## 5. 全局硬约束

1. **不虚构**：API、输出、版本、数字都必须可溯源（写作线 §1.3、§5.6）。
2. **不自证**：「已检查」必须能指出谁检、用什么命令、结果是什么（写作线 §7）。
3. **章节不写样式**：`techbook-typst` 书稿禁止 `#set page/text/par`，禁止手写「第 N 章 / 图 N-M」编号。
4. **产物只写 `dist/`**：同名覆盖，不堆 `-new` / `-latest`。
5. **改引擎要回归**：动 `techbook-typst/src/` 后必须 `doctor + lint + book` 并目视 PDF。
6. **读者验证只能由人做**：Agent 不得声称「读者已验证」。
7. **P1 未签字不得批量写作**：第 1 章没有读者/编辑报告 + 人签字，不得进入第 2 章；`quality_gate.py` 会拦。
8. **冻结是审阅动作**：任何脚本不得自动写 `frozen`；代码/证据未验不得冻结。

---

## 6. 不要做的事

- 不要把 `writing-rules/` 的规则抄进章节正文当内容。
- 不要在 `techbook-typst/chapters/` 里改 `src/` 才能解决的样式问题。
- 不要从随机源文件或长规范中段开始工作而不查 §3 路由表。
- 不要跳过门禁用「我觉得可以了」代替判定（写作线 G0–G8）。
- 不要默认把两个子模块交叉引用写进书稿正文（当前约定：各自独立演进，合并叙事等双方稳定后再做）。

---

## 7. 文档索引（只记入口）

| 文件 | 角色 | 打开时机 |
| --- | --- | --- |
| `README.md`（本文件） | 项目地图 / 任务路由 | 任何会话开始 |
| `writing-rules/workflow/WORKFLOW.md` | **写书三角色工作流** | 外部 Agent 写书开工 |
| **`AGENTS.md`** | **仓库维护契约** | 改本库任何文件之前 |
| `writing-rules/README.md` | 内容规范入口 | 做写作、校验任务 |
| `writing-rules/技术书籍写作规范_v1.md` | 规范导航入口 | 不知从哪读时 |
| `writing-rules/spec/` | 写作规范分片（真源） | 按任务分片读 |
| `writing-rules/如何改规范.md` | 改规则贡献指南 | 动 MUST/阈值/门禁时 |
| `writing-rules/kit/stage_prompts.md` | S-1…S7 阶段提示词 | 按阶段取用 |
| `writing-rules/tools/spec_lint.py` | 校验与门禁 | 校验、发布前 |
| `writing-rules/tools/quality_gate.py` | 质量优先硬门禁 | P1 签字、报告、台账、代码 |
| **`techbook-typst/AGENTS.md`** | **排版与成书契约** | 写/改/编书稿 |
| `techbook-typst/README.md` | 排版人类速览 | 人读或要最短示例 |
| `techbook-typst/DESIGN.md` / `FONTS.md` | 取舍 / 字体 | 改视觉、调字体 |

---

## 8. 环境依赖

| 组件 | 用于 | 说明 |
| --- | --- | --- |
| Typst 0.15+ | 编译 PDF | `techbook-typst/` |
| Nushell（`nu`） | 构建脚本 | `techbook-typst/build.nu` |
| Python 3 | 写作校验 | `writing-rules/tools/spec_lint.py` |

快速自检写作线：

```bash
python3 writing-rules/tools/quality_gate.py books/<slug>
```

快速自检排版线：

```bash
cd techbook-typst
nu build.nu doctor && nu build.nu lint && nu build.nu book
```

---

## 9. 许可

MIT（见 [LICENSE](LICENSE)）。

# 贡献指南

感谢参与 **tech-author-playbook**。**Agent 修改本仓库请先读根目录 [`AGENTS.md`](AGENTS.md)（维护契约）**；本文侧重协作分工与 PR 约定。本仓库是「写技术书」的方法与工具：内容规范（`writing-rules/`）× 成书排版（`techbook-typst/`）。两条线职责不重叠，请先对准你改的那一条。

## 仓库地图（贡献时看这里）

| 你想改 | 进入 | 必读 | 门禁 |
| --- | --- | --- | --- |
| 写作规则 / 门禁脚本 / kit 模板 | `writing-rules/` | `writing-rules/spec/` 与 `writing-rules/如何改规范.md` | `spec_lint` 自检 + 测试 |
| Typst 引擎 / 版式 / 组件 | `techbook-typst/` | `techbook-typst/AGENTS.md` | `nu build.nu doctor && lint && book` |
| 金样板书稿（方法演示） | `books/how-to-write-a-tech-book/` | `handoff/00_README.md` | G0–G8 |
| Markdown → Typst 装配 | `techbook-typst/tools/md2typ.py` | `PROBLEMS.md` P7 | `writing-rules/tools/tests/` |
| 开发者笔记 / 已知问题 | `PROBLEMS.md` | — | 保持「现象→根因→修法→验证」四段 |

## 提 PR 前的硬性要求

1. **不虚构来源**。台账里的 `url` 使用 `https://…` 或 `repo:相对路径`，不要写死任何托管平台地址。
2. **不自证通过**。`已检查` 必须能指出：谁检、用什么命令、结果是什么。
3. **门禁绿了再交**。
   - 改写作线：`python3 writing-rules/tools/tests/run_tests.py`，并对金样板跑 G0–G8（G8 对结构示范书会红，见其 handoff 声明）。
   - 改排版线：`cd techbook-typst && nu build.nu doctor && nu build.nu lint && nu build.nu book`，并目视 `dist/book.pdf`。
4. **产物不进库**。`dist/`、`*.pdf`、日志、`.DS_Store` 由 `.gitignore` 排除。
5. **动引擎要回归**。改 `techbook-typst/src/` 后必须全量重编样书，不能只编正在改的章。

## 人类与 Agent 的分工

| 事项 | 人类 | Agent |
| --- | --- | --- |
| 读者任务测试 / 领域正确性 | **只能人做** | 不得代签 |
| 写单元、跑 lint、出 PDF | 可委托 | 应按 `stage_prompts.md` 流程 |
| 规则取舍与范围拍板 | **人拍板** | 只给选项与代价 |
| 交付状态 `ready` | 人确认后才能写 | 只能写 `draft` |

同一单元的「作者」与「校验者」不要混作一人（TEAM-01）。单 Agent 环境请在 `handoff/04_check.json` 声明「未做独立校验」。

## 改规范（writing-rules）

见 **[writing-rules/如何改规范.md](writing-rules/如何改规范.md)**。摘要：

- 规则 ID 与强度只在正文定义，附录 A 规则总表由脚本派生。
- 新增 MUST 必须写清判定方式与失败动作，否则降级 SHOULD。
- 阈值改动要写进待校准记录，并在 PR 里说明依据。

## 改排版引擎（techbook-typst）

1. 改 `src/`（theme / component / tokens），不要在 `chapters/` 里 `#set page/text/par`。
2. 新组件在 `src/book.typ` re-export，并更新 `AGENTS.md` 组件表。
3. 视觉令牌进 `src/lib/tokens.typ`，优先配置化，不写死颜色字号。

## 金样板与 handoff

- `books/how-to-write-a-tech-book/` 是按规范写完的实战样例，修改它等于改「教材」。
- `handoff/` 六文件是交付快照。**不要手改拷贝件**；改完源文件后执行：

```bash
python3 writing-rules/tools/sync_handoff.py books/how-to-write-a-tech-book
```

  脚本会在 `handoff/00_README.md` 写入本次同步时间（拷贝时间点）。

## 闭眼产出标准结构（Agent 请走这条）

```bash
# 1) 脚手架（目录名与 G0–G8 一致）
python3 writing-rules/tools/init_book.py my-book --title "书名" --claim "可证伪承诺"

# 2) 写作：按 kit/stage_prompts.md 填 01–08，units/Cxx-Sy.spec.md 先于 .md

# 3) 一条命令装配成可编译书稿（units → chapters/chN.typ → config.toml）
python3 writing-rules/tools/assemble_book.py books/my-book \
  --engine techbook-typst --out techbook-typst/chapters --compile

# 变体：输出到书稿自己的 chapters/（薄项目），不改引擎 config
python3 writing-rules/tools/assemble_book.py books/my-book
```

约定：第 N 章文件名固定为 `chapters/chN.typ`；无正文的章也会生成占位骨架，保证能编译。

## 测试

```bash
python3 writing-rules/tools/tests/run_tests.py
```

覆盖：`spec_lint` 门禁与已修 bug 回归、`md2typ` 装配、`sync_handoff`。新修工具问题请补负例（见 `PROBLEMS.md`）。

## 提交说明

- 一次 PR 只动一条线（写作 **或** 排版 **或** 仓库工程），除非是路径重命名这类机械重构。
- 写清：动机、改了什么、如何验证（命令 + 退出码/摘要）。
- 版权主体为 **CodeBu**（见 `LICENSE`）；不要引入写死的仓库主页 URL。

## 行为准则

对事不对人。嘲讽读者或贡献者的内容会被要求改写。技术争议用证据与门禁说话，不靠声量。

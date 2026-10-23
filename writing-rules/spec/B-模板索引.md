# 附录 B 模板索引

模板在 `kit/`，字段与 §1.1、§3.3、§4.2 一一对应。复制到项目后按 §4.1 的短名重命名（如 `02_outline.json` → `outline.json`），字段名不改。

| 文件 | 对应章节 | 用途 |
|---|---|---|
| `kit/01_立项卡.json` | §1.1 | 选题与承诺，G0 输入 |
| `kit/02_outline.schema.json` | §3.3 | 结构 schema，G2 校验依据 |
| `kit/02_outline.json` | §3.3 | 可直接跑 G2 的示例 |
| `kit/03_单元spec.md` | §4.2 | 一节写作合同 |
| `kit/04_ledger.csv` | §1.3、§4.3 | 断言—证据台账 |
| `kit/05_state.json` | 第 0.4 节 | 阶段、进度、阻塞、重试 |
| `kit/06_glossary.json` | §4.6 | 术语与禁用别名 |
| `kit/07_style.kernel.md` | §8.7、附录 H | 文风基线，3–5 段例句 |
| `kit/stage_prompts.md` | 全流程 | 各阶段提示词，按阶段加载 |

**B-01**（MUST｜自检｜阻断）：模板字段被改动即视为接口不兼容，须同步更新本规范与校验脚本。

---


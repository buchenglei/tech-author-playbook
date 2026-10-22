# PROBLEMS — 本轮真书写作暴露的问题与修法

用 writing-rules 把《如何写一本技术书》从 S0 写到 S7 的过程中，工具与规范本身被挊出这些问题。每条含：现象 → 根因 → 修法 → 验证。

---

## P1. `check_claims` 解包崩溃（P0，阻断写作）

**现象**：对 `units/C01-S1.md` 跑 `spec_lint.py --profile manuscript` 直接 Traceback。

**根因**：`paragraphs()` 产出 `(start, buf, sec)` 三元组，`check_claims` 按 `for start, buf in ...` 解包。

**修法**：改为 `for start, buf, _sec in paragraphs(...)`。

**验证**：12 个单元全部可跑 lint；退出码 0。

**教训**：脚本从未被真实书稿执行过。样书是 `.typ`，不是 `.md`，所以 L0 路径一直是死的。

---

## P2. G1 门禁未实现

**现象**：`--gate G1` 返回 `未实现的门禁 G1`，P1 一条，却被阶段提示词写成硬门禁。

**根因**：规范 §7.2 要求 G1，`spec_lint.py` 的门禁表只实现了 G0/G2/G6 的文件检查。

**修法**：实现 G1——查 `08_读者假设.md` 存在、假设行含 given/inferred/assumed、起点清单存在且为动作项、有未验证声明。

**验证**：本书 `--gate G1` 退出码 0。

---

## P3. G3/G5/G7 只检查「第一个 .md」

**现象**：目录下有 12 个正文单元，门禁只扫到按文件名排序的第一个。

**根因**：实现时假设「书稿=一个文件」，与 §4.1 的 `units/` 布局冲突。

**修法**：优先扫 `units/*.md`（排除 `.spec.md`）；G5 增加 outline 中 `status=frozen` 的节必须有正文文件。

**验证**：`--gate G3/G5` 在 12 单元下仍通过；删掉一个 frozen 正文会失败。

---

## P4. manuscript 模式把规范规则 ID 当未定义规则

**现象**：正文写「TOP-01」被报 `S-RULE-01 引用了不存在的规则`，P0。

**根因**：规则自洽检查是为规范正文（附录 A 派生）设计的；书稿引用规范 ID 是正常行为。

**修法**：`profile=manuscript` 时跳过「正文提到但未定义的 ID」检查。

**验证**：C02-S1/S2 含 TOP-01 引用，P0=0。

---

## P5. G2 不检查 `bridge`，与 STR-06 不一致

**现象**：规范 STR-06 要求 produces 与 bridge 非空，G2 只查 produces。

**根因**：门禁实现落后于正文规则。

**修法**：G2 增加 bridge 非空；顺带检查 status 枚举、role 目标落在本章 sections、target_words≥30000、paths 节点存在。

**验证**：本书 `--gate G2` 退出码 0；故意清空 bridge 会报 STR-06。

---

## P6. G6 与 `units/` 布局不接

**现象**：交接包六文件按 §9.4 是「一个目录」，但 G6 只在调用目录根找，和书稿工程目录结构冲突。

**修法**：G6 若根目录缺文件，自动落到 `handoff/`。

**验证**：`--gate G6 books/how-to-write-a-tech-book` 与 `.../handoff` 均通过。

---

## P7. 写作线与排版线无格式契约

**现象**：写作线产出 Markdown 单元；`techbook-typst` 吃 `chapters/*.typ`。中间没有转换约定，原样书直接是 Typst，绕过了全部写作门禁。

**根因**：仓库 README 写明两线独立演进，合并「等双方稳定」——结果是永远没有交接。

**修法（本轮）**：增加 `tools/md2typ.py`（见下节）：把单元 Markdown 装配为带语义组件的 Typst 章节。约定：

| Markdown | Typst |
| --- | --- |
| `# 章标题` | `= 标题` |
| `## 小节` | `== 标题` |
| 表格 | `#tbl(...)` |
| 有序/无序列表 | Typst 列表 |
| 围栏代码 | ` ``` ` 代码框 |
| 「## 附：…」表 | 同表格映射 |

**残留**：语义组件（#goal/#tip/#best）仍需编者在 Typst 里补，自动转换只保结构不保修辞。这是有意边界：排版线不决定文风。

---

## P8. 样书原第三章越权

**现象**：原样书第 3 章《用 techbook 组织书稿》讲 Typst 组件与目录，属于排版工具文档，不是「如何写一本技术书」的内容。

**根因**：样书同时承担「写作方法演示」和「模板说明书」两个身份，scope 未划。

**修法**：按立项卡 `scope_out` 砍掉排版章；组件速查降为附录，不进 claim 路径。目录改成 C01–C04 纯方法链。

---

## P9. 「最后」「容易」「完美」等词的规范/脚本不一致

**现象**：正文用「容易」被 L-LANG-01 打回；规范 §6.3 表格里写了「最后」作填充过渡，但 `FORBIDDEN` 列表没有「最后」。

**根因**：词表以脚本为准，规范叙述略宽。

**修法**：本轮正文改写避用；词表与规范以脚本 `FORBIDDEN` 为单一真源，规范表中「最后」仅作示例不强制。若需对齐，应改脚本或改规范，不得两处各说各话。

---

## P10. 单元字数低于参考区间

**现象**：预算 2500–5000，实写多在 800–1300 字（`chinese_len`）。

**根因**：STR-12 允许「讲透了不补写」；另 `chinese_len` 与 Word「字数」口径不同。

**修法**：不注水。在 spec 的 word_budget 标注实际完成；交接包声明口径。

**残留**：附录 F 阈值仍待真实书稿校准——本轮正好是第一批样本，应在下一本书前回填。

---

## P11. 单 Agent 无法做 TEAM-01 角色分离

**现象**：规范要求作者与校验者不得同一角色实例；当前环境只有一个 Agent。

**根因**：流程假设多角色；单会话现实不满足。

**修法**：按 TEAM-01 声明「未做独立校验」，校验以脚本 + 人类抽检承担，写进 `04_check.json` L2。

---

## 优先级建议（给下一轮）

1. 用本书的 12 个单元当 `spec_lint` 回归夹具（每个曾踩过的问题加一个负例）。
2. 回填附录 F：句长/段落阈值用本轮语料粗校准。
3. 定稿 md→typst 契约，把 `md2typ.py` 纳入 `techbook-typst/build.nu`。
4. 找两名外部作者跑 kill_criteria 第一条，补 L2。

---

## 本轮已修清单（代码）

| 文件 | 改动 |
| --- | --- |
| `writing-rules/tools/spec_lint.py` | check_claims 解包；G1 实现；G3/G5/G7 全量扫描；G2 bridge/role/target_words/paths；G6 handoff 回落；manuscript 跳过规则定义自洽 |
| `books/how-to-write-a-tech-book/**` | 新建完整书稿工程 |
| `techbook-typst/tools/md2typ.py` | 新增 Markdown→Typst 装配器 |

---

## P12. 外评暴露：规则声称脚本一半悬空，G4 假绿，G0 占位可过（P0，可信度）

**现象**（两份外评 + C# 书稿交叉验证）：`A-规则总表` 标称「脚本 L-VOL-01」等 20+ 条在 `tools/*.py` 无实现；`--gate G4` 返回「未实现」却在 `run_gates` 显示 PASS；`init_book` 占位来源能过 G0；金样板 G8 红但 README 写「已跑通」。

**根因**：迭代快于真源同步——门禁/工具改了，规范判定标注、README 信号、金样板定位没跟上；`run_gates` 只看 P0，未实现门禁被报成 P1 因而假绿。

**修法**：
1. 新增 `check_rule_coverage.py`（RULE-01 自动化）+ 测试；
2. 未实现门禁改 P0，`run_gates` 诚实 FAIL；
3. G0 拒「待改写/TODO」占位；`check_claims` 逐句核对；
4. L-VOL-01 由 `validate_quality` 真实产出，其余悬空判定降为「自检」或改指真实 ID；
5. README/handoff 明确金样板为「结构示范，体量未达 G8」。

**验证**：`run_tests.py` 42 passed；`check_rule_coverage.py` COVERAGE_PASS；`run_gates` 对金样板 G4 FAIL、G8 FAIL（与 handoff 声明一致）。

**教训**：**示范物与门禁矛盾时，Agent 跟随示范物。** 改门禁后的三问——金样板还过吗？README 提到了吗？判定标注还真实吗？——任一答不上就不算完成。

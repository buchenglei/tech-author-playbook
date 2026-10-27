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
| `![alt](p)` | `#fig(image(p), caption: [alt])` 或行内 `#image`；`--asset-dir` 复制资源 |
| `[text](url)` | `#link("url")[text]` |
| `> 引用` | `#quote[...]` |
| `---` / `***` | `#line(length: 100%)` |
| `<!-- caption: ... -->` | 表注（表前/表后均可） |

**残留**：语义组件（#goal/#tip/#best）仍需编者在 Typst 里补，自动转换只保结构不保修辞。这是有意边界：排版线不决定文风。`#fig/#link/#quote` 已自动转换，图片资源由 `--asset-dir` 复制到书内 `typst/assets/`。

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

---

## P13. 真实书稿 workflow 空转：P1 未签字、自动冻结、证据被清除（P0，质量）

**现象**（C# 交付包复核）：
- `workflow/03_作者改进方案.md`、`05_章节滚动评估.md`、`07_项目反哺报告.md` 是空模板；没有 `workflow/06_终审/`；阶段 1 没有第 1 章读者/编辑报告。
- `00_阶段状态.json` 写 `phase=P3` 与「视为默示确认」；`04_写作宪法`、`09`、`10` 仍是「待确认/待复核」；`reader_persona_confirmed_by_human=false`。
- `05_state.json` 是 `stage=S2`、`done_units` 仅 C00 六节，而 outline 是 86/86 frozen；`04_check.json` 自称全绿，当前工具复跑 G3/G4/G5/G7/G8 红。
- `bulk_write.py` 按字数把节自动写成 `frozen`；`strip_evidence_tags.py` 删除正文 360 处 `E-xxx`，导致读者报告「每个数字可顺藤摸瓜」无法成立。
- C# 片段多处以 `foo.Bar;` 形式缺调用括号；PDF 编译 0 error 被当成代码正确。

**根因**：
1. WORKFLOW 的「不做硬状态机」被实现成「没有状态机」；`validate_quality` 只在 `frozen ≥ 半数` 时看 gates。
2. 报告只查「非空」，不查引文；冻结由脚本自动完成，不是审阅动作。
3. 代码只验 Typst 编译，没有 C# 片段校验；台账从不被加载。
4. Agent 用「默示确认」替代人签字，绕过了 P1/P3 的人类闸门。

**修法**：
1. 新增 `quality_gate.py`：P1 未签字不得进 P2；无人值守只能 draft；报告必须带 `文件:行号 + 原句 + reviewed_revision`；`done_units` 必须等于 frozen；台账 schema 与 E0/E1/E3 校验；C# 片段缺括号/未标 illustrative 即 P0；章末块与质量预算。
2. `init_book` 生成 `human_confirmations.pilot/final` 与 `workflow/06_终审/`；`--family/--target-words` 同源。
3. 规范/模板/README/WORKFLOW 把「冻结是审阅动作」「P1 试点章」「无人值守 draft」写死。
4. `run_tests.py` 新增负例：缺 spec、4 行报告、P1 未签字、坏 CSV 台账、缺调用括号、illustrative 豁免。

**验证**：`run_tests.py` 57 passed；`quality_gate.py` 对 C# 交付包报 P0（阶段/报告/台账/代码），对正常 P2 夹具无 WF P0；金样板 G8 仍按结构示范预期红。

---

## P14. 量产尾部退化 + 门禁声称不可复核（P0，质量；F# 书稿实证）

**现象**（F#《类型优先》交付包复核，48 章 514 页）：
- 流程这次是真的：P1 双评带 `文件:行号+原句` 与 E0 复现（15 条复现 13）、二审闭环、人签字原话留档、P2 滚动评估 17 轮。但**内容前紧后松**：C18 起挂牌标题（`## 机制：…` 55 处）、C27 起「动手练习/验证清单」块整体消失、C42 起 spec 无 E-id（18 份）与台账 `level='A'`（24 行）、单节掉到 686 字。
- **滚动评估 17 轮均写「spec_lint P0=0」「无违宪」，当前工具实测 103/145 节有 P0**（禁用词 147、数字未挂账 59、挂牌 55）；门禁结论无回执、无法复核。
- 合同口径未钉死：字数口径 cjk_len/chinese_len 两种结论（48 vs 26 节薄）；证据承载策略（正文 E-xxx vs 台账）与基线 CLAIM-01 直接打架，融合评估误判为「不冲突」。
- 工具漂移：写作期自造 `prose_check.py`、自修 `md2typ.py`（占位符单层展开、`#code` 反引号等），均未回流；`research/*.md` 未随包。
- 交付包自造布局（书稿源码/反馈文件/…）：README 竟是 playbook 仓库 README 副本；附录 A–J 承诺了只交付 80 字节占位；handoff/MANIFEST/LICENSE 全缺；包名「终版」但 phase=P2、final 未签。
- 工具自身缺陷：`spec_lint --json` 在 C16-S1/C26-S4 GBK stdout 崩溃；LANG-05 把 `<!-- src -->` 注释行/英文引文算句长（1271 处多数误报）；L-FORM-01 漏去冒号挂牌；CODE-03 误报 `var x = a.B;` 属性读取。

**根因**：
1. 质量靠自觉不靠聚合指标：单点检查抓不住「越写越松」的趋势；尾部没有任何指标对比。
2. 门禁结论只写在报告里，没有可重跑回执；「P0=0」是叙述不是证据。
3. 合同缺字数口径/证据策略/交付物清单三个字段，导致规范冲突被口头消解。
4. 交付包不经 `package_book` 就出包，交付契约形同虚设；自造工具不回流。

**修法**：
1. `quality_gate` 增 DECAY-01/02/03（首 ⅓ vs 末 ⅓：体量/禁用词挂牌/证据完整度）、CTR-01/02/03/04（交付物、图数量、合同骨架块）、EVD-14/15（unit 回指、url 须 https://|repo:、本机路径 P0）、QG-05（章末四件事禁挂牌）、WF-23。
2. RPT-11 + `run_gates --write-check` 门禁回执；`revision_log.jsonl` 迁移链使合法修订不失效旧报告。
3. 合同钉死 `word_count_metric` / `evidence_policy` / `deliverables` / `decay_thresholds`；`spec_lint --evidence-policy` 三态。
4. 修工具误报与崩溃（LANG-05 口径、去冒号挂牌、CODE-03、GBK stdout）；`package_book` 交付状态与命名护栏；`08_交付规范` 加 README 书籍化与 tools/ 回流。
5. `run_gates` G4 默认 SKIP、G7 依赖 G8（门禁单调）；CI 上线写作线回归。

**验证**：`run_tests.py` 87 passed（新增 28 条回归）；F# 案例跑新门禁复现人工结论：DECAY-01 前 16 章均 2764 字 → 末 16 章均 920 字、DECAY-03 spec 100%→62%、EVD-14 51 行、EVD-15 122 行；工具误报负例（注释行/西文引文/属性读取/去冒号挂牌）全绿。

---

## P15. 可复核性断链 + 固定块悬案 + 阶段-进度越界（P0，质量；Avalonia 书稿实证）

**现象**（Avalonia《实战》交付包复核，26 章 69 节 / 249 页 / 台账 439 条）：
- 三案中内容与交付最规范的一份（台账 E0 376 条全有 cmd/exit/hash、README 书籍化、handoff 六文件、`delivery_status: draft` 诚实声明），但**随书工程 BookVault 未随包**：366 条台账 `url=repo:bookvault` 与 222 处 `src:` 锚点全部悬空，自评最引以为傲的「可复核性」（build 0W0E、test 10/10）读者无法复核。
- **门禁结论无法对账**：自评称「G0–G3、G5–G7 全部 PASS、G8 只剩人设一条 P1」，当前工具实测 G8 P0=29（26 条章末固定块挂牌、2 条报告 revision 失配、1 条多行 new 误报）；`handoff/04_check.json` 回执没记工具版本/git rev，事后无法判定口径。
- **阶段-进度越界**：`phase=P1`、试点/人设/融合全部未签，但 69 节全书完稿——「如实登记 P1」掩盖了未签字量产。
- **固定块悬案**：合同要求「标尺/落地/避坑/小结」块，正文用「## 本章标尺/## 落地：…/## 避坑」小节标题承载；09 融合评估只裁了「现象：/机制：」式违规，没裁这类算不算挂牌——作者按默认解释执行了 69 节。
- 工具侧同案复现：CODE-04 对多行 `new Book` + 换行 `{`（合法对象初始化器）误报。

**根因**：
1. `repo:` 引用只校验 scheme 不校验落地，随书工程漏交不被拦。
2. 门禁回执无版本信息，报告里的「P0=0」是叙述不是证据（RPT-11 治了报告侧，回执侧还缺）。
3. 阶段闸门只查「phase 字段」，不查「内容进度是否越阶段」。
4. 合同固定块与 UNIT-21 禁挂牌的冲突没有强制裁决字段，融合评估可漏裁。

**修法**：
1. `quality_gate` EVD-17：`repo:` 引用落地校验（悬空即 P0，按目标聚合）。
2. `run_gates --write-check` 回执记 `git_rev` + 工具版本 + 合同口径。
3. `quality_gate` WF-24：phase=P1 且试点未签字时，试点外完稿单元 ≥3 即 P0（1–2 个 P1）。
4. 合同新增 `chapter_blocks_as_headings`（true=检查点小节 / false=行文 / 未声明而用标题=QG-06），强制 09 显式裁决并人签字；`spec_lint --allow-block-headings` 按裁决豁免固定块词。
5. CODE-04 多行 new 误报修复；WF-25 工具自改未登记反哺。

**验证**：`run_tests.py` 98 passed（新增 11 条）；Avalonia 案例跑新门禁复现人工结论：EVD-17「366 条 repo:bookvault 悬空」、WF-24「66 个试点外单元完稿」、QG-06「26 单元固定块未裁决」各一条聚合 P0。

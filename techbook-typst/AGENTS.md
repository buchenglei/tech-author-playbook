# AGENTS.md —— techbook 作业说明（写给 AI Agent）

本文件是**排版与成书契约**。你（Agent）按本文可以独立完成：建书稿项目 → 写/改章节 → 编译出 PDF 书籍。

只谈**书籍生产与排版**。内容质量、文风、立项方法不在本库范围。

---

## 1. 这是什么 / 不是什么

| 是 | 不是 |
| --- | --- |
| 专业技术书籍 Typst **基础库** | 通用排版引擎 / CMS |
| TOML 配置 + 语义组件 + B5 成书版式 | 要求改 `src/` 才能写正文的框架 |
| 面向 AI 与作者协作的出书工具链 | 写作质量规范 |

**一句话**：改 `config.toml` 与 `chapters/` 就能出书；视觉、编号、页眉都在 `src/`。

- 包名：`techbook`（`@local/techbook:0.4.0`）
- 编译器：Typst 0.15+
- 样书：`chapters/`（《如何写一本技术书》），产物 `dist/book.pdf`

---

## 2. 仓库地图与职责

```text
/
├── AGENTS.md            # 本文件（AI 作业说明）
├── README.md            # 人类快速入口
├── DESIGN.md            # 设计取舍
├── FONTS.md             # 字体
├── typst.toml           # 包元数据
├── build.nu             # 构建入口（Nushell）
├── main.typ             # 书稿编译入口（只装配，不写正文）
├── config.toml          # 书目元数据 + 版式开关
├── chapters/            # 正文（章 / 前言 / 附录）
├── src/                 # ★ 引擎（所有排版改动在此）
│   ├── book.typ         # 包入口（公共 API）
│   ├── theme.typ        # 版式：页面、书眉、章首页、目录、编号
│   ├── component.typ    # 组件：提示块、表、图、清单、步骤…
│   ├── cover.typ        # 扉页 + 版权页
│   ├── lib/tokens.typ   # 默认令牌 + TOML 解析
│   ├── lib/utils.typ
│   └── themes/*.tmTheme # 代码语法主题
├── src/template/        # init 新书稿的骨架
├── tests/smoke.typ      # 冒烟
├── fonts/               # 可选本地字体
└── dist/                # 唯一输出（git 忽略）
```

| 目录/文件 | 谁改 | 说明 |
| --- | --- | --- |
| `config.toml`、`chapters/` | 书稿作者 / Agent 写书 | 书的身份与内容 |
| `src/` | 模板维护者 | 视觉、组件、令牌；**章节禁止** `#set page/text/par` |
| `build.nu` | 维护者 | 编译、init、install |
| `dist/` | 生成物 | 勿手改、勿提交 |

依赖方向：**chapters → book/component → lib/tokens**，禁止反向。

---

## 3. 完整工作流：从零到 PDF

### 3.1 环境

- `typst` 0.15+
- `nu`（Nushell）
- 可选：环境变量 `TYPST` 指定 typst 路径

### 3.2 使用本仓库出样书

```bash
nu build.nu              # 编译样书 + 冒烟
nu build.nu book         # 仅 dist/book.pdf
nu build.nu doctor       # 冒烟
nu build.nu lint         # 章节禁止 #set page/text/par
```

### 3.3 新建一本自己的书

**方式 A：薄项目（推荐，跟随模板升级）**

```bash
# 在本仓库
nu build.nu install              # 安装 @local/techbook:0.4.0
nu build.nu init-linked 我的书    # 在上级目录生成薄书稿

cd ../我的书
# 改 config.toml，写 chapters/
typst compile --root . main.typ dist/book.pdf
```

**方式 B：快照（离线/冻结版本）**

```bash
nu build.nu init 我的书           # 拷贝引擎进书稿目录
cd ../我的书
typst compile --root . main.typ dist/book.pdf
```

### 3.4 写书 / 改书的循环

1. 改 `config.toml`（书名、作者、章节清单）和/或 `chapters/*.typ`
2. `typst compile --root . main.typ dist/book.pdf`
3. `nu build.nu lint`（在模板仓库）或自查：章节内无 `#set page/text/par`
4. 需要时 `nu build.nu doctor`

产物**只写 `dist/`**，同名覆盖，不要用 `-new` / `-latest` 后缀。

---

## 4. 项目契约

### 4.1 `main.typ`（入口只装配）

```typst
#import "src/book.typ": book   // 薄项目改为 "@local/techbook:0.4.0": book

#let cfg = toml("config.toml")
#let chapter-pagebreak = cfg.at("layout", default: (:)).at("chapter-pagebreak", default: true)

#show: book.with(config: cfg)

#for (i, ch) in cfg.chapters.enumerate() {
  if i > 0 and chapter-pagebreak { pagebreak(weak: true) }
  include ch.path
}
```

不要在 `main.typ` 写正文。

### 4.2 `config.toml`（书目 + 版式）

```toml
[doc]
title = "书名"                  # 必填
subtitle = "副标题"
authors = ["作者"]
team = "团队"
org = "组织/出版社"
version = "v1.0"
date = "2026-01-01"             # YYYY-MM-DD
category = "技术写作"
keywords = ["关键词"]
abstract = "内容简介（上版权页）"
history = [["v1.0", "2026-01-01", "初版", "作者"]]

[layout]
cover = true                    # 扉页 + 版权页
toc = true
toc-depth = 2                   # 目录到 N 级标题
header = true                   # 书眉
chapter-pagebreak = true        # 章前分页
indent = "2em"                  # 首行缩进（书感；写 "0em" 关闭）
paper = "jis-b5"                # 或 "iso-b5" / "a4" 等 Typst 纸张名

[color]
accent = "#1e3a8a"              # 主强调色
# accent-ink / accent-soft / accent-wash 可覆盖

[code]
theme = "github"
theme-path = "themes/github.tmTheme"
show-lang = true
show-lines = true
width = "100%"                   # 与正文同宽

[fonts]
serif = ["Noto Serif SC", "Source Han Serif SC", "SimSun"]
sans = ["PingFang SC", "Microsoft YaHei", "Noto Sans SC"]
mono = ["Maple Mono NF", "Maple Mono", "Cascadia Code", "Consolas"]

[[chapters]]
path = "chapters/preface.typ"
note = "注释，不参与排版"

[[chapters]]
path = "chapters/ch1-intro.typ"
```

缺省字段用引擎默认值（见 `src/lib/tokens.typ`）。

### 4.3 章节文件 `chapters/*.typ`

```typst
#import "../src/book.typ": *    // 薄项目：@local/techbook:0.4.0

= 章标题                        // 不要写「第一章」，编号自动生成

正文……
```

---

## 5. 写作约定

1. **标题只写语义名**。`=` 章、`==` 节、`===` 小节、`====` 条目。编号由模板生成（第 X 章 / N.M / N.M.K）。
2. **前言/序/致谢**用 `#preface(title: "前言")[……]`，不占章号。
3. **附录**用 `#appendix[标题]`，自动「附录 A / B / …」，图注变为 `A-M`。
4. **交叉引用**在组件后贴标签，正文写 `@label`：

   ```typst
   #fig(image("a.png"), caption: [架构]) <fig:arch>
   如 @fig:arch 所示。
   #tbl(..., caption: [对照]) <tab:cmp>
   见 @tab:cmp。
   ```

5. **中英文之间不加空格**（模板已开 `cjk-latin-spacing`）。
6. **正文里的 `#` 必须转义**：`C\#`，或放进 `#code[...]`。
7. **标题/`#code` 内容若以 `=`、`#`、`@` 开头，先转义**（`\=` `\#` `\@`），否则会被解析成语法。
8. **多行代码**用 ` ``` ` 围栏，或 `#listing`；短片段 `#code` / `#path` / `#kbd`。
9. **禁止**在章节里 `#set page/text/par`、写死颜色字号。
10. 章末 `#summary` / `#exercises` / `#goal` 是**可选脚手架**，不必每章都有。

---

## 6. 组件 API（按用途）

导入：`#import "../src/book.typ": *`（或按名导入）。

### 6.1 章结构

| 组件 | 用途 |
| --- | --- |
| `#preface(title: "前言")[body]` | 不编号一级标题（前言/序/致谢） |
| `#appendix[标题]` | 附录起始，图注 A-M |
| `#goal[body]` | 本章目标（可选） |
| `#summary[body]` | 本章小结（可选，章末） |
| `#exercises(题1, 题2, …)` | 章末练习（可选） |

### 6.2 提示与强调

| 组件 | 用途 |
| --- | --- |
| `#tip[body]` | 提示 |
| `#warning[body]` | 注意 |
| `#pit[body]` | 避坑 |
| `#best[body]` | 要点 |
| `#keypoint(title: "要点")[body]` | 要点框 |
| `#lead[body]` | 段落小标题（不进目录） |
| `#quote(attribution: "出处", title: "小标题")[body]` | 引用/摘录 |
| `#hl[body]` | 高亮短语 |
| `#term[body]` | 术语下划线 |

自定义调用块：`#callout(kind: "tip", title: "自定义")[body]`；可在 `config.toml` 的 `[callouts.<kind>]` 覆盖 `label/bar/bg/fg`。

### 6.3 图、表、代码、步骤

| 组件 | 用途 |
| --- | --- |
| `#fig(body, caption: …)` | 插图，编号 **图 N-M** |
| `#tbl(columns: …, header: (…), 行…, caption: …)` | 表格，编号 **表 N-M** |
| `#listing(code, title: …, lang: …, file: …)` | 代码清单，编号 **清单 N-M** |
| `#code-block(code, lang: …, file: …)` | 无题注代码块 |
| `#steps(([标题], [说明]), …)` | 步骤列表 |
| `#code[x]` / `#path[x]` / `#kbd[x]` | 行内代码 / 路径 / 按键 |

围栏代码：

````typst
```rust
fn main() {}
```
````

自动套出版物代码框（行号、语言标签）。

### 6.4 图表题注规则

- 正文按章编号：`图 1-1`、`表 2-3`、`清单 3-1`
- 附录内：`图 A-1`
- 公式：`(1-1)` / `(A-1)`
- **不要手写编号**，增删节后会静默错乱；只贴 `@label` 交叉引用。

---

## 7. 构建与验证

| 命令 | 作用 |
| --- | --- |
| `nu build.nu` / `nu build.nu all` | 样书 + 冒烟 |
| `nu build.nu book` | `dist/book.pdf` |
| `nu build.nu doctor` | 编译 `tests/smoke.typ`，统计字体回退 |
| `nu build.nu lint` | 章节禁止 `#set page/text/par` |
| `nu build.nu package` | 打包到 `dist/pkg/local/techbook/0.4.0` |
| `nu build.nu install` | 安装 `@local/techbook:0.4.0` |
| `nu build.nu init <名>` | 快照新书稿 |
| `nu build.nu init-linked <名>` | 薄书稿 |
| `nu build.nu clean` | 清 `dist/` `out/` |

等价手写：

```bash
typst compile --root . main.typ dist/book.pdf
typst compile --root . --input doc=other/config.toml main.typ dist/other.pdf
```

**验收清单（Agent 自检）**

- [ ] `typst compile` 无 error（字体 `unknown font family` 仅警告）
- [ ] 目录章号正确（前言不占号，第一章=第一章）
- [ ] 图/表/清单编号为 N-M；附录为 A-M
- [ ] 书眉：偶数页书名、奇数页章名；页码在书口
- [ ] 章首页无书眉；前言/附录样式正确
- [ ] 章节内无 `#set page/text/par`
- [ ] 正文 `#` 已转义；标签引用可点击

---

## 8. 常见任务

| 任务 | 做法 |
| --- | --- |
| 改书名/作者 | 改 `config.toml` `[doc]` |
| 增删章 | 加/删 `chapters/*.typ`，并在 `[[chapters]]` 登记 |
| 加图 | `#fig(…, caption: […]) <fig:id>`，正文 `@fig:id` |
| 加表 | `#tbl(…, caption: […]) <tab:id>` |
| 加代码清单 | `#listing(…, title: […])` |
| 加前言 | 新文件 `#preface(...)[...]`，放在 chapters 清单最前 |
| 加附录 | `#appendix[标题]` 起头，放清单最后 |
| 改强调色 | `config.toml` `[color] accent` |
| 改字体 | `config.toml` `[fonts]` |
| 改纸张 | `config.toml` `[layout] paper`（Typst 纸张名，如 `jis-b5` / `a4`） |
| 关书眉 | `header = false` |
| 从旧文迁移 | 标题去掉手写章号；表格改 `#tbl`；代码留围栏或 `#listing`；强调改 `*粗体*` / `#hl` |

---

## 9. 禁止事项（硬约束）

1. **禁止**在 `chapters/` 使用 `#set page/text/par`（`lint` 拦截）。
2. **禁止**手写「第 N 章」「图 N-M」等编号，只用模板编号与 `@label`。
3. **禁止**在章节写死颜色、字号、页边距；样式只改 `src/` 或 `config.toml`。
4. **禁止**把引擎文件拷进书稿目录长期手维护（用 `@local` 或一次性 snapshot）。
5. **禁止**在未验证的情况下修改 `src/theme.typ` 的编号/计数逻辑——改完必须全量重编样书。
6. **禁止**用 emoji 作提示块图标（本库调用块为纯文字标签）。
7. 标题与 `#code` 内容中的 `#` `=` `@` 必须转义，否则编译失败或产生错误结构。

---

## 10. 何时改引擎（src/）

仅当需要**新组件、新视觉、新编号规则**时：

1. 改 `src/lib/tokens.typ`（令牌/默认值）或 `src/component.typ`（组件）或 `src/theme.typ`（版式）
2. 如需暴露给章节，在 `src/book.typ` re-export
3. 跑 `nu build.nu doctor && nu build.nu lint && nu build.nu book`
4. 目视 `dist/book.pdf`：封面、目录、章首页、书眉、图注、附录

改 `src/` 属于模板变更；纯写书不要动它。

---

## 11. 故障速查

| 现象 | 处理 |
| --- | --- |
| `the character # is not valid in code` | 代码模式里写了 `#xxx`；改为不带 `#` 的函数调用或包进内容块 |
| `unclosed delimiter` | `#code[#]` 等未转义；写 `#code[\#]` |
| `pagebreaks are not allowed inside of containers` | 不要在 `context`/`block` 内 `pagebreak`；用 `main.typ` 章间分页或组件首尾 `pagebreak(weak: true)` |
| `label <x> does not exist` | 交叉引用名不一致，或 `@` 在 `#code` 里未转义 |
| `cannot reference context` | 标签贴在了 `context` 外层；图/表请用 `#fig`/`#tbl`（已保证 label 可用） |
| `unknown font family` | 仅回退警告；见 `FONTS.md`，可换 `[fonts]` |
| 目录章号不对 | 前言必须用 `#preface`；不要手写「第一章」 |
| 图注不是 N-M | 确认用了 `#fig`/`#tbl`/`#listing`，不是裸 `figure` |
| `dist/*.pdf` 写失败 | 关闭占用该文件的预览 |

---

## 12. 样书即文档

- `chapters/preface.typ` + `ch1.typ`…`ch4.typ` + `appendix-a.typ` 演示常用结构与组件（样书《如何写一本技术书》，由 assemble_book.py 装配）。
- 对照源文件与 `dist/book.pdf` 学习调用方式；正文由 `tools/md2typ.py` 从写作单元装配。
- 新书可用 `nu build.nu init` 得到最小骨架（`src/template/`）。

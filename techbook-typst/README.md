# techbook · 专业技术书籍 Typst 基础库

一套**拿来就能出书**的 Typst 基础库：TOML 配置、B5 成书版式、书眉页码、图表 `N-M` 编号、语义组件。

面向：

1. **人**：写技术书籍，希望版式统一、少改代码；
2. **AI Agent**：完整作业说明见 **[AGENTS.md](AGENTS.md)**，据此写作/编辑并编译出 PDF 书籍。

> 设计取舍见 [DESIGN.md](DESIGN.md)；字体见 [FONTS.md](FONTS.md)。

---

## 这是什么

| 是 | 不是 |
| --- | --- |
| 技术书籍排版基础库 + 构建脚本 | 通用排版引擎 |
| 书稿项目：`config.toml` + `chapters/` | 要求改 `src/` 才能写正文的框架 |
| B5 成书视觉（书眉、章首页、版权页） | 文档/博客模板 |

**一句话**：改 `config.toml` 与 `chapters/` 就能出书；视觉与编号统一在 `src/`。

---

## 快速开始

### 环境

- [Typst](https://typst.app) 0.15+
- [Nushell](https://www.nushell.sh)（`nu`）

### 编译样书

```bash
nu build.nu book         # → dist/book.pdf
nu build.nu doctor       # 冒烟
nu build.nu lint         # 章节禁止 #set page/text/par
```

### 新建一本自己的书

```bash
nu build.nu install            # 安装 @local/techbook:0.4.0
nu build.nu init-linked 我的书  # 薄书稿（推荐）
# 或 nu build.nu init 我的书    # 快照（拷贝引擎）

cd ../我的书
# 改 config.toml、写 chapters/
typst compile --root . main.typ dist/book.pdf
```

---

## 书稿项目结构

```text
my-book/
├── config.toml      # 书目元数据 + 版式
├── main.typ         # 编译入口（只装配）
├── chapters/        # 前言、章、附录
└── dist/            # 产物
```

章节示例：

```typst
#import "../src/book.typ": *

= 章标题          # 不要写「第一章」

#tip[提示] #warning[注意] #pit[避坑] #best[最佳实践]
#keypoint[要点]
#tbl(columns: 2, header: ("A","B"), ("1","2"), caption: [表题])
#listing("code", lang: "python", title: [清单])
#summary[小结]
```

前言 `#preface`、附录 `#appendix`、交叉引用 `@fig:xxx`。完整组件表与约定见 **[AGENTS.md](AGENTS.md)**。

---

## 产物

| 文件 | 内容 |
| --- | --- |
| `dist/book.pdf` | 样书《如何写一本技术书》 |
| `dist/smoke.pdf` | 冒烟 |

输出只写 `dist/`，同名覆盖。

---

## 职责边界

| 目录 | 谁改 |
| --- | --- |
| `config.toml`、`chapters/` | 书稿作者 / Agent |
| `src/` | 模板维护者 |
| `dist/` | 生成物 |

依赖：**chapters → component → lib/tokens**，禁止反向。

---

## 许可

MIT（见 `typst.toml`）。

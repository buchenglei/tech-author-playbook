# BUILD 加载卡

```bash
python3 writing-rules/tools/assemble_book.py books/<slug> \
  --engine techbook-typst --compile
```

默认生成书内 `books/<slug>/typst/`（`main.typ`、`config.toml`、`src/`、`chapters/chN.typ`、`assets/`），
产物在 `books/<slug>/typst/dist/book.pdf`；**不要写 `techbook-typst/chapters`**，那会覆盖样书。
排版故障才开 `techbook-typst/AGENTS.md`。勿把 PDF 提交进库。

## 交付打包

见 `DELIVER.md` / `templates/08_交付规范.md`：

```bash
python3 writing-rules/tools/package_book.py books/<slug> --engine techbook-typst
```

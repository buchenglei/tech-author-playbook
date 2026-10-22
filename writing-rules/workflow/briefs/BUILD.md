# BUILD 加载卡

```bash
python3 writing-rules/tools/assemble_book.py books/<slug> \
  --engine techbook-typst --out techbook-typst/chapters --compile
```

章节名 `chapters/chN.typ`。排版故障才开 `techbook-typst/AGENTS.md`。
产物只在 `dist/`；勿把 PDF 提交进库。

## 交付打包

见 `DELIVER.md` / `templates/08_交付规范.md`：

```bash
python3 writing-rules/tools/package_book.py books/<slug> --engine techbook-typst
```

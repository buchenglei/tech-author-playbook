# 交付卡（打包前检查）

- [ ] 读 `templates/08_交付规范.md`
- [ ] `run_gates.py` / 编译 PDF 通过
- [ ] `handoff/` 六文件齐全，`05_unverified` 非空
- [ ] 执行 `package_book.py` 生成 tar.gz
- [ ] 本地解压抽查：README、PDF、typst 可编译、manuscript、workflow
- [ ] 包内无 archive/日志/DS_Store/废弃章名

```bash
python3 writing-rules/tools/package_book.py books/<slug> \
  --engine techbook-typst --out dist/<slug>-delivery.tar.gz
```

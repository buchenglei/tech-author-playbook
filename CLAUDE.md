# CLAUDE.md

> 这个仓库同时是「写作规范」和「被维护的项目」。**先分流，再动手。**

- **用本库写一本书** → 读 [`README.md`](README.md) §3 路由表 → `writing-rules/workflow/WORKFLOW.md`
- **维护 / 修改本仓库** → 读 [`AGENTS.md`](AGENTS.md)（变更闭环与硬契约）
- **只用排版引擎** → 读 [`techbook-typst/AGENTS.md`](techbook-typst/AGENTS.md)

验证命令：

```bash
python3 writing-rules/tools/tests/run_tests.py
python3 writing-rules/tools/check_rule_coverage.py
python3 writing-rules/tools/run_gates.py books/how-to-write-a-tech-book
```

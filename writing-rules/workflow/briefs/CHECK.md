# CHECK 加载卡

```bash
python3 writing-rules/tools/run_gates.py books/<slug>          # 紧凑 G0–G8
python3 writing-rules/tools/spec_lint.py <file> --profile manuscript
python3 writing-rules/tools/quality_gate.py books/<slug>       # 章签字/报告/证据/代码
python3 writing-rules/tools/validate_quality.py books/<slug>   # G8 质量/体量/流程
python3 writing-rules/tools/tests/run_tests.py                 # 改工具后
```

首批未人签字不得进批量；**人签了字的批次才能 `frozen`**（签字写明改了什么/裁了什么，空签字无效）；报告必须有 `文件:行号 + 原句`；C# 片段必须能编译或标 `illustrative`；有意的形式偏离必须登记 `deviations.jsonl` 并在签收时裁决。

L1 证据自检按 `spec/08-校验.md` §7.5 表；L2 只列「未做」。禁止用「通常」混过事实检查。

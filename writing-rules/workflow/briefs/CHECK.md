# CHECK 加载卡

```bash
python3 writing-rules/tools/run_gates.py books/<slug>     # 紧凑 G0–G7
python3 writing-rules/tools/spec_lint.py <file> --profile manuscript
python3 writing-rules/tools/tests/run_tests.py            # 改工具后
```

L1 证据自检按 `spec/08-校验.md` §7.5 表；L2 只列「未做」。
禁止用「通常」混过事实检查。


```bash
python3 writing-rules/tools/validate_quality.py books/<slug>  # G8 质量/体量/流程
```

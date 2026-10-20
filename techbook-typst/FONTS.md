# 字体说明

模板按 `config.toml` 的 `[fonts]` 选择字体；缺字会回退并产生 `unknown font family` 警告。

## 默认字体栈

| 用途 | 默认回退链 | 说明 |
| --- | --- | --- |
| 正文/标题 | Microsoft YaHei → PingFang SC → Noto Sans SC | Windows 雅黑，Mac 苹方 |
| 代码 | Maple Mono NF → Maple Mono → Cascadia Code → Consolas | 推荐 Maple Mono |

可在文档的 `config.toml` 覆盖：

```toml
[fonts]
sans = ["Microsoft YaHei", "PingFang SC", "Noto Sans SC"]
mono = ["Maple Mono NF", "Maple Mono", "Cascadia Code"]
```

## 可选中文字体

| 字体 | 族名 | 气质 |
| --- | --- | --- |
| 微软雅黑 | Microsoft YaHei | 现代无衬线，Windows 默认 |
| 苹方 | PingFang SC | Mac 系统字 |
| 思源黑体 | Noto Sans SC / Source Han Sans CN | 开源、跨平台 |

## 字重

正文默认 `weight: 400`。标题用 700。

## 验证

```bash
nu build.nu doctor
```

`unknown font family` 是回退提示；`error` 才是失败。

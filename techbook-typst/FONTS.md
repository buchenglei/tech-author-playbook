# 字体说明

模板按 `config.toml` 的 `[fonts]` 选择字体；缺字会回退并产生 `unknown font family` 警告。

## 默认字体栈

| 用途 | 默认回退链 | 说明 |
| --- | --- | --- |
| 正文（衬线） | Noto Serif SC → Source Han Serif SC → Songti SC → STSong → SimSun | 书感正文 |
| 标题（黑体） | PingFang SC → Microsoft YaHei → Noto Sans SC → Heiti SC | 层级清晰 |
| 代码 | Maple Mono NF → Maple Mono → Cascadia Code → Consolas | 推荐 Maple Mono |

引擎对正文用 `serif`，标题 show 规则用 `sans`。覆盖：

```toml
[fonts]
serif = ["Noto Serif SC", "Source Han Serif SC", "SimSun"]
sans = ["PingFang SC", "Microsoft YaHei", "Noto Sans SC"]
mono = ["Maple Mono NF", "Cascadia Code", "Consolas"]
```

## 可选中文字体

| 字体 | 族名 | 气质 |
| --- | --- | --- |
| 宋体-简 / 华文宋体 | Songti SC / STSong | Mac 常见衬线 |
| 思源宋体 | Noto Serif SC / Source Han Serif SC | 开源书感 |
| 中易宋体 | SimSun | Windows 衬线 |
| 苹方 / 雅黑 / 思源黑体 | PingFang SC / Microsoft YaHei / Noto Sans SC | 标题与 UI |

## 字重与行距

正文 `weight: 400`，标题 700。默认 `leading ≈ 0.95em`、段距 `≈ 0.82em`、首行缩进 `2em`（`layout.indent` 可改）。

## 验证

```bash
nu build.nu doctor
```

`unknown font family` 是回退提示；`error` 才是失败。字体不齐时优先补「正文衬线」。

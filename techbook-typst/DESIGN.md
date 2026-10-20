# 设计说明

## 定位

**专业技术书籍** Typst 基础库：不是文档/教程模板。视觉与组件按「可出版的技术书」收敛。

## 核心决策

| 决策 | 原因 |
| --- | --- |
| TOML 配置驱动 | 书目与版式可审查、可 diff，章节不写样式 |
| 唯一入口 `main.typ` | 只装配 include，正文在 `chapters/` |
| B5（jis-b5）开本 | 中文技术书常见尺寸，屏读打印都合适 |
| 双面书眉 + 书口页码 | 偶数页书名、奇数页章名；页码在外侧 |
| 章首页「第 X 章」+ 章题 + 短线 | 成书节奏，区别于博客标题 |
| 图注 `N-M` / 附录 `A-M` | 增删节不手改编号；交叉引用只用 `@label` |
| 调用块纯文字标签 | 印刷向，无 emoji |
| `#preface` / `#appendix` | 前置与后置不占章号；附录切换图表字母编号 |
| state 注入令牌 | `let` 注入对子组件无效 |
| `goal/summary/exercises` 可选 | 书籍不必每章教程脚手架 |
| 单一 `code-frame` | 围栏、`#code-block`、`#listing` 同一视觉 |

## 分层

```text
config.toml → src/lib/tokens → src/theme / component / cover
                              ↑
                     main.typ + chapters
```

## 有意不做

- 与旧版 techdoc 的 API 兼容
- 教程风「目标—练习」强制结构
- 写作质量/文风门禁（另库负责）
- 索引/参考文献自动化（可后续扩展）

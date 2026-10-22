// =============================================================================
//  tests/smoke.typ —— 冒烟：配置注入 + 组件 + 附录编号
// =============================================================================

#import "../src/book.typ": *

#show: book.with(config: (
  doc: (
    title: "冒烟测试",
    authors: ("测试",),
    date: "2026-01-01",
  ),
  layout: (cover: false, toc: false, header: false),
))

= 测试章

#goal[验证组件与配置协同。]

#tip[提示]
#warning[注意]
#pit[避坑]
#best[要点]

#keypoint[要点]
#lead[段落引导]
#quote(attribution: "出处")[摘录内容]

#code[a] #path[b] #kbd[C] #hl[x] #term[术语]

#tbl(columns: (auto, auto), header: ("A", "B"), ("1", "2"), caption: "表")

#fig(
  rect(width: 20mm, height: 10mm, fill: rgb("#ddd")),
  caption: [图],
)

#steps(([一步], [说明]), ([二步], [说明]))

#listing("print(1)", lang: "python", title: [清单])

#summary[小结]
#exercises([题])

#appendix[附录测试]

附录正文，图注应使用 A-M 编号。

#tbl(columns: (auto, auto), header: ("X", "Y"), ("3", "4"), caption: [附录表])

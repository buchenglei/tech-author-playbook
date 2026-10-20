// =============================================================================
//  cover.typ —— 扉页 + 版权页
// -----------------------------------------------------------------------------
//  扉页：书名、副标题、作者、出版信息（印刷向，摘要与关键词归版权页）。
//  版权页：内容简介、作者、版次、关键词、版本记录。
// =============================================================================

#import "lib/utils.typ": author-text

/// 扉页
#let cover-page(ctx) = {
  let t = ctx.tokens
  let m = ctx.meta
  let title-size = t.size.cover-title

  page(
    margin: 0pt,
    header: none,
    footer: none,
    fill: gradient.linear(
      (rgb("#0b1f3a"), 0%),
      (rgb("#1e3a8a"), 55%),
      (rgb("#1e3a8a"), 100%),
      angle: 118deg,
    ),
  )[
    // 装饰：右下细圆环（克制，偏书刊）
    #place(bottom + right, dx: 22mm, dy: -18mm,
      circle(radius: 28mm, fill: none, stroke: 0.7pt + rgb("#93c5fd").transparentize(35%)))
    #place(bottom + right, dx: 42mm, dy: -40mm,
      circle(radius: 12mm, fill: rgb("#2563eb").transparentize(55%), stroke: none))

    #block(width: 100%, height: 100%)[
      #pad(x: 20mm, top: 18mm, bottom: 16mm)[
        #grid(
          rows: (auto, 1fr, auto),
          // ---- 顶栏 ----
          {
            grid(
              columns: (1fr, auto),
              align: (left + horizon, right + horizon),
              text(font: t.fonts.sans, size: 9.5pt, fill: rgb("#93c5fd"), tracking: 0.16em)[
                #if m.category != none [#m.category]
                #if m.category != none and m.org != none [#h(0.55em)·#h(0.55em)]
                #if m.org != none [#m.org]
              ],
              if m.version != none {
                box(
                  fill: rgb("#1e3a5f"),
                  radius: 2pt,
                  inset: (x: 7pt, y: 2.5pt),
                  text(font: t.fonts.sans, size: 8pt, fill: rgb("#bfdbfe"))[#m.version],
                )
              } else { [] },
            )
            v(4mm)
            line(length: 100%, stroke: 0.5pt + rgb("#3b82f6").transparentize(20%))
          },

          // ---- 中段：书名 ----
          {
            align(horizon)[
              #move(dy: -6mm)[
                #block(width: 92%)[
                  #set par(leading: 1.15em, justify: false)
                  #text(font: t.fonts.sans, size: title-size, weight: 700, fill: white)[#m.title]
                  #if m.subtitle != none [
                    #v(6mm)
                    #set par(leading: 1.4em)
                    #text(font: t.fonts.sans, size: t.size.cover-subtitle, fill: rgb("#dbeafe"))[—— #m.subtitle ——]
                  ]
                ]
              ]
            ]
          },

          // ---- 底栏 ----
          {
            line(length: 100%, stroke: 0.5pt + rgb("#3b82f6").transparentize(20%))
            v(4mm)
            grid(
              columns: (1fr, auto),
              align: (left + top, right + top),
              text(font: t.fonts.sans, size: 10pt, fill: white)[
                #author-text(m)
                #if m.team != none [#h(0.5em)｜#h(0.5em)#m.team]
              ],
              text(font: t.fonts.sans, size: 9pt, fill: rgb("#93c5fd"))[
                #if m.date != none [#m.date.cn]
              ],
            )
          },
        )
      ]
    ]
  ]
}

/// 版权页
#let colophon-page(ctx) = {
  let t = ctx.tokens
  let m = ctx.meta
  let title-line = if m.subtitle != none {
    [#m.title / #m.subtitle]
  } else {
    [#m.title]
  }
  page(header: none)[
    #text(font: t.fonts.sans, size: t.size.h2, weight: 700)[版权信息]
    #v(t.space.xs)
    #line(length: 100%, stroke: t.stroke.thin + t.rule-strong)
    #v(t.space.md)
    #if m.abstract != none [
      #text(font: t.fonts.sans, size: t.size.small, weight: 700, fill: t.ink-weak)[内容简介]
      #v(t.space.xs)
      #block(inset: (right: 6mm), par(leading: 1.55em)[
        #text(size: t.size.base, fill: t.ink-weak)[#m.abstract]
      ])
      #v(t.space.lg)
    ]
    #set text(size: t.size.small)
    #grid(
      columns: (22mm, 1fr),
      row-gutter: t.space.xs,
      text(fill: t.ink-mute)[书名], title-line,
      text(fill: t.ink-mute)[作者], text[#author-text(m)],
      ..if m.team != none { (text(fill: t.ink-mute)[团队], text[#m.team]) } else { () },
      ..if m.org != none { (text(fill: t.ink-mute)[组织], text[#m.org]) } else { () },
      text(fill: t.ink-mute)[版本], text[#if m.version != none [#m.version]],
      text(fill: t.ink-mute)[日期], text[#if m.date != none [#m.date.cn]],
      ..if m.keywords.len() > 0 {
        (text(fill: t.ink-mute)[关键词], text[#m.keywords.join(" · ")])
      } else { () },
    )
    #if m.history.len() > 0 [
      #v(t.space.xl)
      #text(font: t.fonts.sans, size: t.size.h3, weight: 700, fill: t.ink)[版本记录]
      #v(t.space.xs)
      #table(
        columns: (16mm, 24mm, 1fr, 20mm),
        inset: (x: t.space.xs, y: t.space.xxs),
        stroke: 0.4pt + t.rule,
        fill: (_, y) => if y == 0 { t.surface-alt } else { t.paper },
        text(weight: 700)[版本], text(weight: 700)[日期], text(weight: 700)[说明], text(weight: 700)[作者],
        ..m.history.map(h => (
          text(weight: 600)[#h.version],
          text(fill: t.ink-weak)[#h.date],
          text(fill: t.ink-weak)[#h.note],
          text(fill: t.ink-mute)[#if h.author != none { h.author }],
        )).flatten(),
      )
    ]
  ]
}

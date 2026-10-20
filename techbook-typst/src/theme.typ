// =============================================================================
//  theme.typ —— 专业技术书籍版式引擎
// -----------------------------------------------------------------------------
//  唯一入口：#show: book.with(config: toml("config.toml"))
//  B5 成书：书眉双面、书口页码、章首页、图表 N-M、印刷向目录。
// =============================================================================

#import "lib/tokens.typ": build-tokens, build-meta
#import "lib/utils.typ": to-cn
#import "component.typ": bind as component-bind, wrap-raw, appendix-state
#import "cover.typ": cover-page, colophon-page

#let num-fmt = numbering

#let chapter-label(n) = "第" + to-cn(n) + "章"

#let appendix-letter(n) = {
  if n <= 0 { return "A" }
  if n <= 26 { str.from-unicode(64 + n) } else { str(n) }
}

#let book(
  /// config.toml 解析后的字典
  config: none,
  /// 或直接传已构建的 meta（高级用法）
  meta: none,
  doc,
) = {
  if config == none and meta == none {
    panic("book: 请传入 config: toml(\"config.toml\")")
  }
  let cfg = if config == none { (:) } else { config }
  let t = build-tokens(cfg)
  let m = if meta != none { meta } else { build-meta(cfg) }
  let layout = cfg.at("layout", default: (:))

  let ctx = (
    tokens: t,
    meta: m,
    toc: layout.at("toc", default: true),
    toc-depth: layout.at("toc-depth", default: 2),
    header: layout.at("header", default: true),
    indent: {
      let ind = layout.at("indent", default: "0em")
      if type(ind) == str {
        if ind == "0" or ind == "0pt" or ind == "0em" { 0pt }
        else if ind.ends-with("em") { float(ind.slice(0, -2)) * 1em }
        else if ind.ends-with("pt") { float(ind.slice(0, -2)) * 1pt }
        else { 0pt }
      } else { ind }
    },
    cover: layout.at("cover", default: true),
  )

  show: component-bind.with(ctx)

  set document(
    title: m.title,
    author: m.author,
    keywords: m.keywords,
    description: if m.abstract != none { m.abstract } else if m.subtitle != none { m.subtitle } else { none },
    date: if m.date != none {
      datetime(year: m.date.year, month: int(m.date.iso.slice(5, 7)), day: int(m.date.iso.slice(8, 10)))
    } else { none },
  )

  // ---- 全局排版 ------------------------------------------------------------
  set text(
    font: t.fonts.sans,
    size: t.size.base,
    weight: 400,
    fill: t.ink,
    lang: "zh",
    region: "cn",
    hyphenate: false,
    cjk-latin-spacing: auto,
  )
  set par(
    justify: true,
    leading: t.rhythm.leading,
    spacing: t.rhythm.par-spacing,
    first-line-indent: (amount: ctx.indent, all: true),
    linebreaks: "optimized",
  )

  // ---- 页面：B5 书版、双面书眉、书口页码 -----------------------------------
  set page(
    paper: t.geometry.paper,
    margin: t.geometry.margin,
    binding: t.geometry.binding,
    fill: t.paper,
    footer-descent: t.geometry.footer-gap,
    header-ascent: t.geometry.header-gap,
    header: if not ctx.header { none } else {
      context {
        let pg = here().page()
        let chapter-start = query(heading.where(level: 1))
          .any(h => h.location().page() == pg)
        if chapter-start {
          none
        } else {
          let hs = query(heading.where(level: 1))
            .filter(h => h.location().page() <= pg)
          let name = if hs.len() > 0 { hs.last().body } else { m.title }
          block(width: 100%)[
            #if calc.even(pg) {
              align(left, text(
                font: t.fonts.sans, size: t.size.tiny, fill: t.ink-mute, tracking: 0.04em,
              )[#m.title])
            } else {
              align(right, text(
                font: t.fonts.sans, size: t.size.tiny, fill: t.ink-mute, tracking: 0.04em,
              )[#name])
            }
            #v(t.space.xxxs)
            #line(length: 100%, stroke: t.stroke.hair + t.rule)
          ]
        }
      }
    },
    footer: context {
      let pg = counter(page).display()
      let mark = text(
        font: t.fonts.sans, size: t.size.small, fill: t.ink-mute,
      )[#pg]
      // 书口侧页码：偶数页在左（外），奇数页在右（外）
      if calc.even(here().page()) {
        align(left, mark)
      } else {
        align(right, mark)
      }
    },
  )

  // ---- 代码 ----------------------------------------------------------------
  set raw(theme: t.code-theme)
  show raw.where(block: true): it => wrap-raw(it)
  show raw.where(block: false): it => context {
    let t2 = ctx.tokens
    if not t2.code-inline-wrap {
      return text(font: t2.fonts.mono, size: t2.size.small - 0.2pt, fill: rgb("#24292f"), it.text)
    }
    let z = "\u{200B}"
    let s = it.text
    s = s.replace(regex("([./_\\-])"), m => m.text + z)
    s = s.replace(regex("([a-z0-9])([A-Z])"), m => m.text.slice(0, 1) + z + m.text.slice(1))
    s = s.replace(regex("([0-9])([A-Za-z])"), m => m.text.slice(0, 1) + z + m.text.slice(1))
    s = s.replace(regex("([A-Za-z])([0-9])"), m => m.text.slice(0, 1) + z + m.text.slice(1))
    text(font: t2.fonts.mono, size: t2.size.small - 0.2pt, fill: rgb("#24292f"), s)
  }

  // ---- 标题编号：章 1 / 节 1.1 / 小节 1.1.1 -------------------------------
  set heading(numbering: (..n) => num-fmt("1.1.1", ..n.pos()))
  set figure(gap: t.space.xs)
  set footnote(numbering: "*")
  set list(
    indent: t.rhythm.list-indent,
    body-indent: t.rhythm.list-body-indent,
    marker: text(fill: t.ink-mute, [•]),
    spacing: 0.35em,
    tight: true,
  )
  set enum(
    indent: t.rhythm.list-indent,
    body-indent: t.rhythm.list-body-indent,
    numbering: n => text(fill: t.ink, weight: 600)[#n.],
    spacing: 0.32em,
    tight: true,
  )
  show list: it => block(above: t.space.md, below: t.space.md, it)
  show enum: it => block(above: t.space.md, below: t.space.md, it)

  // ---- 图注：图/表/清单 ---------------------------------------------------
  show figure.caption: it => block(
    above: t.space.xs,
    below: t.space.xs,
    width: 100%,
  )[
    #set par(first-line-indent: 0pt, justify: false)
    #set text(font: t.fonts.sans, size: t.size.small, fill: t.ink-mute)
    #let body = [#it.supplement #context it.counter.display(it.numbering)#h(0.55em)#it.body]
    #if it.kind == "raw" or it.position == top {
      align(center)[#text(fill: t.ink-weak)[#body]]
    } else {
      align(left)[
        #text(weight: 600, fill: t.ink-weak)[#it.supplement #context it.counter.display(it.numbering)]
        #h(0.55em)#it.body
      ]
    }
  ]

  // 图表编号：正文 N-M，附录 A-M
  set figure(numbering: (..nums) => context {
    if appendix-state.get() {
      let an = counter("techbook-appendix").get().at(0, default: 1)
      let letter = appendix-letter(an)
      let last = if nums.pos().len() > 0 { str(nums.pos().last()) } else { "1" }
      letter + "-" + last
    } else {
      num-fmt("1-1", counter(heading).get().first(), ..nums.pos())
    }
  })
  set math.equation(
    numbering: n => context {
      if appendix-state.get() {
        let an = counter("techbook-appendix").get().at(0, default: 1)
        "(" + appendix-letter(an) + "-" + str(n) + ")"
      } else {
        num-fmt("(1-1)", counter(heading).get().first(), n)
      }
    },
    supplement: [式],
  )

  // ---- 章首页 -------------------------------------------------------------
  show heading.where(level: 1): it => {
    // 按章重置图表/公式计数
    counter(figure.where(kind: "fig")).update(0)
    counter(figure.where(kind: "tbl")).update(0)
    counter(figure.where(kind: "raw")).update(0)
    counter(math.equation).update(0)
    context {
      let numbered = it.numbering != none
      let n = counter(heading).get().first()
      block(above: t.space.md, below: t.space.lg, width: 100%)[
        #set text(font: t.fonts.sans)
        #set par(first-line-indent: 0pt, justify: false)
        #if numbered [
          #text(size: t.size.h1 - 5pt, weight: 700, fill: t.accent)[#chapter-label(n)]
          #v(t.space.sm)
          #text(size: t.size.h1, weight: 700, fill: t.ink)[#it.body]
        ] else [
          #text(size: t.size.h1, weight: 700, fill: t.ink)[#it.body]
        ]
        #v(t.space.sm)
        #line(length: 38%, stroke: t.stroke.thick + t.accent)
      ]
    }
  }

  show heading.where(level: 2): it => {
    context {
      let nums = counter(heading).get()
      let numbered = it.numbering != none
      let num-label = if numbered { num-fmt("1.1", ..nums) + h(0.45em) } else { none }
      block(above: t.space.xl, below: t.space.md, width: 100%)[
        #set text(font: t.fonts.sans)
        #set par(first-line-indent: 0pt)
        #grid(
          columns: (auto, 1fr),
          column-gutter: t.space.xs,
          align: horizon,
          rect(width: 3.2pt, height: 0.95em, fill: t.accent, radius: 0.5pt),
          text(size: t.size.h2, weight: 700, fill: t.ink)[#num-label#it.body],
        )
      ]
    }
  }

  show heading.where(level: 3): it => {
    context {
      let nums = counter(heading).get()
      let numbered = it.numbering != none
      let num-label = if numbered { num-fmt("1.1.1", ..nums) + h(0.4em) } else { none }
      block(above: t.space.lg, below: t.space.sm, width: 100%)[
        #set text(font: t.fonts.sans)
        #set par(first-line-indent: 0pt)
        #text(size: t.size.h3, weight: 700, fill: t.ink)[#num-label#it.body]
      ]
    }
  }

  show heading.where(level: 4): it => {
    block(above: t.space.md, below: t.space.xs, width: 100%)[
      #set text(font: t.fonts.sans)
      #set par(first-line-indent: 0pt)
      #text(size: t.size.h4, weight: 700, fill: t.ink-weak)[#it.body]
    ]
  }

  // ---- 前置页：扉页 → 版权页 → 目录 → 正文 --------------------------------
  if ctx.cover {
    cover-page(ctx)
    colophon-page(ctx)
  }

  if ctx.toc {
    context {
      let entries = query(heading.where(level: 1, outlined: true))
      if entries.len() > 0 {
        page(header: none)[
          #text(font: t.fonts.sans, size: t.size.h1 - 3pt, weight: 700, fill: t.ink)[目录]
          #v(t.space.xs)
          #line(length: 100%, stroke: t.stroke.thick + t.accent)
          #v(t.space.md)
          #set par(first-line-indent: 0pt, justify: false)
          #{
            let depth = ctx.toc-depth
            show outline.entry.where(level: 1): it => {
              let numbered = it.element.numbering != none
              link(it.element.location())[
                #set par(leading: 1.55em)
                #grid(
                  columns: (auto, 1fr, auto),
                  column-gutter: 6pt,
                  align: (left, bottom, right),
                  text(font: t.fonts.sans, size: t.size.base, weight: 600, fill: t.ink)[
                    #if numbered {
                      context {
                        let n = counter(heading).at(it.element.location()).first()
                        chapter-label(n)
                        h(0.6em)
                        it.body()
                      }
                    } else {
                      it.body()
                    }
                  ],
                  box(width: 1fr, align(bottom)[#repeat(gap: 3.5pt)[.]]),
                  text(font: t.fonts.sans, size: t.size.base - 0.5pt, fill: t.ink-mute)[#it.page()],
                )
              ]
            }
            show outline.entry.where(level: 2): it => {
              link(it.element.location())[
                #set par(leading: 1.45em)
                #grid(
                  columns: (1.2em, auto, 1fr, auto),
                  column-gutter: 6pt,
                  align: (left, left, bottom, right),
                  [],
                  text(font: t.fonts.sans, size: t.size.small, fill: t.ink-weak)[
                    #context {
                      if it.element.numbering != none {
                        numbering("1.1", ..counter(heading).at(it.element.location()))
                        h(0.35em)
                      }
                      it.body()
                    }
                  ],
                  box(width: 1fr, align(bottom)[#repeat(gap: 3.5pt)[.]]),
                  text(font: t.fonts.sans, size: t.size.small, fill: t.ink-mute)[#it.page()],
                )
              ]
            }
            show outline.entry.where(level: 3): it => if depth >= 3 {
              link(it.element.location())[
                #set par(leading: 1.4em)
                #grid(
                  columns: (2.4em, auto, 1fr, auto),
                  column-gutter: 6pt,
                  align: (left, left, bottom, right),
                  [],
                  text(font: t.fonts.sans, size: t.size.small, fill: t.ink-mute)[
                    #context {
                      if it.element.numbering != none {
                        numbering("1.1.1", ..counter(heading).at(it.element.location()))
                        h(0.35em)
                      }
                      it.body()
                    }
                  ],
                  box(width: 1fr, align(bottom)[#repeat(gap: 3.5pt)[.]]),
                  text(font: t.fonts.sans, size: t.size.small, fill: t.ink-mute)[#it.page()],
                )
              ]
            } else { none }
            outline(title: none, depth: depth, indent: 0pt, target: heading)
          }
        ]
      }
    }
  }

  doc
}

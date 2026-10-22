// =============================================================================
//  toc.typ —— 目录页（点导线 + 章号）
// =============================================================================
#import "lib/tokens.typ": build-tokens
#import "lib/utils.typ": to-cn

#let chapter-label(n) = "第" + to-cn(n) + "章"

#let toc-page(ctx) = {
  let t = ctx.tokens
  let depth = ctx.toc-depth
  context {
    let entries = query(heading.where(level: 1, outlined: true))
    if entries.len() > 0 {
      page(header: none)[
        #set par(first-line-indent: 0pt, justify: false)
        #text(font: t.fonts.sans, size: t.size.h1 - 3pt, weight: 700, fill: t.ink)[目录]
        #v(t.space.xs)
        #line(length: 100%, stroke: t.stroke.thick + t.accent)
        #v(t.space.md)
        #set par(first-line-indent: 0pt, justify: false)
        #{
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

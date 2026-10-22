#import "lib/tokens.typ": build-tokens

// =============================================================================
//  component.typ —— 书籍语义组件
// -----------------------------------------------------------------------------
//  章节只调用语义组件，不写死颜色字号。配置经 state 注入。
// =============================================================================

#let default-ctx = (tokens: build-tokens((:)))
#let ctx-state = state("techbook-ctx", default-ctx)

/// 附录模式：图/表/清单改用 A-1 编号
#let appendix-state = state("techbook-appendix", false)

#let bind(new-ctx, body) = {
  ctx-state.update(_ => new-ctx)
  body
}

#let get-tokens() = ctx-state.get().tokens

// -----------------------------------------------------------------------------
//  代码框：唯一实现，code-block / wrap-raw / listing 共用
// -----------------------------------------------------------------------------

/// 出版物式代码块：灰底、行号、右上角语言标签
#let code-frame(
  code-text,
  lang: "text",
  file: none,
  lines: auto,
) = context {
  let t = get-tokens()
  let lines = if lines == auto { t.code-show-lines } else { lines }
  let mono-font = t.fonts.mono
  let code = if type(code-text) == str { code-text } else { str(code-text) }
  let lang-str = if lang == none { "text" } else { str(lang) }
  let rows = code.trim("\n").split("\n")
  let nlines = rows.len()
  let show-lines = lines and nlines > 1
  let code-size = t.size.small + 0.1pt
  let gutter-w = str(nlines).len() * 0.62em + 0.9em
  let bg = t.code-bg
  let gutter-fg = t.code-gutter
  let show-lang = t.code-show-lang and lang-str != "text"
  let inset-x = t.code-inset-x

  // 与正文同宽；轻量：浅底 + 上下细线，去掉厚重外框
  block(width: t.code-width, above: t.space.md, below: t.space.md, breakable: true)[
    #line(length: 100%, stroke: t.stroke.hair + t.code-rule)
    #block(width: 100%, fill: bg, inset: (left: inset-x, right: inset-x, top: t.space.sm, bottom: t.space.sm))[
      #if show-lang [
        #place(top + right,
          text(font: t.fonts.sans, size: t.size.tiny, fill: t.code-gutter, tracking: 0.04em)[#lang-str])
      ]
      #align(left)[
        #set par(leading: 0.78em, spacing: 0em, justify: false, first-line-indent: 0pt)
        #if file != none [
          #text(font: t.fonts.sans, size: t.size.tiny, fill: t.ink-mute)[#file]
          #v(t.space.xs)
        ]
        // 逐行渲染：不创建 block 级 raw，避免 show raw 递归 / 双重行号
        #for (i, ln) in rows.enumerate() {
          if show-lines {
            box(width: gutter-w)[
              #set text(font: mono-font, size: code-size, fill: gutter-fg)
              #align(right, str(i + 1))
            ]
            h(t.space.xs)
          }
          raw(ln, lang: lang-str, block: false)
          if i < nlines - 1 { linebreak() }
        }
      ]
    ]
    #line(length: 100%, stroke: t.stroke.hair + t.code-rule)
  ]
}

/// 裸 ``` 围栏 → code-frame（theme 的 show raw 调用）
#let wrap-raw(it, file: none, lines: auto) = {
  code-frame(
    if it.has("text") { it.text } else { str(it) },
    lang: if it.has("lang") and it.lang != none { it.lang } else { "text" },
    file: file,
    lines: lines,
  )
}

/// 代码块 API
#let code-block(code, lang: "text", file: none, lines: auto) = {
  let (text, lang) = if type(code) == str {
    (code, lang)
  } else {
    let r = code
    (
      if r.has("text") { r.text } else { str(r) },
      if r.has("lang") and r.lang != none { r.lang } else { lang },
    )
  }
  code-frame(text, lang: lang, file: file, lines: lines)
}

/// 带题注的代码清单（清单 N-M）
#let listing(code, title: none, lang: "text", file: none, lines: auto) = {
  let body = context {
    code-block(code, lang: lang, file: file, lines: lines)
  }
  figure(
    body,
    kind: "raw",
    supplement: [清单],
    caption: title,
    gap: 10pt,
  )
}

// -----------------------------------------------------------------------------
//  提示块：印刷向纯文字标签
// -----------------------------------------------------------------------------

#let callout(kind: "tip", title: none, ..body) = {
  let parts = body.pos()
  if parts.len() == 0 { panic("callout: 缺少正文") }
  let body = parts.last()
  context {
    let t = get-tokens()
    let sem = t.callouts.at(kind, default: t.callouts.tip)
    let shown = if title != none { title } else { sem.label }
    block(width: 100%, above: t.space.md, below: t.space.md, breakable: true)[
      #block(
        width: 100%,
        fill: rgb(sem.bg),
        stroke: (left: t.stroke.bar + rgb(sem.bar)),
        inset: (left: t.space.md, right: t.space.md, y: t.space.sm),
        radius: (right: t.radius.md),
      )[
        #set par(first-line-indent: 0pt, spacing: t.space.xxs, leading: 0.88em)
        #set text(size: t.size.base - 0.2pt)
        #text(font: t.fonts.sans, weight: 700, fill: rgb(sem.fg))[
          #shown#h(0.55em)
        ]#body
      ]
    ]
  }
}

#let tip(..body) = callout(kind: "tip", ..body)
#let warning(..body) = callout(kind: "warning", ..body)
#let pit(..body) = callout(kind: "pit", ..body)
#let best(..body) = callout(kind: "best", ..body)

// -----------------------------------------------------------------------------
//  要点 / 段落引导 / 摘录
// -----------------------------------------------------------------------------

#let keypoint(title: "要点", ..body) = {
  let parts = body.pos()
  if parts.len() == 0 { panic("keypoint: 缺少正文") }
  let body = parts.last()
  context {
    let t = get-tokens()
    block(width: 100%, above: t.space.md, below: t.space.md)[
      #block(
        width: 100%,
        fill: t.accent-wash,
        stroke: (left: t.stroke.bar + t.accent),
        inset: (left: t.space.md, right: t.space.md, y: t.space.sm),
        radius: (right: t.radius.md),
      )[
        #set par(first-line-indent: 0pt, spacing: t.space.xxs)
        #text(font: t.fonts.sans, weight: 700, fill: t.accent-ink, size: t.size.small)[#title#h(0.45em)]
        #text(size: t.size.base)[#body]
      ]
    ]
  }
}

/// 段落小标题（不进目录）
#let lead(body) = context {
  let t = get-tokens()
  block(above: t.space.lg, below: t.space.sm, width: 100%)[
    #set par(first-line-indent: 0pt, spacing: 0pt)
    #text(font: t.fonts.sans, weight: 700, size: t.size.base + 0.5pt, fill: t.ink)[#body]
  ]
}

/// 引用/摘录：左色条，可带出处或小标题
/// 用法：#quote[正文] 或 #quote(attribution: "来源", title: "小标题")[正文]
#let quote(attribution: none, title: none, ..body) = {
  let parts = body.pos()
  if parts.len() == 0 { panic("quote: 缺少正文") }
  let body = parts.last()
  context {
    let t = get-tokens()
    block(width: 100%, above: t.space.md, below: t.space.md)[
      #block(
        width: 100%,
        fill: t.surface,
        stroke: (left: t.stroke.thin + t.accent),
        inset: (left: t.space.md, right: t.space.md, y: t.space.sm),
        radius: (right: t.radius.sm),
      )[
        #set par(first-line-indent: 0pt, spacing: t.space.xxs)
        #if title != none [
          #text(font: t.fonts.sans, size: t.size.small, weight: 700, fill: t.ink-weak)[#title]
          #v(t.space.xxs)
        ]
        #text(fill: t.ink-weak, body)
        #if attribution != none [
          #v(t.space.xs)
          #align(right, text(size: t.size.small, fill: t.ink-mute)[—— #attribution])
        ]
      ]
    ]
  }
}

// -----------------------------------------------------------------------------
//  章末结构（可选脚手架）
// -----------------------------------------------------------------------------

/// 本章目标（可选）
#let goal(body) = keypoint(title: "本章目标", body)

/// 本章小结（可选，不强制每章）
#let summary(body) = {
  context {
    let t = get-tokens()
    block(above: t.space.xl, below: t.space.md, width: 100%)[
      #line(length: 100%, stroke: t.stroke.thin + t.rule)
      #v(t.space.sm)
      #grid(
        columns: (auto, 1fr),
        column-gutter: t.space.md,
        align: (left + top, left + top),
        text(font: t.fonts.sans, size: t.size.small, weight: 700, fill: t.accent)[本章小结],
        block[
          #set par(first-line-indent: 0pt, spacing: t.space.xs)
          #text(size: t.size.base - 0.2pt)[#body]
        ],
      )
    ]
    pagebreak(weak: true)
  }
}

/// 章末练习（可选）
#let exercises(..items) = {
  let pos = items.pos()
  if pos.len() == 0 { panic("exercises: 至少一题") }
  context {
    let t = get-tokens()
    let list = enum(
      numbering: n => text(font: t.fonts.sans, size: t.size.small, weight: 700, fill: t.accent)[#n.],
      indent: 0.8em,
      body-indent: 0.5em,
      ..pos,
    )
    block(above: t.space.lg, below: t.space.md, width: 100%)[
      #grid(
        columns: (auto, 1fr),
        column-gutter: t.space.md,
        align: (left + top, left + top),
        text(font: t.fonts.sans, size: t.size.small, weight: 700, fill: t.accent)[练习],
        list,
      )
    ]
    pagebreak(weak: true)
  }
}

// -----------------------------------------------------------------------------
//  前置 / 附录
// -----------------------------------------------------------------------------

/// 不编号的一级标题（前言、序、致谢等）
/// 自动抵消标题计数，保证正文第一章仍是「第一章」
#let preface(title: "前言", body) = {
  pagebreak(weak: true)
  heading(level: 1, numbering: none, outlined: true)[#title]
  counter(heading).update(n => {
    if type(n) == int {
      calc.max(0, n - 1)
    } else if type(n) == array and n.len() > 0 {
      n.slice(0, n.len() - 1) + (calc.max(0, n.at(-1) - 1),)
    } else {
      n
    }
  })
  body
  pagebreak(weak: true)
}

/// 附录起始：附录 A / B / C …，图注改用 A-1
#let appendix(title) = {
  pagebreak(weak: true)
  context {
    let t = get-tokens()
    let n = counter("techbook-appendix").get().at(0, default: 0) + 1
    counter("techbook-appendix").step()
    appendix-state.update(_ => true)
    counter(figure.where(kind: "fig")).update(0)
    counter(figure.where(kind: "tbl")).update(0)
    counter(figure.where(kind: "raw")).update(0)
    let letter = if n <= 26 { str.from-unicode(64 + n) } else { str(n) }
    heading(level: 1, numbering: none, outlined: true)[
      #text(fill: t.accent, weight: 700)[附录#h(0.45em)#letter]#h(0.6em)#title
    ]
  }
}

// -----------------------------------------------------------------------------
//  表 / 图
// -----------------------------------------------------------------------------

#let tbl(
  columns: auto,
  header: (),
  ..rows,
  caption: none,
  align: left,
) = {
  if columns == auto { panic("tbl: 必须传 columns") }
  let body = context {
    let t = get-tokens()
    let header-cells = header.map(h => text(font: t.fonts.sans, size: t.size.small, weight: 700, fill: t.ink)[#h])
    let body-cells = rows.pos().map(r => r.map(c => text(font: t.fonts.sans, size: t.size.small, fill: t.ink)[#c]))
    let n = 1 + body-cells.len()
    // 三线表：顶线、表头下线、底线，更像书
    table(
      columns: columns,
      align: align,
      inset: (x: t.space.sm, y: t.space.xs + 1pt),
      stroke: none,
      table.hline(y: 0, stroke: t.stroke.rule + t.ink-weak),
      table.hline(y: 1, stroke: t.stroke.hair + t.rule-strong),
      table.hline(y: n, stroke: t.stroke.rule + t.ink-weak),
      ..header-cells,
      ..body-cells.flatten(),
    )
  }
  figure(
    body,
    caption: caption,
    kind: "tbl",
    supplement: [表],
  )
}

#let fig(body, caption: none) = {
  figure(body, caption: caption, kind: "fig", supplement: [图])
}

// -----------------------------------------------------------------------------
//  步骤
// -----------------------------------------------------------------------------

#let steps(..items) = {
  let items = items.pos()
  if items.len() == 0 { panic("steps: 至少一步") }
  context {
    let t = get-tokens()
    block(above: t.space.md, below: t.space.md, width: 100%)[
      #for (i, item) in items.enumerate() {
        let (title, body) = if type(item) == array { (item.at(0), item.at(1)) } else { (none, item) }
        let is-last = i == items.len() - 1
        block(breakable: false, width: 100%)[
          #grid(
            columns: (1.5em, 1fr),
            column-gutter: t.space.sm,
            align: (left + top, left + top),
            block(width: 1.5em, height: 1.4em)[
              #if not is-last {
                place(top + center, dy: 1.3em, rect(width: 0.6pt, height: t.space.sm + 0.55em, fill: t.rule))
              }
              #box(
                width: 1.35em,
                height: 1.35em,
                radius: 50%,
                fill: if is-last { t.accent } else { t.accent-soft },
                align(center + horizon, text(
                  font: t.fonts.sans, size: t.size.tiny, weight: 700,
                  fill: if is-last { t.paper } else { t.accent-ink },
                  box(str(i + 1)),
                )),
              )
            ],
            block(above: 0.15em, below: if is-last { 0pt } else { t.space.sm })[
              #set par(first-line-indent: 0pt, spacing: t.space.xxs, leading: 0.85em)
              #if title != none [
                #text(font: t.fonts.sans, weight: 700)[#title]
                #v(t.space.xxxs)
              ]
              #body
            ],
          )
        ]
      }
    ]
  }
}

// -----------------------------------------------------------------------------
//  行内
// -----------------------------------------------------------------------------

#let hl(body) = context {
  let t = get-tokens()
  box(
    fill: t.accent-soft, radius: 1.5pt, inset: (x: 2.5pt, y: 0.6pt),
    baseline: 0.05em, text(fill: t.accent-ink, weight: 600)[#body],
  )
}

#let kbd(key) = context {
  let t = get-tokens()
  box(
    inset: (x: 3pt, y: 1pt), radius: 3pt,
    stroke: 0.5pt + rgb("#d0d7de"), fill: rgb("#f6f8fa"), baseline: 0.08em,
    text(font: t.fonts.mono, size: t.size.small - 0.5pt, fill: rgb("#24292f"))[#key],
  )
}

#let path(p) = context {
  let t = get-tokens()
  box(
    fill: rgb("#eff1f3"), radius: 3pt, inset: (x: 3.5pt, y: 0.8pt), baseline: 0.05em,
    text(font: t.fonts.mono, size: t.size.small - 0.2pt, fill: rgb("#24292f"))[#p],
  )
}

/// 行内代码/命令
#let code(p) = path(p)

#let term(word) = context {
  let t = get-tokens()
  underline(stroke: 0.6pt + t.accent, offset: 0.18em, text(weight: 600)[#word])
}

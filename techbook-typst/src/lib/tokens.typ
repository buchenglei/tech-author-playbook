// =============================================================================
//  lib/tokens.typ —— 成书默认令牌 + TOML 合并
// -----------------------------------------------------------------------------
//  使用者只改 config.toml；本文件提供默认值与解析逻辑，勿在业务文档里改。
//  定位：专业技术书籍（B5 开本、书眉、图注 N-M、印刷向组件）。
// =============================================================================

// ---- 配色（成书唯一预设，可被 [color] 覆盖）--------------------------------

#let book-colors = (
  accent: "#1e3a8a",
  accent-ink: "#1e3a8a",
  accent-soft: "#e8eef8",
  accent-wash: "#f4f7fb",
  ink: "#111827",
  ink-weak: "#374151",
  ink-mute: "#6b7280",
  rule: "#d1d5db",
  rule-strong: "#9ca3af",
  surface: "#f7f8fa",
  surface-alt: "#eef1f5",
  paper: "#ffffff",
  code-fg: "#24292f",
)

// 提示块四型：印刷向纯文字标签，无图标
#let callout-kinds = (
  tip: (label: "提示", bar: "#1e3a8a", bg: "#eef2ff", fg: "#1e3a8a"),
  warning: (label: "注意", bar: "#b45309", bg: "#fffbeb", fg: "#92400e"),
  pit: (label: "避坑", bar: "#b91c1c", bg: "#fef2f2", fg: "#991b1b"),
  best: (label: "最佳实践", bar: "#047857", bg: "#ecfdf5", fg: "#065f46"),
)

// ---- 几何 / 节奏（B5 成书）--------------------------------------------------

#let geometry = (
  paper: "jis-b5",
  margin: (inside: 24mm, outside: 20mm, top: 22mm, bottom: 24mm),
  header-gap: 10mm,
  footer-gap: 12mm,
  binding: left,
)

#let type-scale = (
  base: 10.5pt,
  small: 9pt,
  tiny: 8pt,
  h1: 24pt,
  h2: 15pt,
  h3: 12.5pt,
  h4: 11pt,
  cover-title: 32pt,
  cover-subtitle: 13pt,
)

#let rhythm = (
  leading: 0.82em,
  par-spacing: 0.72em,
  list-indent: 1.5em,
  list-body-indent: 0.55em,
)

#let space = (
  xxxs: 1.5pt,
  xxs: 3pt,
  xs: 5pt,
  sm: 8pt,
  md: 12pt,
  lg: 18pt,
  xl: 26pt,
  xxl: 36pt,
)

#let stroke = (
  hair: 0.4pt,
  thin: 0.6pt,
  rule: 0.8pt,
  thick: 2.2pt,
  bar: 3pt,
)

#let radius = (sm: 2pt, md: 3pt)

// ---- 字体默认 ---------------------------------------------------------------

#let default-fonts = (
  sans: ("Microsoft YaHei", "PingFang SC", "Noto Sans SC"),
  mono: ("Maple Mono NF", "Maple Mono", "Cascadia Code", "Consolas"),
)

// ---- 工具 -------------------------------------------------------------------

#let as-color(x) = if type(x) == str { rgb(x) } else { x }

#let parse-length(x, fallback: 0pt) = {
  if x == none { fallback }
  else if type(x) == length { x }
  else if type(x) == str {
    let s = x.trim()
    if s.ends-with("pt") { float(s.slice(0, -2)) * 1pt }
    else if s.ends-with("em") { float(s.slice(0, -2)) * 1em }
    else if s.ends-with("mm") { float(s.slice(0, -2)) * 1mm }
    else if s.ends-with("%") { float(s.slice(0, -1)) * 1% }
    else { float(s) * 1pt }
  } else if type(x) == float or type(x) == int { x * 1pt }
  else { fallback }
}

/// 宽松解析日期：datetime / "2026-10-17" / "2026/10" / none
#let parse-date(d) = {
  if d == none or d == auto { return none }
  if type(d) == datetime {
    let pad(n) = if n < 10 { "0" + str(n) } else { str(n) }
    let month = if d.month() != none { pad(d.month()) } else { "01" }
    let day = if d.day() != none { pad(d.day()) } else { "01" }
    return (
      iso: str(d.year()) + "-" + month + "-" + day,
      cn: str(d.year()) + " 年 " + str(d.month()) + " 月" + (
        if d.day() != none { " " + str(d.day()) + " 日" } else { "" }
      ),
      year: d.year(),
    )
  }
  let s = str(d).trim().replace("/", "-")
  let parts = s.split("-").filter(p => p != "")
  let year = int(parts.at(0, default: "0"))
  if year == none or year < 1970 {
    panic("config: 无法解析日期 " + repr(d) + "，期望 YYYY-MM-DD")
  }
  let month = if parts.len() > 1 { int(parts.at(1)) } else { 1 }
  let day = if parts.len() > 2 { int(parts.at(2)) } else { 1 }
  parse-date(datetime(year: year, month: month, day: day))
}

#let fold-paragraph(x) = {
  if type(x) != str { return x }
  x.split("\n").map(l => l.trim()).filter(l => l != "").join("")
}

/// 把 config.toml 的字典 + 默认值合成 theme tokens
#let build-tokens(cfg) = {
  let style = cfg.at("color", default: (:))
  // 成书唯一基色，允许逐项覆盖
  let accent = as-color(style.at("accent", default: book-colors.accent))
  let accent-ink = as-color(style.at("accent-ink", default: book-colors.accent-ink))
  let accent-soft = as-color(style.at("accent-soft", default: book-colors.accent-soft))
  let accent-wash = as-color(style.at("accent-wash", default: book-colors.accent-wash))

  let fonts = cfg.at("fonts", default: (:))
  let type-cfg = cfg.at("type", default: (:))
  let geom-cfg = cfg.at("layout", default: (:))

  let size = type-scale
  for (k, v) in type-cfg {
    if k in size { size.insert(k, parse-length(v, fallback: size.at(k))) }
  }

  let code-cfg = cfg.at("code", default: (:))
  let code-theme-name = code-cfg.at("theme", default: "github")
  let code-theme-path = code-cfg.at("theme-path", default: "themes/" + code-theme-name + ".tmTheme")

  let paper = geom-cfg.at("paper", default: geometry.paper)

  (
    code-theme: code-theme-path,
    code-show-lang: code-cfg.at("show-lang", default: true),
    code-show-lines: code-cfg.at("show-lines", default: true),
    code-inline-wrap: code-cfg.at("inline-wrap", default: true),
    code-width: parse-length(code-cfg.at("width", default: "92%"), fallback: 92%),
    accent: accent,
    accent-ink: accent-ink,
    accent-soft: accent-soft,
    accent-wash: accent-wash,
    ink: as-color(book-colors.ink),
    ink-weak: as-color(book-colors.ink-weak),
    ink-mute: as-color(book-colors.ink-mute),
    rule: as-color(book-colors.rule),
    rule-strong: as-color(book-colors.rule-strong),
    surface: as-color(book-colors.surface),
    surface-alt: as-color(book-colors.surface-alt),
    paper: as-color(book-colors.paper),
    code-fg: as-color(book-colors.code-fg),
    callouts: {
      let merged = callout-kinds
      let user = cfg.at("callouts", default: (:))
      for (k, patch) in user {
        if k in merged {
          let base = merged.at(k)
          let next = (:)
          for (bk, bv) in base { next.insert(bk, bv) }
          for (pk, pv) in patch { next.insert(pk, pv) }
          merged.insert(k, next)
        } else {
          merged.insert(k, patch)
        }
      }
      merged
    },
    fonts: (
      sans: fonts.at("sans", default: default-fonts.sans),
      mono: fonts.at("mono", default: default-fonts.mono),
    ),
    size: size,
    space: space,
    stroke: stroke,
    radius: radius,
    rhythm: (
      leading: parse-length(type-cfg.at("leading", default: none), fallback: rhythm.leading),
      par-spacing: parse-length(type-cfg.at("par-spacing", default: none), fallback: rhythm.par-spacing),
      list-indent: rhythm.list-indent,
      list-body-indent: rhythm.list-body-indent,
    ),
    geometry: (
      paper: paper,
      margin: geometry.margin,
      header-gap: geometry.header-gap,
      footer-gap: geometry.footer-gap,
      binding: geometry.binding,
    ),
  )
}

/// 解析 [doc] 书目元数据
#let build-meta(cfg) = {
  let doc = cfg.at("doc", default: (:))
  let title = doc.at("title", default: "")
  if title == "" or title == none {
    panic("config.toml: [doc].title 不能为空")
  }
  let authors = doc.at("authors", default: ())
  if type(authors) == str { authors = (authors,) }
  let keywords = doc.at("keywords", default: ())
  if type(keywords) == str { keywords = (keywords,) }
  let history = doc.at("history", default: ()).map(h => (
    version: str(h.at(0)),
    date: str(h.at(1)),
    note: fold-paragraph(str(h.at(2))),
    author: if h.len() > 3 { str(h.at(3)) } else { none },
  ))
  (
    title: fold-paragraph(title),
    subtitle: fold-paragraph(doc.at("subtitle", default: none)),
    author: authors.map(a => fold-paragraph(str(a))),
    team: fold-paragraph(doc.at("team", default: none)),
    org: fold-paragraph(doc.at("org", default: none)),
    version: fold-paragraph(doc.at("version", default: none)),
    date: parse-date(doc.at("date", default: auto)),
    category: fold-paragraph(doc.at("category", default: none)),
    keywords: keywords.map(k => fold-paragraph(str(k))),
    abstract: fold-paragraph(doc.at("abstract", default: none)),
    history: history,
  )
}

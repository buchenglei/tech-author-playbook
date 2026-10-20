// =============================================================================
//  main.typ —— 书稿编译入口
// =============================================================================

#import "src/book.typ": book

#let cfg = toml("config.toml")
#let chapter-pagebreak = cfg.at("layout", default: (:)).at("chapter-pagebreak", default: true)

#show: book.with(config: cfg)

#for (i, ch) in cfg.chapters.enumerate() {
  if i > 0 and chapter-pagebreak { pagebreak(weak: true) }
  include ch.path
}

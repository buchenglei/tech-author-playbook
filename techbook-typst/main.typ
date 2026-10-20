// =============================================================================
//  main.typ —— 书稿唯一编译入口
// -----------------------------------------------------------------------------
//  默认编译主书稿（config.toml）：
//    typst compile --root . main.typ dist/book.pdf
//  指定其他配置：
//    typst compile --root . --input doc=path/to/config.toml main.typ dist/other.pdf
//  推荐：nu build.nu
// =============================================================================

#import "src/book.typ": book

#let doc-path = sys.inputs.at("doc", default: "config.toml")
#let cfg = toml(doc-path)
#let chapter-pagebreak = cfg.at("layout", default: (:)).at("chapter-pagebreak", default: true)

#show: book.with(config: cfg)

#for (i, ch) in cfg.chapters.enumerate() {
  if i > 0 and chapter-pagebreak { pagebreak(weak: true) }
  include ch.path
}

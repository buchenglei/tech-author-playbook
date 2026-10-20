// =============================================================================
//  book.typ —— 包入口（techbook）
// -----------------------------------------------------------------------------
//  #import "@local/techbook:0.4.0": *
//  #show: book.with(config: toml("config.toml"))
// =============================================================================

#import "theme.typ": book
#import "lib/tokens.typ": build-tokens, build-meta
#import "component.typ": (
  tip, warning, pit, best,
  keypoint, lead, quote,
  goal, summary, exercises,
  preface, appendix,
  code-block, listing, tbl, fig, steps,
  hl, kbd, path, code, term,
  callout,
)

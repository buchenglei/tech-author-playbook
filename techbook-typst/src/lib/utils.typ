// =============================================================================
//  lib/utils.typ —— 纯函数工具
// =============================================================================

#let cn-digits = ("〇", "一", "二", "三", "四", "五", "六", "七", "八", "九")

/// 1 → "一"，12 → "十二"
#let to-cn(n) = {
  if n <= 0 { return str(n) }
  if n < 10 { return cn-digits.at(n) }
  if n < 20 {
    let r = calc.rem(n, 10)
    return "十" + if r == 0 { "" } else { cn-digits.at(r) }
  }
  if n < 100 {
    let r = calc.rem(n, 10)
    return cn-digits.at(calc.floor(n / 10)) + "十" + if r == 0 { "" } else { cn-digits.at(r) }
  }
  if n < 1000 {
    let h = calc.floor(n / 100)
    let r = calc.rem(n, 100)
    return cn-digits.at(h) + "百" + (
      if r == 0 { "" } else if r < 10 { "零" + cn-digits.at(r) } else { to-cn(r) }
    )
  }
  str(n)
}

/// 作者展示
#let author-text(meta) = {
  if meta.author.len() == 0 { "" } else { meta.author.join("、") }
}

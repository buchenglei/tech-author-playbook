# =============================================================================
#  build.nu —— 构建入口
# -----------------------------------------------------------------------------
#  nu build.nu              # all：样书 + 冒烟 → dist/
#  nu build.nu book         # 仅样书 PDF
#  nu build.nu doctor       # 冒烟 + 字体回退统计
#  nu build.nu lint         # 章节禁止 #set page/text/par
#  nu build.nu init <名称>  # 在上级目录创建书稿项目（snapshot）
#  nu build.nu init-linked <名称>  # 薄书稿，依赖 @local/techbook
#  nu build.nu install      # 安装 @local/techbook
#  nu build.nu clean
#  环境变量 TYPST 可指定 typst 路径
# =============================================================================

def typst_bin [] {
  if ("TYPST" in $env) and not ($env.TYPST | is-empty) {
    $env.TYPST
  } else {
    "typst"
  }
}

def ensure_dist [] {
  if not ("dist" | path exists) {
    mkdir dist
  }
}

def run_typst [args: list<string>] {
  ensure_dist
  let bin = (typst_bin)
  let err_file = (["dist" "last-typst.err"] | path join)
  let result = (^$bin ...$args | complete)
  $result.stderr | save --force $err_file
  if $result.exit_code != 0 {
    print $"error: typst exit ($result.exit_code)"
    open --raw $err_file | print
    exit 1
  }
}

def compile_doc [input: string, output: string, doc_cfg?: string] {
  print $"==> ($input) -> ($output)"
  mut args = [compile --root . --diagnostic-format short]
  if $doc_cfg != null and not ($doc_cfg | is-empty) {
    $args = ($args | append [--input $"doc=($doc_cfg)"])
  }
  $args = ($args | append [$input $output])
  run_typst $args
}

def task_book [] {
  compile_doc main.typ (["dist" "book.pdf"] | path join)
  print "built dist/book.pdf"
}

def task_all [] {
  task_book
  task_doctor
  print "built all → dist/"
}

def task_doctor [] {
  let bin = (typst_bin)
  print $"typst : ((do { ^$bin --version }) | str trim)"
  ensure_dist
  let log = (["dist" "doctor.log"] | path join)
  let result = (^$bin compile --root . --diagnostic-format short tests/smoke.typ (["dist" "smoke.pdf"] | path join) | complete)
  $result.stderr | save --force $log
  if $result.exit_code != 0 {
    open --raw $log | lines | where {|l| $l =~ "error:|panicked"} | each {|l| print $l}
    print "!! smoke failed"
    exit 1
  }
  let notes = (open --raw $log | lines | where {|l| $l =~ "unknown font family"} | length)
  print ($notes | into string | append " font fallback note(s)" | str join)
  print "OK"
}

def task_lint [] {
  let files = ((glob "chapters/*.typ") | append (glob "src/template/chapters/*.typ"))
  mut bad = false
  for f in $files {
    let hits = (open --raw $f
      | lines
      | where {|l| $l =~ '^[[:space:]]*#set (page|text|par)\b' })
    if ($hits | length) > 0 {
      print $"!! ($f) must not use #set page/text/par"
      $bad = true
    }
  }
  if not $bad {
    print "lint OK"
  } else {
    exit 1
  }
}

def task_init_linked [name: string] {
  let parent = (pwd | path dirname)
  let dest = ($parent | path join $name)
  if ($dest | path exists) {
    print $"target exists: ($dest)"
    exit 1
  }
  mkdir ($dest | path join "chapters")
  mkdir ($dest | path join "dist")
  cp src/template/config.toml $dest
  cp -r src/template/chapters/* ($dest | path join "chapters")
  # 薄项目：引擎走 @local/techbook，改写入口与章节 import
  open --raw src/template/main.typ
    | str replace 'src/book.typ' '@local/techbook:0.4.0'
    | save --force ($dest | path join "main.typ")
  for f in (glob ([$dest "chapters" "*.typ"] | path join)) {
    open --raw $f
      | str replace '../src/book.typ' '@local/techbook:0.4.0'
      | save --force $f
  }
  print $"created thin project ($dest)"
  print "请先在本仓库执行 nu build.nu install 安装 @local/techbook"
  print $"然后: cd ($dest); typst compile --root . main.typ dist/book.pdf"
}

def task_init [name: string] {
  let parent = (pwd | path dirname)
  let dest = ($parent | path join $name)
  if ($dest | path exists) {
    print $"target exists: ($dest)"
    exit 1
  }
  mkdir ($dest | path join "chapters")
  mkdir ($dest | path join "src")
  cp src/template/config.toml $dest
  cp src/template/main.typ $dest
  cp -r src/template/chapters/* ($dest | path join "chapters")
  # 引擎快照进 src/，与 main.typ / 章节 import 路径一致
  for f in [book.typ theme.typ component.typ cover.typ lib themes] {
    cp -r (["src" $f] | path join) ($dest | path join "src")
  }
  mkdir ($dest | path join "dist")
  print $"created ($dest)"
  print "edit config.toml and chapters/, then: typst compile --root . main.typ dist/book.pdf"
}

def task_package [] {
  ensure_dist
  let ver = "0.4.0"
  let dest = (["dist" "pkg" "local" "techbook" $ver] | path join)
  if ($dest | path exists) {
    rm -rf $dest
  }
  mkdir ($dest | path join "lib")
  mkdir ($dest | path join "themes")
  cp src/book.typ $dest
  cp src/theme.typ $dest
  cp src/component.typ $dest
  cp src/cover.typ $dest
  cp src/lib/tokens.typ ($dest | path join "lib")
  cp src/lib/utils.typ ($dest | path join "lib")
  cp src/themes/github.tmTheme ($dest | path join "themes")
  cp README.md AGENTS.md $dest
  $'
[package]
name = "techbook"
version = "0.4.0"
entrypoint = "book.typ"
authors = ["docs"]
license = "MIT"
description = "Typst techbook template"
compiler = "0.15.0"
' | save --force ([$dest "typst.toml"] | path join)
  print $"packaged -> ($dest)"
}

def task_install [] {
  task_package
  let ver = "0.4.0"
  mut user_root = ""
  if "TYPST_PACKAGE_PATH" in $env {
    $user_root = $env.TYPST_PACKAGE_PATH
  } else if ("LOCALAPPDATA" in $env) {
    $user_root = ($env.LOCALAPPDATA | path join "typst" "packages")
  } else if (sys host | get name) == "Darwin" {
    $user_root = ([$env.HOME "Library" "Application Support" "typst" "packages"] | path join)
  } else {
    $user_root = ([$env.HOME ".local" "share" "typst" "packages"] | path join)
  }
  let target = ([$user_root "local" "techbook" $ver] | path join)
  if ($target | path exists) {
    rm -rf $target
  }
  mkdir $target
  let src = (["dist" "pkg" "local" "techbook" $ver] | path join)
  for f in [book.typ theme.typ component.typ cover.typ lib themes typst.toml README.md AGENTS.md] {
    let item = ([$src $f] | path join)
    if ($item | path exists) {
      cp -r $item $target
    }
  }
  print $"installed @local/techbook:($ver) -> ($target)"
  print "书稿 main.typ 使用: #import \"@local/techbook:0.4.0\": book"
}

def task_clean [] {
  if ("dist" | path exists) {
    rm -rf dist
  }
  if ("out" | path exists) {
    rm -rf out
  }
  print "cleaned dist/ out/"
}

def main [
  task: string = "all",
  name: string = "",
] {
  match $task {
    "all" => { task_all }
    "book" => { task_book }
    "doctor" => { task_doctor }
    "lint" => { task_lint }
    "init" => {
      if ($name | is-empty) {
        print "usage: nu build.nu init <name>   (snapshot: 拷贝引擎)"
        print "       nu build.nu init-linked <name>  (推荐: 依赖 @local/techbook)"
        exit 1
      }
      task_init $name
    }
    "init-linked" => {
      if ($name | is-empty) {
        print "usage: nu build.nu init-linked <name>"
        exit 1
      }
      task_init_linked $name
    }
    "package" => { task_package }
    "install" => { task_install }
    "clean" => { task_clean }
    _ => {
      print $"unknown task: ($task)"
      print "tasks: all book doctor lint package install init <name> init-linked <name> clean"
      exit 1
    }
  }
}

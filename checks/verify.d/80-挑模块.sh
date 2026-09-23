# ── 挑模块 ─────────────────────────────────────────────────────────
# 入口按「本次改了哪些文件」挑模块。挑错了表现是静默的：该跑的没跑，一路绿灯，
# 而人以为检查过了。所以这里喂几组写死的改动清单进去，看它挑出来的是不是该挑的。
#
# 两个为这一步留的口子：VERIFY_CHANGED_FROM 指一个文件，入口就从那里读改动清单
# 而不是问 git；--list 只列出会跑哪些模块、不真跑。有了这两个，这份检查才是确定
# 的——不依赖当前暂存区里恰好有什么。
#
# 本模块自己盯 checks/，而入口的规矩是「改动碰到 checks/ 就跑全套」，所以夹具一
# 被动到这模块就会跑到，不会因为挑模块挑错而把自己跳过。
# watch: checks/

entry="${SCRIPT_DIR}/verify.sh"

# 喂一份改动清单进去，要回它会挑哪些模块（一行一个）
pick() {
  local list; list="$(scratch_file)"
  printf '%s\n' "$1" > "$list"
  VERIFY_CHANGED_FROM="$list" bash "$entry" --changed --list 2>/dev/null
}

expect_pick() {   # expect_pick <说明> <改动清单> <该挑中的模块名...>
  local desc="$1" files="$2"; shift 2
  local out; out="$(pick "$files")"
  local m
  for m in "$@"; do
    case "$out" in
      *"$m"*) ;;
      *) fail "${desc}：没挑中 ${m}（实际挑了：${out:-无}）" ;;
    esac
  done
}

expect_not_pick() {   # expect_not_pick <说明> <改动清单> <不该挑中的模块名...>
  local desc="$1" files="$2"; shift 2
  local out; out="$(pick "$files")"
  local m
  for m in "$@"; do
    case "$out" in
      *"$m"*) fail "${desc}：不该挑 ${m} 却挑了（实际挑了：${out}）" ;;
    esac
  done
}

# 改通知判定：只跑 40
expect_pick "改 plugin/hooks/notify" "plugin/hooks/notify" "40-notify.sh"
expect_not_pick "改 plugin/hooks/notify" "plugin/hooks/notify" "50-notify-render.sh" "30-statusline-smoke.sh"

# 改 notify.ps1：只跑 50。40 与 50 的前缀关系最容易误伤——按前缀匹配的话
# "plugin/hooks/notify" 会把 "plugin/hooks/notify.ps1" 也吃进来，白白多跑 51 秒
expect_pick "改 plugin/hooks/notify.ps1" "plugin/hooks/notify.ps1" "50-notify-render.sh"
expect_not_pick "改 plugin/hooks/notify.ps1" "plugin/hooks/notify.ps1" "40-notify.sh"

# 改状态栏脚本：20 与 30 都要跑
expect_pick "改 statusline 脚本" "plugin/statusline/statusline.py" "20-statusline-sync.sh" "30-statusline-smoke.sh"
expect_not_pick "改 statusline 脚本" "plugin/statusline/statusline.py" "40-notify.sh"

# 改 session-start：10、20、25 都要跑（它们都靠它把东西同步出去）
expect_pick "改 session-start" "plugin/hooks/session-start" "10-session-start.sh" "20-statusline-sync.sh" "25-rules-sync.sh"
expect_not_pick "改 session-start" "plugin/hooks/session-start" "30-statusline-smoke.sh"

# 改插件根之外的文档：一个都不跑。这是常态，不是异常
expect_not_pick "改 README" "README.md" "10-session-start.sh" "40-notify.sh"
expect_not_pick "改 docs" "docs/superpowers/plans/x.md" "60-wiring.sh"

# 暂存区是空的（空提交、只改了被忽略的文件）：挑不出任何模块，不该报错
out_empty="$(pick "")"
if [ -n "$out_empty" ]; then
  fail "改动清单为空时不该挑中任何模块，实际挑了：${out_empty}"
fi

# 改动清单里含被删除的文件（git mv 之后的提交就是这么显示的）：
# 文件没了正是最该跑检查的时候，照样要挑中。
# 输入和上面「改 notify」那条字面一样，因为入口从 git 拿到的只有路径、看不出是改是删——
# 这一条要钉的就是「删除也照样出现在清单里、也照样挑得中」，别把它当成重复的删掉。
expect_pick "被删掉的 notify" "plugin/hooks/notify" "40-notify.sh"

# 夹具自己被动过：跑全套，不是只跑某一个。夹具的问题会波及所有模块
expect_pick "改入口自己" "checks/verify.sh" "10-session-start.sh" "40-notify.sh" "60-wiring.sh" "80-挑模块.sh"

# ── 真 git 那条路径 ────────────────────────────────────────────────
# 上面那些走的是 VERIFY_CHANGED_FROM，绕开了 git。真实那条路要单独验一次，因为它有
# 自己的坑：git 默认把非 ASCII 路径转义成 "plugin/hooks/\344\270\255\346\226\207.txt"
# （带引号、八进制），而声明的路径是原样的中文，一条都对不上。表现是改了中文名文件却
# 一个模块都不跑、放行退出 0 —— 静默，正是这个仓库一直在防的那类失败。
# 本仓库中文文件名很多（技能名就是中文），所以这个坑踩得到。
#
# 没拿真仓库试：得往暂存区里塞东西，会搅乱当时正要提交的内容。这里造个小仓库、把真
# 入口拷进去，跑的是同一份代码。
if ! command -v git >/dev/null 2>&1; then
  echo "提示：没找到 git，跳过真 git 挑模块的验证"
else
  gits="$(scratch_dir)"
  mkdir -p "${gits}/checks/verify.d" "${gits}/plugin/hooks"
  cp "$entry" "${gits}/checks/verify.sh"
  printf '# watch: plugin/\n' > "${gits}/checks/verify.d/10-x.sh"
  printf 'x\n' > "${gits}/plugin/hooks/中文.txt"
  (
    cd "$gits" || exit 1
    git init -q .
    git config user.email t@example.com
    git config user.name t
    git add -A
    git commit -qm init
    printf 'y\n' > "plugin/hooks/中文.txt"
    git add "plugin/hooks/中文.txt"
  ) >/dev/null 2>&1

  out_git="$(cd "$gits" && bash checks/verify.sh --changed --list 2>&1)"
  case "$out_git" in
    *10-x.sh*) ;;
    *) fail "改非 ASCII 路径的文件：没挑中 10-x.sh（实际挑了：${out_git:-无}）" ;;
  esac
fi

# 声明本身必须站得住（模块缺 watch 就报错、声明了不存在的路径就报错）这一条不在
# 这里验：入口遇到这种声明会硬失败，一跑就撞上，不是静默的。任务 3 Step 7 手工验一次。

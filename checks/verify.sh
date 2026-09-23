#!/usr/bin/env bash
# 校验脚本的入口：查依赖、挑模块、按序加载 verify.d/ 下的模块、汇总结果。
# 每个模块只校验一件事，入口不掺业务逻辑。
#
#   bash checks/verify.sh                    跑全部
#   bash checks/verify.sh notify             只跑文件名里带 notify 的模块
#   bash checks/verify.sh --changed          只跑被本次改动影响到的模块（按暂存区挑，改完自己跑用）
#   bash checks/verify.sh --changed --list   只列出会跑哪些模块，不真跑
#
# 模块是被 source 进同一个 shell 的，共享这里定义的 fail / scratch_dir /
# scratch_file / test_home / statusline_src / rules_src。别改成靠 $( ) 返回值传数组那种写法：
# 子 shell 里改的东西传不出来（30 那块里记着同一类坑）。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PLUGIN_DIR="${REPO_ROOT}/plugin"   # 插件根：会跟着插件发出去的那部分
HOOKS_DIR="${PLUGIN_DIR}/hooks"    # 运行时 hook 所在

# 下面这些变量分两类，别混：
#   SCRIPT_DIR —— 检查脚本自己的东西（verify.d 在哪）
#   REPO_ROOT / PLUGIN_DIR / HOOKS_DIR —— 被检查的运行时文件在哪
# 两者以前都写成 ${SCRIPT_DIR}/...，长得一模一样，改目录时最容易一起改错。
RULES_FILE="${PLUGIN_DIR}/skills/plain-language/rules.md"
VERIFY_D="${SCRIPT_DIR}/verify.d"
# cmd.exe 的批处理分支要从仓库根用相对路径调它（见 10 里那段说明）
RUN_HOOK_CMD_WIN='plugin\hooks\run-hook.cmd'

fails=0
fail() { echo "FAIL: $1" >&2; fails=$((fails + 1)); }

# 临时文件统一登记，退出时一起删。原来是每个小节自己 rm -rf，中途 exit 就漏下。
_scratch_list="$(mktemp)"
scratch_dir()  { local d; d="$(mktemp -d)"; printf '%s\n' "$d" >> "$_scratch_list"; printf '%s' "$d"; }
scratch_file() { local f; f="$(mktemp)";    printf '%s\n' "$f" >> "$_scratch_list"; printf '%s' "$f"; }
_cleanup() {
  local p
  while IFS= read -r p; do [ -n "$p" ] && rm -rf "$p"; done < "$_scratch_list"
  rm -f "$_scratch_list"
}
trap _cleanup EXIT

# rules.md 带 CR 时字节数会和文档记录的对不上，多半是编辑器写回的。只是提示，不算失败——
# 仓库内容应统一 LF，见 .gitattributes。
# 用 tr 数 CR，别用 grep。Git Bash 的 grep 在文本模式下匹配不到 CR，两条死路都会骗人：
# CR 取自变量时 grep "$CR" 恒为 0；grep -c $'\r' 这种写法取输出时 $'\r' 会退化成空模式，
# 返回的其实是**行数**——看着像「检测到了 CR」，其实每行都算命中
# （实测：3 行 1 个 CR 的文件返回 3，全 LF 的 3 行文件也返回 3）。
# 文件不在时别让重定向的报错漏到 stderr（先判可读，判定语义不变）。
if [ -r "$RULES_FILE" ] && [ "$(LC_ALL=C tr -dc '\r' < "$RULES_FILE" | wc -c)" -gt 0 ]; then
  echo "提示：rules.md 含 CR 行尾，字节数与文档记录对不上（多半是编辑器写回的）。仓库内容应统一 LF，见 .gitattributes"
fi

# 解析注入文本要用 node，接住它的报错要用 mktemp，比对同步过去的脚本要用 cmp。缺了就直接说清楚，别把「工具没装」误报成「JSON 不合法」
for dep in node mktemp cmp; do
  if ! command -v "$dep" >/dev/null 2>&1; then
    echo "FAIL: 需要 ${dep} 才能校验 hook" >&2
    exit 1
  fi
done

# 10、20、25 共用这个替身 HOME：session-start 会把 statusline/ 下的脚本和 rules/ 下的
# 规则同步到配置目录，不换 HOME 就会写进真实用户的 ~/.claude。校验脚本不该动真东西。
test_home="$(scratch_dir)"
statusline_src="$(cd "${PLUGIN_DIR}/statusline" 2>/dev/null && pwd)"
rules_src="$(cd "${PLUGIN_DIR}/rules" 2>/dev/null && pwd)"

# ── 参数 ───────────────────────────────────────────────────────────
by_changed=0
list_only=0
filter=""
for arg in "$@"; do
  case "$arg" in
    --changed) by_changed=1 ;;
    --list)    list_only=1 ;;
    -*) echo "FAIL: 不认识的参数「${arg}」" >&2; exit 1 ;;
    *)  if [ -n "$filter" ]; then
          echo "FAIL: 只接受一个筛选子串，多给了「${arg}」" >&2; exit 1
        fi
        filter="$arg" ;;
  esac
done

mods_all=("$VERIFY_D"/*.sh)
if [ ! -e "${mods_all[0]}" ]; then
  echo "FAIL: ${VERIFY_D} 下没有校验模块" >&2
  exit 1
fi

# ── watch 声明 ─────────────────────────────────────────────────────
# 每个模块都必须在文件头写一行 `# watch: <路径> [<路径>...]`，路径以仓库根为基准；
# 以 / 结尾的按目录前缀匹配，否则按整条路径相等匹配。
#
# 这一行只能「读」出来，不能靠 source 拿——模块一被 source 就会跑起来
# （10 第 9 行就执行了 session-start），必须在决定跑不跑之前就用读文本的方式拿到。
watch_of() { sed -n 's/^# watch:[[:space:]]*//p' "$1" | head -1; }

# 声明站不住就直接报错，不静默跳过——静默跳过等于这个模块永远不会跑，
# 而人以为检查过了。这是本仓库其他模块一直在防的那类失败。
for mod in "${mods_all[@]}"; do
  _name="${mod##*/}"
  _w="$(watch_of "$mod")"
  if [ -z "$_w" ]; then
    echo "FAIL: ${_name} 没有声明 watch（文件头缺一行「# watch: 路径」）" >&2
    exit 1
  fi
  for _p in $_w; do
    case "$_p" in
      */) [ -d "${REPO_ROOT}/${_p%/}" ] || { echo "FAIL: ${_name} 声明的目录不存在：${_p}" >&2; exit 1; } ;;
      *)  [ -e "${REPO_ROOT}/${_p}" ]   || { echo "FAIL: ${_name} 声明的路径不存在：${_p}" >&2; exit 1; } ;;
    esac
  done
done
unset _name _w _p

# ── 按改动挑模块 ───────────────────────────────────────────────────
# 一条声明路径是否命中一个改动文件。目录声明按前缀，文件声明按整条相等。
# 后半条不能省：`plugin/hooks/notify` 若按前缀匹配，会把 `plugin/hooks/notify.ps1`
# 也吃进来，白白多跑 51 秒。
watch_hits() {
  case "$1" in
    */) case "$2" in "$1"*) return 0 ;; esac ;;
    *)  [ "$2" = "$1" ] && return 0 ;;
  esac
  return 1
}

mods=("${mods_all[@]}")
if [ "$by_changed" -eq 1 ]; then
  if [ -n "${VERIFY_CHANGED_FROM:-}" ]; then
    changed="$(cat "$VERIFY_CHANGED_FROM" 2>/dev/null)"
  else
    # -c core.quotePath=false 不能省：git 默认把非 ASCII 路径转义成
    # "plugin/hooks/\344\270\255\346\226\207.txt"（带引号、八进制），声明的路径是
    # 原样中文，一条都对不上——表现是改了中文名文件却一个模块都不跑、放行退出 0。
    # 本仓库中文文件名很多，这个坑踩得到（80 里造了小仓库钉住它）。
    changed="$(git -C "$REPO_ROOT" -c core.quotePath=false diff --cached --name-only 2>/dev/null)"
  fi

  # 夹具自己被动过（入口、模块，任何 checks/ 下的东西）：跑全套，不是只跑某一个。
  # 夹具的问题会波及所有模块，挑着跑会有漏网的。
  run_all=0
  while IFS= read -r _f; do
    case "$_f" in checks/*) run_all=1 ;; esac
  done <<EOF
$changed
EOF
  unset _f

  picked=()
  for mod in "${mods_all[@]}"; do
    if [ "$run_all" -ne 1 ]; then
      _w="$(watch_of "$mod")"
      _hit=0
      while IFS= read -r _f; do
        [ -n "$_f" ] || continue
        for _p in $_w; do
          watch_hits "$_p" "$_f" && _hit=1
        done
      done <<EOF
$changed
EOF
      unset _f
      [ "$_hit" -eq 1 ] || continue
    fi
    picked+=("$mod")
  done
  unset _w _p _hit
  # 空数组在 set -u 下的写法：先判长度再展开，bash 4.2 到 5.x 都安全
  if [ "${#picked[@]}" -eq 0 ]; then mods=(); else mods=("${picked[@]}"); fi
fi

# ── 子串筛选 ───────────────────────────────────────────────────────
if [ -n "$filter" ]; then
  _kept=()
  for mod in "${mods[@]}"; do
    case "${mod##*/}" in
      *"$filter"*) _kept+=("$mod") ;;
    esac
  done
  if [ "${#_kept[@]}" -eq 0 ]; then mods=(); else mods=("${_kept[@]}"); fi
  unset _kept
fi

# ── 跑 ─────────────────────────────────────────────────────────────
if [ "${#mods[@]}" -eq 0 ]; then
  # --changed 挑不出模块是常态（改 README 就属于这种），放行不报错。
  # 带子串筛选却一个都没匹配上则是用错了，按原来的规矩报错。
  if [ "$by_changed" -eq 1 ]; then
    [ "$list_only" -eq 1 ] || echo "本次改动没有匹配到任何检查模块"
    exit 0
  fi
  echo "FAIL: 没有模块匹配「${filter}」（可用的：${mods_all[*]##*/}）" >&2
  exit 1
fi

for mod in "${mods[@]}"; do
  name="${mod##*/}"
  if [ "$list_only" -eq 1 ]; then
    echo "$name"
    continue
  fi
  echo "── ${name}"
  # shellcheck source=/dev/null
  . "$mod"
done

[ "$list_only" -eq 1 ] && exit 0

echo
if [ "$fails" -eq 0 ]; then
  echo "全部通过"
else
  echo "${fails} 项失败" >&2
  exit 1
fi

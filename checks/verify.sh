#!/usr/bin/env bash
# 校验脚本的入口：查依赖、按序加载 verify.d/ 下的模块、汇总结果。
# 每个模块只校验一件事，入口不掺业务逻辑。
#
#   bash checks/verify.sh            跑全部
#   bash checks/verify.sh notify     只跑文件名里带 notify 的模块
#
# 模块是被 source 进同一个 shell 的，共享这里定义的 fail / scratch_dir /
# scratch_file / test_home / statusline_src / rules_src。别改成靠 $( ) 返回值传数组那种写法：
# 子 shell 里改的东西传不出来（30 那块里记着同一类坑）。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PLUGIN_DIR="${REPO_ROOT}/plugin"   # 插件根：会跟着插件发出去的那部分
HOOKS_DIR="${PLUGIN_DIR}/hooks"    # 运行时 hook 所在
# cmd.exe 的批处理分支要从仓库根用相对路径调它（见 10 里那段说明）。
# 从仓库根起算，所以前面带 plugin/。
RUN_HOOK_CMD_WIN='plugin\hooks\run-hook.cmd'
RULES_FILE="${PLUGIN_DIR}/skills/plain-language/rules.md"
VERIFY_D="${SCRIPT_DIR}/verify.d"

# 下面这些变量分两类，别混：
#   SCRIPT_DIR —— 检查脚本自己的东西（verify.d 在哪）
#   REPO_ROOT / PLUGIN_DIR / HOOKS_DIR —— 被检查的运行时文件在哪
# 两者以前都写成 ${SCRIPT_DIR}/...，长得一模一样，改目录时最容易一起改错。

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

mods=("$VERIFY_D"/*.sh)
if [ ! -e "${mods[0]}" ]; then
  echo "FAIL: ${VERIFY_D} 下没有校验模块" >&2
  exit 1
fi

filter="${1:-}"
ran=0
for mod in "${mods[@]}"; do
  name="${mod##*/}"
  case "$name" in
    *"$filter"*) ;;
    *) continue ;;
  esac
  echo "── ${name}"
  # shellcheck source=/dev/null
  . "$mod"
  ran=$((ran + 1))
done

if [ "$ran" -eq 0 ]; then
  echo "FAIL: 没有模块匹配「${filter}」（可用的：${mods[*]##*/}）" >&2
  exit 1
fi

echo
if [ "$fails" -eq 0 ]; then
  echo "全部通过"
else
  echo "${fails} 项失败" >&2
  exit 1
fi

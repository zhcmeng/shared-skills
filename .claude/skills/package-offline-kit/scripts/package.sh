#!/usr/bin/env bash
# 把本仓库的插件打成离线安装包，放进指定目录。
#
#   bash package.sh [输出目录]
#
# 输出目录不给时用 C:/Study/offline-kit/skills。
# 包只从 HEAD 取：打包范围内有未提交改动就先停下，别把半个版本发出去。

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
DEFAULT_OUT='C:/Study/offline-kit/skills'
OUT_DIR="${1:-$DEFAULT_OUT}"

# 用户可能照 Windows 的写法传路径，反斜杠先换成正斜杠，bash 才认。
OUT_DIR="${OUT_DIR//\\//}"
OUT_DIR="${OUT_DIR%/}"
ZIP_NAME='shared-skills.zip'

TMP_ZIP=''
CHECK_DIR=''
cleanup() {
  [ -n "$TMP_ZIP" ] && rm -f "$TMP_ZIP"
  [ -n "$CHECK_DIR" ] && rm -rf "$CHECK_DIR"
  return 0
}
trap cleanup EXIT

fail() {
  echo "失败：$1" >&2
  exit 1
}

command -v git >/dev/null 2>&1 || fail '找不到 git。'
command -v unzip >/dev/null 2>&1 || fail '找不到 unzip——核对包内容要用它。'
[ -d "${REPO_ROOT}/.git" ] || fail "从脚本位置没找到仓库根（${REPO_ROOT}）。"
[ -d "${REPO_ROOT}/.claude-plugin" ] || fail '仓库根下没有 .claude-plugin/。'
[ -d "${REPO_ROOT}/plugin" ] || fail '仓库根下没有 plugin/。'

# 只打 HEAD 里的内容。打包范围内的未提交改动会让包与仓库对不上，先停。
dirty="$(git -C "$REPO_ROOT" status --porcelain -- .claude-plugin plugin)"
if [ -n "$dirty" ]; then
  printf '%s\n' "$dirty" >&2
  fail '上面这些改动还没提交。包只取 HEAD，先提交再打包。'
fi

# 输出目录不存在就建；路径被文件占着就停。
if [ -e "$OUT_DIR" ] && [ ! -d "$OUT_DIR" ]; then
  fail "${OUT_DIR} 被一个文件占着，换一个目录。"
fi
mkdir -p "$OUT_DIR" || fail "建不了输出目录 ${OUT_DIR}。"
OUT_DIR="$(cd "$OUT_DIR" && pwd)" || fail "进不去输出目录 ${OUT_DIR}。"
ZIP_PATH="${OUT_DIR}/${ZIP_NAME}"

# 读清单里的版本号要用 Python 3；机器上叫 python3、python 或 py -3 都行。
PYTHON=()
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; raise SystemExit(sys.version_info[0] != 3)' 2>/dev/null; then
  PYTHON=(python3)
elif command -v python >/dev/null 2>&1 && python -c 'import sys; raise SystemExit(sys.version_info[0] != 3)' 2>/dev/null; then
  PYTHON=(python)
elif command -v py >/dev/null 2>&1 && py -3 -c 'import sys' 2>/dev/null; then
  PYTHON=(py -3)
else
  fail '找不到 Python 3——两份清单的版本号要用它读。'
fi

read_version() {
  "${PYTHON[@]}" - "$1" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    data = json.load(f)

if "plugins" in data:
    for item in data["plugins"]:
        if item.get("name") == "shared-skills":
            print(item.get("version", ""))
            break
else:
    print(data.get("version", ""))
PY
}

MARKET_VER="$(read_version "${REPO_ROOT}/.claude-plugin/marketplace.json")"
PLUGIN_VER="$(read_version "${REPO_ROOT}/plugin/.claude-plugin/plugin.json")"
[ -n "$MARKET_VER" ] || fail 'marketplace.json 里没读到 shared-skills 的版本号。'
[ -n "$PLUGIN_VER" ] || fail 'plugin.json 里没读到版本号。'
if [ "$MARKET_VER" != "$PLUGIN_VER" ]; then
  fail "两处版本号不一致：marketplace.json 是 ${MARKET_VER}，plugin.json 是 ${PLUGIN_VER}。先改成同一个号。"
fi

# 先打到临时文件，核对都过了再挪过去；中途失败不会留下半个包。
TMP_ZIP="${OUT_DIR}/.${ZIP_NAME}.tmp.$$"
git -C "$REPO_ROOT" archive --prefix=shared-skills/ --format=zip -o "$TMP_ZIP" HEAD .claude-plugin plugin \
  || fail 'git archive 没打成包。'

# 顶层只能有一个 shared-skills/。
top="$(unzip -Z1 "$TMP_ZIP" | sed 's#/.*##' | sort -u)"
[ "$top" = 'shared-skills' ] || fail "包的顶层不是只有一个 shared-skills/：${top:-（空）}"

# 开发用的目录一个都不该在包里。
leaked="$(unzip -Z1 "$TMP_ZIP" | grep -E '^shared-skills/(checks|docs|evals|tests|\.git)(/|$)' || true)"
[ -z "$leaked" ] || fail "包里混进了开发目录：${leaked}"

# 技能份数：包里的与仓库里的要对得上。
WANT_SKILLS="$(find "${REPO_ROOT}/plugin/skills" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ')"
GOT_SKILLS="$(unzip -Z1 "$TMP_ZIP" | grep -cE '^shared-skills/plugin/skills/[^/]+/SKILL\.md$' || true)"
if [ "$GOT_SKILLS" != "$WANT_SKILLS" ]; then
  fail "包里有 ${GOT_SKILLS} 个 SKILL.md，仓库里有 ${WANT_SKILLS} 个——有技能没进包，或者多进了。"
fi

# 包内两份清单的版本号，与仓库里的一致。
CHECK_DIR="$(mktemp -d)"
unzip -q "$TMP_ZIP" -d "$CHECK_DIR" || fail '解不开刚打的包。'
ZIP_MARKET_VER="$(read_version "${CHECK_DIR}/shared-skills/.claude-plugin/marketplace.json")"
ZIP_PLUGIN_VER="$(read_version "${CHECK_DIR}/shared-skills/plugin/.claude-plugin/plugin.json")"
[ "$ZIP_MARKET_VER" = "$MARKET_VER" ] || fail "包内 marketplace.json 的版本是 ${ZIP_MARKET_VER}，仓库里是 ${MARKET_VER}。"
[ "$ZIP_PLUGIN_VER" = "$PLUGIN_VER" ] || fail "包内 plugin.json 的版本是 ${ZIP_PLUGIN_VER}，仓库里是 ${PLUGIN_VER}。"

# 有 claude 命令就再跑一遍官方校验。校验器的提示（README、图标）不影响安装，成功时不打印。
validate() {
  local out
  if ! out="$(claude plugin validate "$1" 2>&1)"; then
    printf '%s\n' "$out" >&2
    fail "claude plugin validate 没过：$1"
  fi
}
if command -v claude >/dev/null 2>&1; then
  validate "${CHECK_DIR}/shared-skills"
  validate "${CHECK_DIR}/shared-skills/plugin"
fi

mv -f "$TMP_ZIP" "$ZIP_PATH" || fail "写不进 ${ZIP_PATH}。"
TMP_ZIP=''  # 已经挪走，退出时别再删

SIZE="$(du -h "$ZIP_PATH" | awk '{print $1}')"
echo "已打包：${ZIP_PATH}"
echo "版本：${MARKET_VER}"
echo "技能：${GOT_SKILLS} 个"
echo "大小：${SIZE}"
echo
echo '另一台机器上这样装：'
echo "  1. 解压 ${ZIP_NAME}，得到 shared-skills/ 文件夹"
echo '  2. 在 Claude Code 里执行：'
echo '     /plugin marketplace add <解压后的 shared-skills 文件夹路径>'
echo '     /plugin install shared-skills@shared-skills'

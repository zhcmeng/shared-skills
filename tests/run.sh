#!/usr/bin/env bash
# 跑技能脚本自己的测试：被测试的代码在 plugin/skills/<技能名>/scripts/ 下，
# 测试在 tests/<技能名>/test_<脚本名>.py。
#
#   bash tests/run.sh                      全跑
#   bash tests/run.sh test-case-design     只跑那一门
#
# 为什么单开一个入口、不挂进 checks/verify.sh：verify.sh 按改动的路径挑模块，
# 挂进去就成了「改任何一门技能都把这门的测试带着跑一遍」——没碰到的部分不该跑。
# 这一份按需跑：改了哪门的脚本就跑哪门。
#
# 一律带 -X utf8：技能脚本自己在 main() 里把重定向出去的那一路切成了 UTF-8
# （各自有一份 prefer_utf8），测试文件没有这一步；不带的话，管道上的中文按本机
# 区域编码 GBK 落下来，看的人拿到的是「���」。
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$#" -gt 1 ]; then
  echo "FAIL: 最多给一个技能名，现在给了 $# 个" >&2
  exit 1
fi
filter="${1:-}"

# Windows 上是 python，别的平台常见 python3。缺了就直说，别把「没装」当成「测试没过」
py="$(command -v python || command -v python3 || true)"
if [ -z "$py" ]; then
  echo "FAIL: 找不到 python，跑不了测试" >&2
  exit 1
fi

# 一份都没匹配上、或者给的技能名对不上任何一门，都按失败报。
# 静默放行等于这个入口没跑，而人以为跑过了——这本仓库一直在防那类失败。
shopt -s nullglob
files=("${REPO_ROOT}"/tests/*/test_*.py)
shopt -u nullglob

if [ "${#files[@]}" -eq 0 ]; then
  echo "FAIL: tests/ 下一份 test_*.py 都没有" >&2
  exit 1
fi

if [ -n "$filter" ]; then
  picked=()
  for f in "${files[@]}"; do
    case "${f#"${REPO_ROOT}"/}" in
      tests/"$filter"/*) picked+=("$f") ;;
    esac
  done
  if [ "${#picked[@]}" -eq 0 ]; then
    # 提示按「带测试的那几门」报，不拿 ls 列目录：tests/ 下还放着这份脚本自己，
    # 列进去会让人以为它是一门技能。
    dirs=""
    for f in "${files[@]}"; do
      d="${f#"${REPO_ROOT}"/tests/}"
      dirs="${dirs}${d%%/*} "
    done
    echo "FAIL: 没有叫「${filter}」的技能带测试（带测试的有：${dirs% }）" >&2
    exit 1
  fi
  files=("${picked[@]}")
fi

fails=0
for f in "${files[@]}"; do
  rel="${f#"${REPO_ROOT}"/}"
  echo "── ${rel}"
  # 输出先收进临时文件：过了就不用贴；没过才连它一起贴出来。
  # 贴的是末尾那段（tail）不是开头：测试的失败汇总和 Python 的报错都在末尾。
  out="$(mktemp)"
  if (cd "$REPO_ROOT" && "$py" -X utf8 "$rel") >"$out" 2>&1; then
    echo "   通过"
  else
    fails=$((fails + 1))
    echo "   没过，下面是它的输出：" >&2
    tail -40 "$out" >&2
  fi
  rm -f "$out"
done

echo
if [ "$fails" -eq 0 ]; then
  echo "全部通过"
else
  echo "${fails} 份没过" >&2
  exit 1
fi

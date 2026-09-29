#!/usr/bin/env bash
# 自查入口。按文件名顺序跑 verify.d/ 下的模块。
# 用法：bash checks/verify.sh [关键词]
#   给了关键词就只跑文件名里带该词的模块；不给就全跑。
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
filter="${1:-}"

rc=0
ran=0
for m in "$here"/verify.d/*.sh; do
  [ -e "$m" ] || continue
  name=$(basename "$m")
  if [ -n "$filter" ] && [[ "$name" != *"$filter"* ]]; then
    continue
  fi
  ran=$((ran + 1))
  echo "--- $name"
  if ! bash "$m"; then
    echo "  [红] $name 没过"
    rc=1
  fi
done

echo
if [ "$ran" = "0" ]; then
  echo "没有匹配到任何模块（关键词：$filter）。"
  exit 1
fi
[ "$rc" = "0" ] && echo "全部通过。" || echo "还有红的。"
exit $rc

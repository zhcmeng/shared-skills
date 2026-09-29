#!/usr/bin/env bash
# 查 docs/ 下的文章里，标题层级有没有跳级（一级标题下面直接三级这种）。
set -uo pipefail

root=$(cd "$(dirname "$0")/../.." && pwd)
rc=0

while IFS= read -r f; do
  prev=0
  while IFS= read -r line; do
    case "$line" in
      '#'*)
        level=$(printf '%s' "$line" | sed 's/^\(#*\).*/\1/' | tr -d '\n' | wc -c)
        if [ "$prev" -gt 0 ] && [ "$level" -gt $((prev + 1)) ]; then
          echo "  [红] $(basename "$f")：标题从 $prev 级跳到 $level 级"
          rc=1
        fi
        prev=$level
        ;;
    esac
  done < "$f"
done < <(find "$root/docs" -name '*.md' 2>/dev/null)

[ "$rc" = "0" ] && echo "  [绿] 标题层级没跳级"
exit $rc

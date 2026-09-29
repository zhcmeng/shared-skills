#!/usr/bin/env bash
# 查 docs/ 下的文章里，相对链接指的路径在不在。
set -uo pipefail

root=$(cd "$(dirname "$0")/../.." && pwd)
rc=0

while IFS= read -r f; do
  dir=$(dirname "$f")
  while IFS= read -r target; do
    [ -n "$target" ] || continue
    case "$target" in
      http://*|https://*|mailto:*|\#*) continue ;;
    esac
    target=${target%%#*}
    [ -n "$target" ] || continue
    if [ ! -e "$dir/$target" ]; then
      echo "  [红] $(basename "$f")：链接指的 $target 不在"
      rc=1
    fi
  done < <(grep -o '](\([^)]*\))' "$f" | sed 's/^](//; s/)$//')
done < <(find "$root/docs" -name '*.md' 2>/dev/null)

[ "$rc" = "0" ] && echo "  [绿] 链接都指得到"
exit $rc

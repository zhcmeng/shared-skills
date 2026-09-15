#!/usr/bin/env bash
# 校验 SessionStart hook：输出必须是合法 JSON，且注入文本非空、含规则关键词。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fails=0
fail() { echo "FAIL: $1" >&2; fails=$((fails + 1)); }

out="$(bash "${SCRIPT_DIR}/session-start" 2>/dev/null)"
if [ -z "$out" ]; then
  fail "session-start 没有输出（应为一行 JSON）"
  echo "1 项失败" >&2
  exit 1
fi

ctx="$(printf '%s' "$out" | node -e '
let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{
  let j;try{j=JSON.parse(s)}catch(e){console.error("JSON 解析失败: "+e.message);process.exit(2)}
  const c=j&&j.hookSpecificOutput&&j.hookSpecificOutput.additionalContext;
  if(typeof c!=="string"){console.error("缺 hookSpecificOutput.additionalContext");process.exit(3)}
  if(j.hookSpecificOutput.hookEventName!=="SessionStart"){console.error("hookEventName 不是 SessionStart");process.exit(4)}
  process.stdout.write(c);
});' 2>&1)" || fail "输出不是合法 JSON 或缺字段：${ctx}"

if [ -z "${ctx:-}" ]; then
  fail "注入文本为空"
else
  printf '%s' "$ctx" | grep -q '要改的' || fail "注入文本里没有「要改的」小节"
  printf '%s' "$ctx" | grep -q '保留'   || fail "注入文本里没有「保留」小节"
  printf '%s' "$ctx" | grep -q '护城河' || fail "注入文本里没有规则表的例句（疑似读到了空文件）"
fi

if [ "$fails" -eq 0 ]; then
  echo "全部通过"
else
  echo "${fails} 项失败" >&2
  exit 1
fi

#!/usr/bin/env bash
# 校验 SessionStart hook：输出必须是合法 JSON；注入文本的结尾与 rules.md 原文逐字一致、限定语块首尾结构完整；含关键词。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RULES_FILE="${SCRIPT_DIR}/../skills/plain-language/rules.md"
fails=0
fail() { echo "FAIL: $1" >&2; fails=$((fails + 1)); }

# 解析注入文本要用 node，接住它的报错要用 mktemp。缺了就直接说清楚，别把「工具没装」误报成「JSON 不合法」
for dep in node mktemp; do
  if ! command -v "$dep" >/dev/null 2>&1; then
    echo "FAIL: 需要 ${dep} 才能校验 hook 的注入内容" >&2
    exit 1
  fi
done

out="$(bash "${SCRIPT_DIR}/session-start" 2>/dev/null)"
if [ -z "$out" ]; then
  fail "session-start 没有输出（应为一行 JSON）"
  echo "1 项失败" >&2
  exit 1
fi

node_err="$(mktemp)"
if ctx="$(printf '%s' "$out" | node -e '
const fs=require("fs");
let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{
  let j;try{j=JSON.parse(s)}catch(e){console.error("JSON 解析失败: "+e.message);process.exit(2)}
  const c=j&&j.hookSpecificOutput&&j.hookSpecificOutput.additionalContext;
  if(typeof c!=="string"){console.error("缺 hookSpecificOutput.additionalContext");process.exit(3)}
  if(j.hookSpecificOutput.hookEventName!=="SessionStart"){console.error("hookEventName 不是 SessionStart");process.exit(4)}
  const rules=fs.readFileSync(process.argv[1],"utf8").replace(/\n+$/,"");
  const i=c.length-rules.length;
  if(i<0||c.slice(i)!==rules){console.error("注入文本的结尾与 rules.md 原文不一致（换行转义可能被改坏）");process.exit(5)}
  if(!c.slice(0,i).endsWith("</EXTREMELY_IMPORTANT>\n\n")){console.error("rules.md 原文前面应是 </EXTREMELY_IMPORTANT> 加一个空行");process.exit(6)}
  process.stdout.write(c);
});' "$RULES_FILE" 2>"$node_err")"; then
  parse_ok=1
else
  parse_ok=0
  fail "注入文本校验失败，node 报错：$(cat "$node_err")"
fi
rm -f "$node_err"

if [ "$parse_ok" -eq 1 ]; then
  if [ -z "$ctx" ]; then
    fail "注入文本为空"
  else
    printf '%s' "$ctx" | grep -q '要改的' || fail "注入文本里没有「要改的」小节"
    printf '%s' "$ctx" | grep -q '保留'   || fail "注入文本里没有「保留」小节"
    printf '%s' "$ctx" | grep -q '护城河' || fail "注入文本里没有规则表的例句（疑似读到了空文件）"
  fi
fi

# polyglot 包装没人测过就等于没护住：run-hook.cmd 的输出必须与直接调用 session-start 一致
wrapped="$(bash "${SCRIPT_DIR}/run-hook.cmd" session-start 2>/dev/null)"
[ "$wrapped" = "$out" ] || fail "run-hook.cmd 的输出与直接调用 session-start 不一致"

if [ "$fails" -eq 0 ]; then
  echo "全部通过"
else
  echo "${fails} 项失败" >&2
  exit 1
fi

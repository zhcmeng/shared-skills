# ── SessionStart 注入 ──────────────────────────────────────────────
# 验的是：输出是合法 JSON；注入文本的结尾与 rules.md 原文逐字一致；限定语块首尾
# 结构完整且正文非空；含关键词；polyglot 的两个分支（bash 与 Windows 上的 cmd
# 批处理）输出都与直接调用 session-start 一致。
# 关键词那几条盯的是 rules.md 的几个部分各还在不在——尤其那张表（正例／反例／原因）：
# 它是整份规则里唯一在生成时起作用的组织方式，整段删掉的话，别的断言照样全过。
# test_home 由入口提供，20 复用同一个。
# watch: plugin/hooks/session-start plugin/hooks/run-hook.cmd plugin/hooks/hooks.json plugin/skills/plain-language/rules.md

out="$(HOME="$test_home" bash "${HOOKS_DIR}/session-start" 2>/dev/null)"
if [ -z "$out" ]; then
  fail "session-start 没有输出（应为一行 JSON）"
  echo "1 项失败" >&2
  exit 1
fi

node_err="$(scratch_file)"
if ctx="$(printf '%s' "$out" | node -e '
const fs=require("fs");
let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{
  let j;try{j=JSON.parse(s)}catch(e){console.error("JSON 解析失败: "+e.message);process.exit(2)}
  const c=j&&j.hookSpecificOutput&&j.hookSpecificOutput.additionalContext;
  if(typeof c!=="string"){console.error("缺 hookSpecificOutput.additionalContext");process.exit(3)}
  if(j.hookSpecificOutput.hookEventName!=="SessionStart"){console.error("hookEventName 不是 SessionStart");process.exit(4)}
  // 两边都先归一化行尾（CRLF → LF）再去尾部空行：行尾差异不该误报，但换行转义被改坏照样要抓到
  const norm = s => s.replace(/\r\n/g,"\n").replace(/\n+$/,"");
  const rawRules = fs.readFileSync(process.argv[1],"utf8");
  const rules = norm(rawRules);
  const cc = norm(c);
  const i = cc.length - rules.length;
  if(i<0||cc.slice(i)!==rules){console.error("注入文本的结尾与 rules.md 原文不一致（换行转义可能被改坏）");process.exit(5)}
  // 限定语块是承重的那部分，只验「结尾一致」抓不到它被整块删掉。这里只断言结构，不复制任何限定语措辞
  const head = cc.slice(0,i);
  if(!head.endsWith("</EXTREMELY_IMPORTANT>\n\n")){console.error("rules.md 原文前面应是 </EXTREMELY_IMPORTANT> 加一个空行");process.exit(6)}
  const body = head.slice(0, head.length - "</EXTREMELY_IMPORTANT>\n\n".length);
  if(!body.startsWith("<EXTREMELY_IMPORTANT>\n")){console.error("注入文本应以 <EXTREMELY_IMPORTANT> 加一个换行开头（限定语块的开始不见了）");process.exit(7)}
  if(body.slice("<EXTREMELY_IMPORTANT>\n".length).trim()===""){console.error("限定语块里没有限定语正文（只剩一对空标签）");process.exit(8)}
  process.stdout.write(c);
});' "$RULES_FILE" 2>"$node_err")"; then
  parse_ok=1
else
  parse_ok=0
  fail "注入文本校验失败，node 报错：$(cat "$node_err")"
fi

if [ "$parse_ok" -eq 1 ]; then
  if [ -z "$ctx" ]; then
    fail "注入文本为空"
  else
    printf '%s' "$ctx" | grep -q '要怎么表述才能让读者明白' || fail "注入文本里没有判据那句（要怎么表述才能让读者明白）"
    printf '%s' "$ctx" | grep -q '反例' || fail "注入文本里没有「反例」一列（表只剩正面一半）"
    printf '%s' "$ctx" | grep -q '照原样写' || fail "注入文本里没有「这些照原样写」小节"
    printf '%s' "$ctx" | grep -q '护城河' || fail "注入文本里没有规则表的例句（疑似读到了空文件）"
  fi
fi

# polyglot 包装没人测过就等于没护住：run-hook.cmd 的输出必须与直接调用 session-start 一致
wrapped="$(HOME="$test_home" bash "${HOOKS_DIR}/run-hook.cmd" session-start 2>/dev/null)"
[ "$wrapped" = "$out" ] || fail "run-hook.cmd 的输出与直接调用 session-start 不一致"

# run-hook.cmd 在 Windows 上的生产路径是 cmd 批处理分支，上面那条只走了 bash 分支。
# 实测：把 REM 注释改回中文，cmd 分支退出 255、输出变成一屏回显垃圾，而本脚本此前照样报「全部通过」。
# 所以这里必须真跑一次 cmd.exe，并且**比对输出而非退出码**——退出码会骗人。
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    if ! command -v cmd.exe >/dev/null 2>&1; then
      fail "在 MSYS/MINGW 环境下找不到 cmd.exe，无法校验批处理分支"
    else
      cmd_bin="cmd.exe"
      command -v timeout >/dev/null 2>&1 && cmd_bin="timeout 20 cmd.exe"
      # 必须在仓库根跑（批处理分支用相对路径 hooks 下的 run-hook.cmd）。
      # MSYS_NO_PATHCONV=1 必需：Git Bash 会把 /c 当路径改写（cygpath -w /c 得到 C:\），
      #   cmd.exe 于是丢掉 /c 开关、进交互模式。
      # < /dev/null 也必需：交互模式下 cmd.exe 会一直等输入（实测 timeout 10 能把它杀掉，rc=124），
      #   接上 /dev/null 它读到 EOF 就正常退出。120 秒是宿主工具的超时值，不是 cmd.exe 的属性。
      # HOME 也必须传进去：cmd.exe 会继承环境变量，bash 分支再把 HOME 传给 session-start，
      # 否则这一跑会往真实用户的 ~/.claude 里同步脚本（实测过，环境变量能穿透 cmd.exe）。
      cmd_out="$(cd "${REPO_ROOT}" && HOME="$test_home" MSYS_NO_PATHCONV=1 $cmd_bin /c "${RUN_HOOK_CMD_WIN} session-start" < /dev/null 2>/dev/null)"
      cmd_rc=$?
      [ "$cmd_rc" -eq 0 ] || fail "cmd.exe 走批处理分支退出码是 ${cmd_rc}（应为 0）"
      [ "$cmd_out" = "$out" ] || fail "cmd.exe 走批处理分支的输出与 session-start 不一致（Windows 上的生产路径已坏）"
    fi
    ;;
  *)
    echo "（非 Windows：跳过 cmd.exe 批处理分支检查。此处的生产路径就是 bash 分支，上面那条冒烟对比已覆盖）"
    ;;
esac

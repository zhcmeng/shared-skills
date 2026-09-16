#!/usr/bin/env bash
# 校验 SessionStart hook：输出必须是合法 JSON；注入文本的结尾与 rules.md 原文逐字一致、限定语块首尾结构完整且正文非空；含关键词；polyglot 的两个分支（bash 与 Windows 上的 cmd 批处理）输出都与直接调用 session-start 一致；statusline/ 下的脚本被同步到配置目录、内容逐字一致、内容相同时不重写、被改坏能修回、CLAUDE_CONFIG_DIR 优先于 HOME；两个状态栏脚本真跑一次，比对输出里的费用/命中率/token/时长，以及缺输入时时长那一截整段消失。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RULES_FILE="${SCRIPT_DIR}/../skills/plain-language/rules.md"
fails=0
fail() { echo "FAIL: $1" >&2; fails=$((fails + 1)); }

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

# 下面每一处调用 session-start 都要把 HOME 换掉：这个 hook 会把 statusline/ 下的脚本
# 同步到配置目录，不换就会写进真实用户的 ~/.claude。校验脚本不该动真东西。
# 后面的同步校验复用同一个临时目录。
test_home="$(mktemp -d)"

out="$(HOME="$test_home" bash "${SCRIPT_DIR}/session-start" 2>/dev/null)"
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
wrapped="$(HOME="$test_home" bash "${SCRIPT_DIR}/run-hook.cmd" session-start 2>/dev/null)"
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
      cmd_out="$(cd "${SCRIPT_DIR}/.." && HOME="$test_home" MSYS_NO_PATHCONV=1 $cmd_bin /c "hooks\run-hook.cmd session-start" < /dev/null 2>/dev/null)"
      cmd_rc=$?
      [ "$cmd_rc" -eq 0 ] || fail "cmd.exe 走批处理分支退出码是 ${cmd_rc}（应为 0）"
      [ "$cmd_out" = "$out" ] || fail "cmd.exe 走批处理分支的输出与 session-start 不一致（Windows 上的生产路径已坏）"
    fi
    ;;
  *)
    echo "（非 Windows：跳过 cmd.exe 批处理分支检查。此处的生产路径就是 bash 分支，上面那条冒烟对比已覆盖）"
    ;;
esac

# ── statusline 脚本同步 ────────────────────────────────────────────
# settings.json 里的 statusLine 命令指向的是配置目录下的固定路径（插件安装目录带版本号，
# 指不得），所以这两个脚本有没有被放到那儿，直接决定状态栏能不能用。
statusline_src="$(cd "${SCRIPT_DIR}/../statusline" 2>/dev/null && pwd)"
test_cfg="${test_home}/.claude"

for f in statusline.py subagent-statusline.py; do
  if [ ! -f "${statusline_src}/${f}" ]; then
    fail "仓库里缺 statusline/${f}（同步的源文件）"
  elif [ ! -f "${test_cfg}/${f}" ]; then
    fail "session-start 没有把 statusline/${f} 同步到配置目录"
  elif ! cmp -s "${statusline_src}/${f}" "${test_cfg}/${f}"; then
    fail "同步到配置目录的 ${f} 与仓库里的不一致"
  fi
done

# 幂等：内容一致时不该重写。把目标的时间戳拨回 2000-01-01 再跑一次，然后拿一个
# 2000-01-02 的参照文件去比——没被重写就还是 2000-01-01（比参照旧），被重写了就是
# 「现在」（比参照新）。用参照文件而不是拿源文件的 mtime 比，是因为源文件的 mtime
# 是 checkout 时间，刚克隆完就跑校验时它会和「现在」撞在同一秒，判据就不成立了。
if [ -f "${test_cfg}/statusline.py" ]; then
  touch -t 200001010000 "${test_cfg}/statusline.py"
  idem_ref="$(mktemp)"
  touch -t 200001020000 "$idem_ref"
  HOME="$test_home" bash "${SCRIPT_DIR}/session-start" >/dev/null 2>&1
  [ "${test_cfg}/statusline.py" -ot "$idem_ref" ] \
    || fail "内容一致时仍重写了 statusline.py（同步不幂等）"
  rm -f "$idem_ref"
fi

# 目标被改坏要能修回，否则「仓库是唯一真相」这句话不成立
if [ -f "${test_cfg}/statusline.py" ]; then
  printf '\n# 校验脚本塞的杂质\n' >> "${test_cfg}/statusline.py"
  HOME="$test_home" bash "${SCRIPT_DIR}/session-start" >/dev/null 2>&1
  cmp -s "${statusline_src}/statusline.py" "${test_cfg}/statusline.py" \
    || fail "目标被改坏后没能同步回仓库版本"
fi

# 设了 CLAUDE_CONFIG_DIR 就该写到那儿，而不是继续写 $HOME/.claude
cfg_alt="$(mktemp -d)"
home_alt="$(mktemp -d)"
CLAUDE_CONFIG_DIR="$cfg_alt" HOME="$home_alt" bash "${SCRIPT_DIR}/session-start" >/dev/null 2>&1
[ -f "${cfg_alt}/statusline.py" ] || fail "设了 CLAUDE_CONFIG_DIR 时没有同步到该目录"
if [ -d "${home_alt}/.claude" ]; then
  fail "设了 CLAUDE_CONFIG_DIR 时仍往 HOME/.claude 写了"
fi
rm -rf "$cfg_alt" "$home_alt"
rm -rf "$test_home"

# ── statusline 脚本冒烟 ────────────────────────────────────────────
# 这两个脚本坏了不报错，只会让状态栏空白或少一截，所以要真跑一次、比对输出内容。
#
# 记录是现造的，不依赖本机真实会话。时间戳写死成周三上午（北京时间），落在高峰段，
# 这样「峰」字在不在也可断言；写死而不是取「现在」，是为了让判定与跑的时刻无关。
#
# 路径用「cd 进临时目录 + JSON 里放相对路径」，不传绝对路径：MSYS 只改写**命令行参数**
# 里的 POSIX 路径，JSON 是走 stdin 的，里面的 /tmp/... 原样送达原生 Python，打不开文件。
# 这个坑不报错——脚本读不到记录就静默不输出，测试会以一种看不懂的方式挂掉（实测过）。
# 相对路径两边都不改写，各平台一致。
#
# 断言一律写在 $( ) 外面：$( ) 起子 shell，在里面调 fail 只会加在子 shell 的副本上，
# 计数传不出来，失败会被吞掉。
if ! command -v python >/dev/null 2>&1; then
  echo "提示：没找到 python，跳过状态栏脚本冒烟测试（状态栏本身也得有 python 才跑得起来）"
else
  # 主状态栏的测试目录里不能有 subagents/：statusline.py 会把子代理记录一并计入
  # 本会话开销，两份同内容的记录叠起来总 token 直接翻倍。
  smoke_main="$(mktemp -d)"
  smoke_sub="$(mktemp -d)"
  mkdir -p "${smoke_sub}/sess/subagents"
  cat > "${smoke_main}/sess.jsonl" <<'SYNTHJSONL'
{"timestamp":"2026-09-16T02:00:00.000Z","message":{"model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
SYNTHJSONL
  cp "${smoke_main}/sess.jsonl" "${smoke_sub}/sess.jsonl"
  # 记录文件名必须与下面任务行的 id 对上：脚本是按 agent-<id>.jsonl 去找每个子代理的记录的
  for id in run frozen zero nostart; do
    cp "${smoke_main}/sess.jsonl" "${smoke_sub}/sess/subagents/agent-${id}.jsonl"
  done

  main_out="$(cd "$smoke_main" && printf '{"transcript_path":"sess.jsonl","cost":{"total_duration_ms":7500000}}' \
    | python "${statusline_src}/statusline.py" 2>/dev/null)"
  for frag in '缓存命中 90.0%' '总token 1.05M' '(峰)' '2h05m'; do
    case "$main_out" in
      *"$frag"*) ;;
      *) fail "主状态栏输出里没有「${frag}」（实际：${main_out}）" ;;
    esac
  done

  # 取不到 cost.total_duration_ms 时这一截应当整段消失，而不是编个数顶上。
  # 拿「正常输出掐掉时长后缀」当基准，比另写一套断言更严。
  degrade_out="$(cd "$smoke_main" && printf '{"transcript_path":"sess.jsonl"}' \
    | python "${statusline_src}/statusline.py" 2>/dev/null)"
  [ "$degrade_out" = "${main_out% · 2h05m}" ] \
    || fail "主状态栏缺 cost 时的降级不对（实际：${degrade_out}）"

  # 三个子代理任务，分别压住时长的三条分支：
  #   running   —— 起点定在 120 秒前，落在 2m 这一档（到 179 秒都还是 2m，跑慢点不会跨档）。
  #                这一条依赖当前时刻，所以档位留了宽裕。
  #   completed —— 起点写死成「末条记录前 300 秒」= 5m，全程用固定时刻算，与跑的时刻无关，
  #                所以能咬死确切数字。它压的是最容易改坏的那条：已结束的代理必须停在末条
  #                记录上，不能跟着「现在」一直涨。真要是涨了，这条断言就会挂。
  #   startTime=0 —— 0 在这套数据里是「未设置」的哨兵值（不是 1970 年），顺着算会得出
  #                「20712d01h」这种荒谬结果。
  #   没有 startTime —— 起点压根取不到，同样不显示。
  #                后两条要断言的是「时长那一截不存在」，没有比钉死整行更严的写法了。
  start_ms=$(( $(date +%s) * 1000 - 120000 ))
  sub_out="$(cd "$smoke_sub" && printf '{"columns":160,"transcript_path":"sess.jsonl","tasks":[{"id":"run","description":"冒烟","status":"running","startTime":%s},{"id":"frozen","description":"冻住","status":"completed","startTime":1789523700000},{"id":"zero","description":"零起点","status":"running","startTime":0},{"id":"nostart","description":"无起点","status":"running"}]}' "$start_ms" \
    | python "${statusline_src}/subagent-statusline.py" 2>/dev/null)"
  for frag in '冒烟' '缓存命中 90.0%' '总token 1.05M' '(峰)' '2m' '5m'; do
    case "$sub_out" in
      *"$frag"*) ;;
      *) fail "子代理状态栏输出里没有「${frag}」（实际：${sub_out}）" ;;
    esac
  done
  line_of() { printf '%s\n' "$sub_out" | grep -F "\"id\": \"$1\""; }
  [ "$(line_of frozen)" = '{"id": "frozen", "content": "冻住  ¥0.64(峰) · 缓存命中 90.0% · 总token 1.05M · 5m"}' ] \
    || fail "已结束的子代理时长没停在末条记录（实际：$(line_of frozen)）"
  [ "$(line_of zero)" = '{"id": "zero", "content": "零起点  ¥0.64(峰) · 缓存命中 90.0% · 总token 1.05M"}' ] \
    || fail "起点为 0 的子代理不该显示时长（实际：$(line_of zero)）"
  [ "$(line_of nostart)" = '{"id": "nostart", "content": "无起点  ¥0.64(峰) · 缓存命中 90.0% · 总token 1.05M"}' ]     || fail "取不到起点的子代理不该显示时长（实际：$(line_of nostart)）"

  # ── 同一条回复被拆成多条记录时不能重复累加 ──
  # Claude Code 把一条回复的思考、正文、工具调用各写成一条记录，每条都带同一份完整
  # usage 和同一个 message.id。照着行数累加会把一次调用算成好几遍（真实会话实测被
  # 放大 2.6~4.2 倍）。下面把一次调用写成三条，另加一次独立调用（id 不同）作对照：
  # 合计只该按两次调用计 —— 总 token 2.10M、费用 ¥1.27、命中率仍 90.0%。
  smoke_dup="$(mktemp -d)"
  smoke_dsub="$(mktemp -d)"
  mkdir -p "${smoke_dsub}/sess/subagents"
  cat > "${smoke_dup}/dup.jsonl" <<'SYNTHJSONL'
{"timestamp":"2026-09-16T02:00:00.000Z","message":{"id":"msg_a","stop_reason":"tool_use","model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
{"timestamp":"2026-09-16T02:00:00.200Z","message":{"id":"msg_a","stop_reason":"tool_use","model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
{"timestamp":"2026-09-16T02:00:00.400Z","message":{"id":"msg_a","stop_reason":"tool_use","model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
{"timestamp":"2026-09-16T02:05:00.000Z","message":{"id":"msg_b","stop_reason":"end_turn","model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
SYNTHJSONL
  cp "${smoke_dup}/dup.jsonl" "${smoke_dsub}/sess/subagents/agent-dup.jsonl"

  dup_main="$(cd "$smoke_dup" && printf '{"transcript_path":"dup.jsonl"}' \
    | python "${statusline_src}/statusline.py" 2>/dev/null)"
  for frag in '¥1.27(峰)' '缓存命中 90.0%' '总token 2.10M'; do
    case "$dup_main" in
      *"$frag"*) ;;
      *) fail "主状态栏把同一个 message.id 的多条记录重复累加了（没有「${frag}」，实际：${dup_main}）" ;;
    esac
  done

  # startTime 定在末条记录前 300 秒，时长才与跑的时刻无关，能写死成 5m
  dup_sub="$(cd "$smoke_dsub" && printf '{"columns":160,"transcript_path":"sess.jsonl","tasks":[{"id":"dup","description":"重复","status":"completed","startTime":1789524000000}]}' \
    | python "${statusline_src}/subagent-statusline.py" 2>/dev/null)"
  [ "$dup_sub" = '{"id": "dup", "content": "重复  ¥1.27(峰) · 缓存命中 90.0% · 总token 2.10M · 5m"}' ] \
    || fail "子代理状态栏把同一个 message.id 的多条记录重复累加了（实际：${dup_sub}）"
  rm -rf "$smoke_dup" "$smoke_dsub"

  rm -rf "$smoke_main" "$smoke_sub"
fi

# ── 通知 hook ──────────────────────────────────────────────────────
# 判定的全部内容就一条：事件来自的会话，是不是你最后打过字的那个。所以这里把
# 「标记文件里写的是谁」和「事件来自谁」两个变量穷举一遍，看决定是弹还是不弹。
#
# 用一个假的 PowerShell，不真弹：真弹既打扰人，也没法断言弹了什么。假的把收到的参数
# 记进日志，断言的就是「真实运行时会交给 PowerShell 什么」。CLAUDE_NOTIFY_PS 是为此
# 留的口子，顺带也让换别的 PowerShell 成为可能。
notify_dir="$(mktemp -d)"
notify_cfg="${notify_dir}/cfg"
notify_log="${notify_dir}/log"
notify_stub="${notify_dir}/ps-stub"
mkdir -p "$notify_cfg"
: > "$notify_log"

cat > "$notify_stub" <<'STUB'
#!/usr/bin/env bash
# 假的 PowerShell：把参数原样记进日志，什么都不弹
{ printf 'CALL'; for a in "$@"; do printf ' [%s]' "$a"; done; printf '\n'; } >> "$STUB_LOG"
exit 0
STUB
chmod +x "$notify_stub"

# 标记文件名是 hooks/notify 与校验脚本之间的约定，改名两边都要改
MARK_NAME=".notify-current-session"
mark() { printf '%s' "$1" > "${notify_cfg}/${MARK_NAME}"; }
notify() {
  printf '%s' "$1" | STUB_LOG="$notify_log" CLAUDE_CONFIG_DIR="$notify_cfg" \
    CLAUDE_NOTIFY_PS="$notify_stub" bash "${SCRIPT_DIR}/notify" 2>/dev/null
  return 0
}
calls() { cat "$notify_log" 2>/dev/null; }
reset_calls() { : > "$notify_log"; }
# 断言「这一跑弹了，且弹的是这些内容」。片段按顺序都得出现，避免只对上事件名就算过
expect_toast() {
  local desc="$1"; shift
  local line; line="$(tail -n 1 "$notify_log" 2>/dev/null)"
  case "$line" in
    *"[-Mode] [toast]"*) ;;
    *) fail "${desc}：没有弹通知（实际：${line:-无调用}）"; return ;;
  esac
  local frag
  for frag in "$@"; do
    case "$line" in
      *"$frag"*) ;;
      *) fail "${desc}：通知里没有「${frag}」（实际：${line}）" ;;
    esac
  done
}
expect_silent() {
  local desc="$1"
  [ -z "$(calls)" ] || fail "${desc}：不该弹却弹了（实际：$(calls)）"
}

# 别的会话答完 → 弹。正文用 last_assistant_message，不用去翻记录
reset_calls; mark "session-other"
notify '{"hook_event_name":"Stop","session_id":"session-a","cwd":"C:\\work\\demo","last_assistant_message":"把 hook 加好了"}'
expect_toast "别的会话答完" "[-Tag] [sessiona]" "[-Title] [Claude Code · demo]" "[-Body] [答完了：把 hook 加好了]"

# 当前会话答完 → 不弹。这是整个功能的中心：你正看着它，不需要提醒
reset_calls; mark "session-a"
notify '{"hook_event_name":"Stop","session_id":"session-a","cwd":"C:\\work\\demo","last_assistant_message":"把 hook 加好了"}'
expect_silent "当前会话答完"

# 从来没有标记过（非交互会话，比如 claude -p）：无从判断你在哪，宁可弹
reset_calls; rm -f "${notify_cfg}/${MARK_NAME}"
notify '{"hook_event_name":"Stop","session_id":"session-a","cwd":"C:\\work\\demo","last_assistant_message":"跑完了"}'
expect_toast "没有标记文件时答完"

# 正文取不到时只留前缀，不该出现「答完了：」后面空一截还带着冒号
reset_calls; mark "session-other"
notify '{"hook_event_name":"Stop","session_id":"session-a","cwd":"C:\\work\\demo"}'
expect_toast "答完但没有正文" "[-Body] [答完了]"

# 提醒只有两行位置，长正文要截断，且按字符截而不是按字节（中文一个字三字节，
# 按字节截会把最后一个字劈成半个，显示成乱码）
reset_calls; mark "session-other"
long="$(printf '一%.0s' $(seq 1 200))"
notify "{\"hook_event_name\":\"Stop\",\"session_id\":\"session-a\",\"cwd\":\"C:\\\\work\\\\demo\",\"last_assistant_message\":\"${long}\"}"
case "$(tail -n 1 "$notify_log")" in
  *"…"*) ;;
  *) fail "超长正文没有被截断" ;;
esac
# 截断要按字符数，不是字节数。中文一个字三字节，按字节截会把最后一个字劈成半个。
# 数一数留下几个「一」最直接：正好 90 个才对，多一个少一个都说明截错了单位。
ones="$(tail -n 1 "$notify_log" | grep -o '一' | wc -l | tr -d ' ')"
[ "$ones" = "90" ] || fail "超长中文正文截断的字符数不对（应留 90 个「一」，实际 ${ones} 个）"

# 正文里的换行和制表符会把通知版面撑坏，要压成一行
reset_calls; mark "session-other"
notify '{"hook_event_name":"Stop","session_id":"session-a","cwd":"C:\\work\\demo","last_assistant_message":"第一行\n第二行\t带制表符"}'
expect_toast "正文压成一行" "[-Body] [答完了：第一行 第二行 带制表符]"

# 你敲字了 → 记下「当前会话是这个」，并撤掉这个会话遗留的提醒。
# 撤这一步不能省：常驻通知不会自己消失，你答完那道选择题，屏幕上还挂着「等你选」。
reset_calls; mark "session-other"
notify '{"hook_event_name":"UserPromptSubmit","session_id":"session-a","source":"user","cwd":"C:\\work\\demo"}'
[ "$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-a" ] \
  || fail "UserPromptSubmit 没有把标记改成当前会话（实际：$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)）"
case "$(calls)" in
  *"[-Mode] [clear]"*"[-Tag] [sessiona]"*) ;;
  *) fail "回到会话后没有撤掉它的旧提醒（实际：${calls:-无调用}）" ;;
esac

# /loop 唤醒、定时唤醒、非交互调用走的是同一个事件，但那些时刻你并不在，
# 不该把「当前会话」抢过去 —— 抢了的话，那个会话之后出事就不再提醒你了
for src in loop_wakeup schedule_wakeup poll_event sdk system; do
  reset_calls; mark "session-other"
  notify "{\"hook_event_name\":\"UserPromptSubmit\",\"session_id\":\"session-a\",\"source\":\"${src}\"}"
  [ "$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-other" ] \
    || fail "source=${src} 时不该改写当前会话标记"
  expect_silent "source=${src} 的 UserPromptSubmit"
done

# 弹选择题：正文是问题原文，这样你不切窗口也能先看一眼问的是什么
reset_calls; mark "session-other"
notify '{"hook_event_name":"PreToolUse","session_id":"session-a","tool_name":"AskUserQuestion","cwd":"C:\\work\\demo","tool_input":{"questions":[{"question":"要放进插件还是只在本机配？"}]}}'
expect_toast "别的会话弹选择题" "[-Body] [等你选：要放进插件还是只在本机配？]"

# 同一个事件名也被别的工具用着，只认 AskUserQuestion
reset_calls; mark "session-other"
notify '{"hook_event_name":"PreToolUse","session_id":"session-a","tool_name":"Bash","cwd":"C:\\work\\demo","tool_input":{"command":"ls"}}'
expect_silent "PreToolUse 但不是 AskUserQuestion"

# 要你批准：只认 permission_prompt。空闲提醒（idle_prompt）是你明确不要的那条，
# 它和你答完一轮是同一件事，弹两遍纯属吵
reset_calls; mark "session-other"
notify '{"hook_event_name":"Notification","session_id":"session-a","notification_type":"permission_prompt","cwd":"C:\\work\\demo","message":"Claude needs your permission"}'
expect_toast "别的会话要权限" "[-Body] [要批准：Claude needs your permission]"

reset_calls; mark "session-other"
notify '{"hook_event_name":"Notification","session_id":"session-a","notification_type":"idle_prompt","cwd":"C:\\work\\demo","message":"Claude is waiting for your input"}'
expect_silent "空闲等待提醒（明确不要）"

# 坏输入不该让 hook 挂掉。hook 挂掉比通知弹不出来严重得多
reset_calls; mark "session-other"
notify '这不是 JSON'
[ $? -eq 0 ] || fail "非 JSON 输入没有正常退出"
expect_silent "非 JSON 输入"
notify ''
expect_silent "空输入"
notify '{"hook_event_name":"Stop","cwd":"C:\\work\\demo"}'
expect_silent "缺 session_id"
notify '{"hook_event_name":"没听说过的事件","session_id":"session-a"}'
expect_silent "不认识的 hook 事件"

# 标记文件跟着 CLAUDE_CONFIG_DIR 走，而不是写死 $HOME/.claude
reset_calls
alt_cfg="$(mktemp -d)"; alt_home="$(mktemp -d)"
printf '%s' "session-other" | STUB_LOG="$notify_log" CLAUDE_CONFIG_DIR="$alt_cfg" HOME="$alt_home" \
  CLAUDE_NOTIFY_PS="$notify_stub" bash "${SCRIPT_DIR}/notify" >/dev/null 2>&1 <<< '{"hook_event_name":"UserPromptSubmit","session_id":"session-a","source":"user"}'
[ "$(cat "${alt_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-a" ] \
  || fail "标记文件没有写在 CLAUDE_CONFIG_DIR 下"
[ -f "${alt_home}/.claude/${MARK_NAME}" ] && fail "设了 CLAUDE_CONFIG_DIR 时仍往 HOME/.claude 写了标记"
rm -rf "$alt_cfg" "$alt_home"

# run-hook.cmd 的 bash 分支要能把 notify 透传进去
wrapped_notify="$(STUB_LOG="$notify_log" CLAUDE_CONFIG_DIR="$notify_cfg" CLAUDE_NOTIFY_PS="$notify_stub" \
  bash "${SCRIPT_DIR}/run-hook.cmd" notify <<< '{"hook_event_name":"不认识的","session_id":"x"}' 2>/dev/null)"
[ $? -eq 0 ] || fail "run-hook.cmd 透传 notify 时退出码非 0"

# ── 通知渲染层 ────────────────────────────────────────────────────
# notify.ps1 的源码里带中文注释，Windows PowerShell 5.1 只在文件带 UTF-8 BOM 时才按
# UTF-8 解析；没有 BOM 它按 GBK 解，中文注释的字节错位还会连带吞掉换行，报出来的行号
# 都对不上（本机实测）。失败方式是静默的：脚本解析不了，通知就再也不弹，会话照开。
# 所以既查 BOM，也真跑一次让 PowerShell 解析全文、顺便验证转义和中文输出。
ps1="${SCRIPT_DIR}/notify.ps1"
if [ ! -f "$ps1" ]; then
  fail "缺 hooks/notify.ps1"
else
  [ "$(head -c 3 "$ps1" | od -An -tx1 | tr -d ' \n')" = "efbbbf" ] \
    || fail "notify.ps1 缺 UTF-8 BOM（PowerShell 5.1 会按 GBK 解析，中文注释会让脚本解析失败，且不报错）"
fi

if ! command -v powershell.exe >/dev/null 2>&1; then
  echo "提示：没找到 powershell.exe，跳过通知渲染层的解析检查（这一项本来就只在 Windows 上有意义）"
elif [ -f "$ps1" ]; then
  ps_path="$ps1"
  command -v cygpath >/dev/null 2>&1 && ps_path="$(cygpath -w "$ps1")"
  ps_out="$(powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ps_path" \
    -Mode toast -DryRun -Tag selfcheck -Title '标题 & 尖括号' -Body '正文 <夹>' 2>&1)"
  case "$ps_out" in
    *"<text>标题 &amp; 尖括号</text>"*) ;;
    *) fail "notify.ps1 没生成预期的标题（中文或 XML 转义有问题，实际：${ps_out}）" ;;
  esac
  case "$ps_out" in
    *"<text>正文 &lt;夹&gt;</text>"*) ;;
    *) fail "notify.ps1 没有转义正文里的尖括号（实际：${ps_out}）" ;;
  esac
  case "$ps_out" in
    *'scenario="reminder"'*) ;;
    *) fail "notify.ps1 没有用常驻那一档（通知会自己消失，你就可能错过）" ;;
  esac
fi

# hooks.json 的接线：四条通知 hook 少一条，对应那个时刻就再也不提醒，而且不报错。
# 用 node 解析而不是 grep —— JSON 换个缩进、换个字段顺序，grep 就会骗人。
hook_err="$(node -e '
const fs = require("fs");
const j = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const errs = [];
const hooks = j.hooks || {};
if (!hooks.SessionStart) errs.push("SessionStart 那条被改没了");
const events = ["UserPromptSubmit", "Stop", "PreToolUse", "Notification"];
for (const ev of events) {
  const groups = hooks[ev];
  if (!Array.isArray(groups) || groups.length === 0) { errs.push("缺 " + ev); continue; }
  let hit = null;
  for (const g of groups) for (const h of (g.hooks || [])) {
    if (/run-hook\.cmd"\s+notify/.test(h.command || "")) hit = h;
  }
  if (!hit) { errs.push(ev + " 没有指向 run-hook.cmd notify"); continue; }
  if (hit.async !== true) errs.push(ev + " 没挂后台（async 不是 true），会挡住操作");
}
let pre = false;
for (const g of (hooks.PreToolUse || [])) if (g.matcher === "AskUserQuestion") pre = true;
if (!pre) errs.push("PreToolUse 没有匹配 AskUserQuestion（弹选择题那一刻接不住）");
if (errs.length) { console.error(errs.join("；")); process.exit(1); }
' "${SCRIPT_DIR}/hooks.json" 2>&1)" || fail "hooks.json 接线不对：${hook_err}"

# Windows 上的生产路径是 cmd 批处理分支。notify 还得靠标准输入拿到事件数据，
# 标准输入能不能穿过 cmd.exe 到 bash，只有真跑一次才知道。
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    if command -v cmd.exe >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1; then
      reset_calls; mark "session-other"
      (cd "${SCRIPT_DIR}/.." && STUB_LOG="$notify_log" CLAUDE_CONFIG_DIR="$notify_cfg" \
        CLAUDE_NOTIFY_PS="$notify_stub" MSYS_NO_PATHCONV=1 timeout 20 cmd.exe /c "hooks\run-hook.cmd notify" \
        <<< '{"hook_event_name":"Stop","session_id":"session-cmd","cwd":"C:\\work\\demo","last_assistant_message":"走批处理分支"}' 2>/dev/null)
      expect_toast "cmd.exe 批处理分支" "[-Tag] [sessioncmd]" "[-Body] [答完了：走批处理分支]"
    fi
    ;;
esac

rm -rf "$notify_dir"

if [ "$fails" -eq 0 ]; then
  echo "全部通过"
else
  echo "${fails} 项失败" >&2
  exit 1
fi

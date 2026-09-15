#!/usr/bin/env bash
# 校验 SessionStart hook：输出必须是合法 JSON；注入文本的结尾与 rules.md 原文逐字一致、限定语块首尾结构完整且正文非空；含关键词；polyglot 的两个分支（bash 与 Windows 上的 cmd 批处理）输出都与直接调用 session-start 一致；statusline/ 下的脚本被同步到配置目录、内容逐字一致、内容相同时不重写、被改坏能修回、CLAUDE_CONFIG_DIR 优先于 HOME。
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
statusline_src="${SCRIPT_DIR}/../statusline"
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

if [ "$fails" -eq 0 ]; then
  echo "全部通过"
else
  echo "${fails} 项失败" >&2
  exit 1
fi

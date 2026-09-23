# ── 通知判定 ───────────────────────────────────────────────────────
# 判定的全部内容就一条：这条提醒对应的会话，是不是你眼睛正看着的那个。判据有两个，
# 按可信度排：前台窗口标题（说了算），标记文件（窗口答不出来时才轮到它）。这里把两个
# 判据各自写的是谁穷举一遍，看决定是弹还是不弹。
#
# 用一个假的 PowerShell，不真弹：真弹既打扰人，也没法断言弹了什么。假的把收到的参数
# 记进日志，断言的就是「真实运行时会交给 PowerShell 什么」。CLAUDE_NOTIFY_PS 是为此
# 留的口子，顺带也让换别的 PowerShell 成为可能。
notify_dir="$(scratch_dir)"
notify_cfg="${notify_dir}/cfg"
notify_log="${notify_dir}/log"
notify_stub="${notify_dir}/ps-stub"
mkdir -p "$notify_cfg"
: > "$notify_log"

cat > "$notify_stub" <<'STUB'
#!/usr/bin/env bash
# 假的 PowerShell。focused 模式是一次「问」、不是一次「做」，不进日志 —— 日志只记
# 弹和撤，断言才好写。回答由 STUB_FOCUSED 给：yes / no / 空（空 = 标题读不到）
case " $* " in
  *" -Mode focused "*)
    [ -n "${STUB_FOCUSED:-}" ] && printf '%s' "$STUB_FOCUSED"
    exit 0 ;;
esac
# 其余：把参数原样记进日志，什么都不弹
{ printf 'CALL'; for a in "$@"; do printf ' [%s]' "$a"; done; printf '\n'; } >> "$STUB_LOG"
exit 0
STUB
chmod +x "$notify_stub"

# 事件 JSON 一律用 printf 拼，不在源码里手写转义：源码里写的双反斜杠会被中转链路
# 削成单个，JSON 随之非法，而 notify 碰到坏 JSON 是静默退出的——测试会以「一条都没弹」
# 的形式挂掉，真正的原因看不出来（本仓库栽过一次）。反斜杠同理，用 awk 现造一个。
# 这几个拼装器不做转义，只喂下面这些固定数据，别拿它拼带引号的内容。
bs="$(awk 'BEGIN{printf "%c",92}')"
win_cwd="C:${bs}${bs}work${bs}${bs}demo"
ev_stop()  { printf '{"hook_event_name":"Stop","session_id":"%s","cwd":"%s","last_assistant_message":"%s"}' "$1" "$2" "$3"; }
ev_ask()   { printf '{"hook_event_name":"PreToolUse","session_id":"%s","tool_name":"AskUserQuestion","cwd":"%s","tool_input":{"questions":[{"question":"%s"}]}}' "$1" "$2" "$3"; }
ev_tool()  { printf '{"hook_event_name":"PreToolUse","session_id":"%s","tool_name":"%s","cwd":"%s","tool_input":{"command":"ls"}}' "$1" "$2" "$3"; }
ev_prompt(){ printf '{"hook_event_name":"UserPromptSubmit","session_id":"%s","source":"%s","cwd":"%s"}' "$1" "$2" "$3"; }
# 真实形状：payload 里根本没有 source 字段（本机抓包确认），但带提示词
ev_prompt_txt(){ printf '{"hook_event_name":"UserPromptSubmit","session_id":"%s","cwd":"%s","prompt":"%s"}' "$1" "$2" "$3"; }
ev_note()  { printf '{"hook_event_name":"Notification","session_id":"%s","notification_type":"%s","cwd":"%s","message":"%s"}' "$1" "$2" "$3" "$4"; }

# 标记文件名是 hooks/notify 与校验脚本之间的约定，改名两边都要改
MARK_NAME=".notify-current-session"
mark() { printf '%s' "$1" > "${notify_cfg}/${MARK_NAME}"; }
notify() {
  printf '%s' "$1" | STUB_LOG="$notify_log" STUB_FOCUSED="${STUB_FOCUSED:-}" \
    CLAUDE_CONFIG_DIR="$notify_cfg" CLAUDE_NOTIFY_PS="$notify_stub" \
    bash "${HOOKS_DIR}/notify" 2>/dev/null
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

# 别的会话答完 → 弹。正文用 last_assistant_message，不用去翻记录。
# 这条没给转录路径，标题就只剩项目名一段，项目名取 cwd 末段；
# 反斜杠形式的 cwd 顺带在这里被压住。
reset_calls; mark "session-other"
notify "$(ev_stop session-a "$win_cwd" "把 hook 加好了")"
expect_toast "别的会话答完" "[-Tag] [sessiona]" "[-Title] [demo]" "[-Body] [答完了：把 hook 加好了]"

# ── 会话名从哪来 ─────────────────────────────────────────────────────
# 标题写成「项目名 · 会话名」，缺哪段少哪段。会话名有三种来源，取用顺序
# 不是我定的，是从 Claude Code 自己那里挖出来的（它显示会话名用的是
# agentName 优先于 customTitle 优先于 aiTitle）。跟着它走，弹窗上的名字才和别处一致。
#
# 三种记录各占一行 JSON，追加在转录里；同一种记录随会话反复重写，所以取最后一条。
tr_dir="$(scratch_dir)"
tr_file="${tr_dir}/session.jsonl"
put() { printf '%s\n' "$1" >> "$tr_file"; }

# 带转录路径的 Stop 事件。会话名要从转录里读，所以路径得给进去
ev_stop_tr(){ printf '{"hook_event_name":"Stop","session_id":"%s","cwd":"%s","transcript_path":"%s","last_assistant_message":"%s"}' "$1" "$2" "$3" "$4"; }

# 自动生成的标题
reset_calls; : > "$tr_file"; put '{"type":"ai-title","aiTitle":"自动生成的标题"}'
mark "session-other"
notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_toast "会话名取自动生成的标题" "[-Title] [demo · 自动生成的标题]"

# 同一种记录写了多条 → 取最后一条（会话过程中标题会反复重写）
reset_calls; : > "$tr_file"
put '{"type":"ai-title","aiTitle":"旧标题"}'
put '{"type":"ai-title","aiTitle":"新标题"}'
mark "session-other"
notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_toast "同名记录取最后一条" "[-Title] [demo · 新标题]"

# 三种记录同时在 → 按优先级取，不是按谁写在最后。这里故意把优先级最高的写在最前面、
# 把自动标题写在最后：按「取最后一条」实现会得到「自动生成的」，正好被这条挡住
reset_calls; : > "$tr_file"
put '{"type":"agent-name","agentName":"优先级最高的"}'
put '{"type":"custom-title","customTitle":"改名记录"}'
put '{"type":"ai-title","aiTitle":"自动生成的"}'
mark "session-other"
notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_toast "三种记录同时在时的优先级" "[-Title] [demo · 优先级最高的]"

# 少了最高那档 → 落到 /rename 改的名上，仍然赢过自动标题
reset_calls; : > "$tr_file"
put '{"type":"ai-title","aiTitle":"自动生成的"}'
put '{"type":"custom-title","customTitle":"改名记录"}'
mark "session-other"
notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_toast "改名优先于自动标题" "[-Title] [demo · 改名记录]"

# 转录里一条标题记录都没有 → 回落到项目目录名，标题只剩两段
reset_calls; : > "$tr_file"
mark "session-other"
notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_toast "转录里没有标题记录" "[-Title] [demo]"

# 转录文件根本不存在（会话刚开始、路径写错）→ 同样回落，不报错也不留空标题
reset_calls
notify "$(ev_stop_tr session-a "$win_cwd" "${tr_dir}/不存在.jsonl" "跑完了")"
expect_toast "转录文件不存在" "[-Title] [demo]"

# 标题字段是空的 → 当作没取到，别在标题里留一截孤零零的分隔点
reset_calls; : > "$tr_file"; put '{"type":"ai-title","aiTitle":""}'
mark "session-other"
notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_toast "标题字段为空" "[-Title] [demo]"

# 项目名和会话名都取不到（工作目录是空的，转录也没有）→ 退回应用名，不让标题行空着
reset_calls; mark "session-other"
notify "$(ev_stop session-a "" "跑完了")"
expect_toast "项目和会话名都没有时退回应用名" "[-Title] [Claude Code]"

# 转录会很大，只回看末尾一段。标题记录在近处要能取到，而且不能被窗口开头那半行
# 断掉的 JSON 带偏——窗口按字节切，首行几乎注定是断的
reset_calls; : > "$tr_file"
put '{"type":"ai-title","aiTitle":"远处的旧标题"}'
put "{\"type\":\"assistant\",\"message\":\"$(head -c 400000 /dev/zero | tr '\0' 'x')\"}"
put '{"type":"ai-title","aiTitle":"近处的新标题"}'
mark "session-other"
notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_toast "标题记录落在末尾窗口内" "[-Title] [demo · 近处的新标题]"

# Windows 上 Claude Code 给的是反斜杠路径，得能读。路径本身要先转义成合法 JSON，
# 否则 notify 拿到坏 JSON 会静默退出，断言只会以「没弹」的形式挂掉，看不出真原因
if command -v cygpath >/dev/null 2>&1; then
  reset_calls; : > "$tr_file"; put '{"type":"ai-title","aiTitle":"反斜杠路径"}'
  tr_win="$(cygpath -w "$tr_file")"
  mark "session-other"
  # 模式那侧的 $bs 必须加引号。不加的话 bash 会把模式里的反斜杠当成转义符，替换变成
  # 空操作，路径原样进 JSON —— 成了非法转义，notify 收到坏 JSON 静默退出（本仓库栽过）
  notify "$(ev_stop_tr session-a "$win_cwd" "${tr_win//"$bs"/"$bs$bs"}" "跑完了")"
  expect_toast "反斜杠形式的转录路径" "[-Title] [demo · 反斜杠路径]"
fi

# ── 你眼睛看着哪个会话 ───────────────────────────────────────────────
# 标记记的是「你最后在哪儿敲过字」，不是「你现在看着哪儿」。这两件事分家时两个方向都会错：
#   · 你在 A 敲完就切到 B，A 成了「后台」，标记还说它是当前会话 —— 它一答完就弹，可你正看着它；
#   · 你停在 claude agents 总览列表上，谁都不算当前，标记却还压着最后打字的那个 —— 它不弹，
#     可你根本没在看它。
# 所以判据换成了前台窗口标题：窗口说「是」就压、说「不是」就弹，标记退到后面 —— 只有窗口
# 答不出来（会话还没名字、前台窗口读不到、PowerShell 起不来）才轮到它。
#
# 窗口标题里带着会话名（终端标签上显示的就是它），这是唯一能拿到「你在看哪个会话」的
# 地方 —— Claude Code 不把焦点告诉 hook。
# 窗口标题里要拿会话名去比，所以这几条都得用「有名字的会话」来验：转录里放一条标题记录
reset_calls; : > "$tr_file"; put '{"type":"ai-title","aiTitle":"演示会话"}'
mark "session-other"
STUB_FOCUSED=yes notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_silent "标记不是你，但你正看着它"

# 前台窗口不是它（在看别的会话、或干脆不在终端里）→ 照弹，提醒才有意义
reset_calls; mark "session-other"
STUB_FOCUSED=no notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_toast "你看着别处时照弹" "[-Body] [答完了：跑完了]"

# 读不到窗口标题（别的终端程序、拿不到前台窗口）→ 退回标记那一套，不能因为问不到就不提醒
reset_calls; mark "session-other"
STUB_FOCUSED= notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_toast "问不到窗口时退回标记" "[-Body] [答完了：跑完了]"

# 会话还没有名字（刚开始、标题还没生成）→ 没有可比对的东西，同样退回标记
reset_calls; mark "session-other"
STUB_FOCUSED=yes notify "$(ev_stop session-a "$win_cwd" "跑完了")"
expect_toast "会话没名字时退回标记" "[-Body] [答完了：跑完了]"

# 标记说是你、窗口说不是 → 照弹。这一条是「窗口说了算」的分界：标记只知道你最后在哪儿
# 敲过字，你敲完切走了它并不知道。最常见的形状就是停在总览列表上 —— 那时谁都不算当前，
# 可标记还压着最后打字的那个。旧写法（标记先判、命中就退出）在这儿会静默，正好是错的
reset_calls; mark "session-a"
STUB_FOCUSED=no notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_toast "标记说是你、窗口说不是 → 照弹" "[-Body] [答完了：跑完了]"

# 标记说是你、窗口答不出来 → 压。窗口没得答时标记是唯一凭据，不能反过来当成「你没在看」
reset_calls; mark "session-a"
STUB_FOCUSED= notify "$(ev_stop_tr session-a "$win_cwd" "$tr_file" "跑完了")"
expect_silent "窗口答不出来时退回标记：标记说是你就不弹"

# 会话还没名字时同理：没有可比对的东西，标记说了算
reset_calls; mark "session-a"
STUB_FOCUSED=no notify "$(ev_stop session-a "$win_cwd" "跑完了")"
expect_silent "会话没名字时退回标记：标记说是你就不弹"

# 当前会话答完 → 不弹。这是整个功能的中心：你正看着它，不需要提醒
reset_calls; mark "session-a"
notify "$(ev_stop session-a "$win_cwd" "把 hook 加好了")"
expect_silent "当前会话答完"

# 从来没有标记过（非交互会话，比如 claude -p）：无从判断你在哪，宁可弹
reset_calls; rm -f "${notify_cfg}/${MARK_NAME}"
notify "$(ev_stop session-a "$win_cwd" "跑完了")"
expect_toast "没有标记文件时答完"

# 正文取不到时只留前缀，不该出现「答完了：」后面空一截还带着冒号
reset_calls; mark "session-other"
notify "$(ev_stop session-a "$win_cwd" "")"
expect_toast "答完但没有正文" "[-Body] [答完了]"

# 提醒只有两行位置，长正文要截断，且按字符截而不是按字节（中文一个字三字节，
# 按字节截会把最后一个字劈成半个，显示成乱码）
reset_calls; mark "session-other"
long="$(printf '一%.0s' $(seq 1 200))"
notify "$(ev_stop session-a "$win_cwd" "$long")"
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
notify "$(ev_stop session-a "$win_cwd" "第一行${bs}n第二行${bs}t带制表符")"
expect_toast "正文压成一行" "[-Body] [答完了：第一行 第二行 带制表符]"

# 你敲字了 → 记下「当前会话是这个」，并撤掉这个会话遗留的提醒。
# 撤这一步不能省：常驻通知不会自己消失，你答完那道选择题，屏幕上还挂着「等你选」。
reset_calls; mark "session-other"
notify "$(ev_prompt session-a user "$win_cwd")"
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
  notify "$(ev_prompt session-a "$src" "$win_cwd")"
  [ "$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-other" ] \
    || fail "source=${src} 时不该改写当前会话标记"
  expect_silent "source=${src} 的 UserPromptSubmit"
done

# ── 哪些提示词算「你在用这个会话」 ───────────────────────────────────
# 事件名的字面意思骗人：UserPromptSubmit 不只在你敲字时触发，机器也会借它把会话叫醒。
# 判别不能靠 payload 里的 source —— CLI 的 schema 里声明了它（任务通知按设计该报
# system），但 2.1.269 实测从不发这个字段：人打的提示词和后台任务注入的字段集一模一样
# （本机抓包逐字段比对过）。所以只能看提示词本身。
#
# 机器注入的一律以 < 开头。这条不是我定的，是 Claude Code 自己认「人打的」用的形状。
# 后台任务完成是抢标记的主力：本机 1591 份会话记录里 <task-notification> 出现 1000 次。
# 它一轮完成就把标记挪到自己身上，你正看着的会话于是成了「后台」，通知开始乱弹
# —— 这正是这次报上来的 bug。
tn='<task-notification>'
reset_calls; mark "session-other"
notify "$(ev_prompt_txt session-a "$win_cwd" "${tn}${bs}n<task-id>x</task-id>${bs}n</task-notification>")"
[ "$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-other" ] \
  || fail "后台任务完成的提示词不该改写当前会话标记"
expect_silent "后台任务完成的 UserPromptSubmit"

# 前面带空白也一样挡掉，不然加个换行就绕过去了
reset_calls; mark "session-other"
notify "$(ev_prompt_txt session-a "$win_cwd" "${bs}n${bs}n  ${tn}</task-notification>")"
[ "$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-other" ] \
  || fail "带前导空白的机器注入提示词不该改写当前会话标记"

# 同类的机器注入一律挡掉，不是只挡后台任务通知这一种
for t in '<local-command-stdout>' '<fork-boilerplate>' '<system-reminder>'; do
  reset_calls; mark "session-other"
  notify "$(ev_prompt_txt session-a "$win_cwd" "${t}机器塞进来的")"
  [ "$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-other" ] \
    || fail "${t} 开头的提示词不该改写当前会话标记"
done

# 反过来，真敲的字必须算数 —— 而且要在最贴近真实的形状下验：payload 里没有 source 字段。
# 这一条钉的是「将来 CLI 真的开始发 source 时，别把正常输入也一起挡掉」
reset_calls; mark "session-other"
notify "$(ev_prompt_txt session-a "$win_cwd" "把通知的标题改成带上会话名")"
[ "$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-a" ] \
  || fail "人打的提示词没有把标记改成当前会话（实际：$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)）"

# 斜杠命令和 ! 命令也是你敲的，虽然它们同样以标签开头。例外就这三个，别的一律按机器
# 注入挡掉。反过来列黑名单不行：CLI 加一个新标签它就开始抢标记，也就是这个 bug 的由来
for t in '<command-message>' '<command-name>' '<bash-input>'; do
  reset_calls; mark "session-other"
  notify "$(ev_prompt_txt session-a "$win_cwd" "${t}foo</command-name>")"
  [ "$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-a" ] \
    || fail "${t} 开头（你敲的命令）应当记成当前会话"
done

# 弹选择题：正文是问题原文，这样你不切窗口也能先看一眼问的是什么
reset_calls; mark "session-other"
notify "$(ev_ask session-a "$win_cwd" "要放进插件还是只在本机配？")"
expect_toast "别的会话弹选择题" "[-Body] [等你选：要放进插件还是只在本机配？]"

# 同一个事件名也被别的工具用着，只认 AskUserQuestion
reset_calls; mark "session-other"
notify "$(ev_tool session-a Bash "$win_cwd")"
expect_silent "PreToolUse 但不是 AskUserQuestion"

# 要你批准：只认 permission_prompt。空闲提醒（idle_prompt）是你明确不要的那条，
# 它和你答完一轮是同一件事，弹两遍纯属吵
reset_calls; mark "session-other"
notify "$(ev_note session-a permission_prompt "$win_cwd" "Claude needs your permission")"
expect_toast "别的会话要权限" "[-Body] [要批准：Claude needs your permission]"

reset_calls; mark "session-other"
notify "$(ev_note session-a idle_prompt "$win_cwd" "Claude is waiting for your input")"
expect_silent "空闲等待提醒（明确不要）"

# ── 你回到那个会话动了手 → 撤掉它自己的提醒 ─────────────────────────
# 「切到那个会话」这个动作本身，hook 侧看不见：Claude Code 不把终端焦点暴露给 hook
# （它的 33 个 hook 事件里没有焦点事件，焦点只在内部用来发「客户端在线」心跳和决定
# 要不要跳过它自己的通知）。所以只能认「你在那个会话里真的动了手」。
#
# 三种提醒里，「答完了」是你打字撤的，那条已经有了。「等你选」和「要批准」不是打字
# —— 你是在界面上点掉的，UserPromptSubmit 不会触发，提醒于是留在屏幕上不走。
# 工具真的跑起来，才是这两种「已经处理了」的可靠信号。
ev_post() { printf '{"hook_event_name":"PostToolUse","session_id":"%s","tool_name":"%s","cwd":"%s","tool_input":{"command":"ls"}}' "$1" "$2" "$3"; }

# 先弹一条挂上，再模拟你在那个会话里动手
reset_calls; mark "session-other"
notify "$(ev_stop session-a "$win_cwd" "跑完了")"
reset_calls
notify "$(ev_post session-a Bash "$win_cwd")"
case "$(calls)" in
  *"[-Mode] [clear]"*"[-Tag] [sessiona]"*) ;;
  *) fail "在那个会话里动了手，它自己的提醒没有被撤掉（实际：${calls:-无调用}）" ;;
esac

# 撤的是「事件来自的那个会话」的提醒，不是别的会话的。每个会话的通知各有各的标签，
# 撤错标签等于把别人的提醒误删，或者自己的删不掉
reset_calls; mark "session-other"
notify "$(ev_stop session-a "$win_cwd" "跑完了")"
reset_calls
notify "$(ev_post session-b Bash "$win_cwd")"
case "$(calls)" in
  *"[-Tag] [sessiona]"*) fail "别的会话动手，却撤了 session-a 的提醒（实际：${calls}）" ;;
esac

# 动手不是说话，不该把「当前会话」标记抢过去。抢了的话，那个会话之后出事就不再提醒你
reset_calls; mark "session-other"
notify "$(ev_post session-a Bash "$win_cwd")"
[ "$(cat "${notify_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-other" ] \
  || fail "工具跑起来不该改写当前会话标记"

# 屏幕上根本没有这个会话的通知时，一次 PowerShell 都不该起。PostToolUse 是唯一每个
# 工具调用都会来的事件（本机实测：一次会话的工具调用中位数 17 次），而一次 PowerShell
# 约 750 毫秒 —— 撤一个不存在的东西不值这个价
reset_calls; mark "session-other"
notify "$(ev_post session-b Bash "$win_cwd")"
expect_silent "没有通知挂着时的 PostToolUse"

# 坏输入不该让 hook 挂掉。hook 挂掉比通知弹不出来严重得多
reset_calls; mark "session-other"
notify '这不是 JSON'
[ $? -eq 0 ] || fail "非 JSON 输入没有正常退出"
expect_silent "非 JSON 输入"
notify ''
expect_silent "空输入"
notify '{"hook_event_name":"Stop","cwd":"/tmp"}'
expect_silent "缺 session_id"
notify '{"hook_event_name":"没听说过的事件","session_id":"session-a"}'
expect_silent "不认识的 hook 事件"

# 标记文件跟着 CLAUDE_CONFIG_DIR 走，而不是写死 $HOME/.claude
reset_calls
alt_cfg="$(scratch_dir)"; alt_home="$(scratch_dir)"
STUB_LOG="$notify_log" CLAUDE_CONFIG_DIR="$alt_cfg" HOME="$alt_home" \
  CLAUDE_NOTIFY_PS="$notify_stub" bash "${HOOKS_DIR}/notify" >/dev/null 2>&1 \
  <<< "$(ev_prompt session-a user "$win_cwd")"
[ "$(cat "${alt_cfg}/${MARK_NAME}" 2>/dev/null)" = "session-a" ] \
  || fail "标记文件没有写在 CLAUDE_CONFIG_DIR 下"
[ -f "${alt_home}/.claude/${MARK_NAME}" ] && fail "设了 CLAUDE_CONFIG_DIR 时仍往 HOME/.claude 写了标记"

# run-hook.cmd 的 bash 分支要能把 notify 透传进去
STUB_LOG="$notify_log" CLAUDE_CONFIG_DIR="$notify_cfg" CLAUDE_NOTIFY_PS="$notify_stub" \
  bash "${HOOKS_DIR}/run-hook.cmd" notify >/dev/null 2>&1 <<< '{"hook_event_name":"不认识的","session_id":"x"}'
[ $? -eq 0 ] || fail "run-hook.cmd 透传 notify 时退出码非 0"

# Windows 上的生产路径是 cmd 批处理分支。notify 还得靠标准输入拿到事件数据，
# 标准输入能不能穿过 cmd.exe 到 bash，只有真跑一次才知道。
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    if command -v cmd.exe >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1; then
      reset_calls; mark "session-other"
      (cd "${REPO_ROOT}" && STUB_LOG="$notify_log" CLAUDE_CONFIG_DIR="$notify_cfg" \
        CLAUDE_NOTIFY_PS="$notify_stub" MSYS_NO_PATHCONV=1 timeout 20 cmd.exe /c "${RUN_HOOK_CMD_WIN} notify" \
        <<< "$(ev_stop session-cmd "$win_cwd" "走批处理分支")" 2>/dev/null)
      expect_toast "cmd.exe 批处理分支" "[-Tag] [sessioncmd]" "[-Body] [答完了：走批处理分支]"
    fi
    ;;
esac

# ── statusline 脚本冒烟 ────────────────────────────────────────────
# 这两个脚本坏了不报错，只会让状态栏空白或少一截，所以要真跑一次、比对输出内容。
# statusline_src 由入口提供。
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
  # 输出里该出现的片段，按顺序都得命中
  expect_contains() {
    local desc="$1" out="$2"; shift 2
    local frag
    for frag in "$@"; do
      case "$out" in
        *"$frag"*) ;;
        *) fail "${desc}：没有「${frag}」（实际：${out}）" ;;
      esac
    done
  }

  # 主状态栏的测试目录里不能有 subagents/：statusline.py 会把子代理记录一并计入
  # 本会话开销，两份同内容的记录叠起来总 token 直接翻倍。
  smoke_main="$(scratch_dir)"
  smoke_sub="$(scratch_dir)"
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
  expect_contains "主状态栏输出" "$main_out" '缓存命中 90.0%' '总token 1.05M' '(峰)' '2h05m'

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
  expect_contains "子代理状态栏输出" "$sub_out" '冒烟' '缓存命中 90.0%' '总token 1.05M' '(峰)' '2m' '5m'
  line_of() { printf '%s\n' "$sub_out" | grep -F "\"id\": \"$1\""; }
  [ "$(line_of frozen)" = '{"id": "frozen", "content": "冻住  ¥0.64(峰) · 缓存命中 90.0% · 总token 1.05M · 5m"}' ] \
    || fail "已结束的子代理时长没停在末条记录（实际：$(line_of frozen)）"
  [ "$(line_of zero)" = '{"id": "zero", "content": "零起点  ¥0.64(峰) · 缓存命中 90.0% · 总token 1.05M"}' ] \
    || fail "起点为 0 的子代理不该显示时长（实际：$(line_of zero)）"
  [ "$(line_of nostart)" = '{"id": "nostart", "content": "无起点  ¥0.64(峰) · 缓存命中 90.0% · 总token 1.05M"}' ] \
    || fail "取不到起点的子代理不该显示时长（实际：$(line_of nostart)）"

  # ── 同一条回复被拆成多条记录时不能重复累加 ──
  # Claude Code 把一条回复的思考、正文、工具调用各写成一条记录，每条都带同一份完整
  # usage 和同一个 message.id。照着行数累加会把一次调用算成好几遍（真实会话实测被
  # 放大 2.6~4.2 倍）。下面把一次调用写成三条，另加一次独立调用（id 不同）作对照：
  # 合计只该按两次调用计 —— 总 token 2.10M、费用 ¥1.27、命中率仍 90.0%。
  smoke_dup="$(scratch_dir)"
  smoke_dsub="$(scratch_dir)"
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
  expect_contains "主状态栏（同 message.id 多条记录）" "$dup_main" '¥1.27(峰)' '缓存命中 90.0%' '总token 2.10M'

  # startTime 定在末条记录前 300 秒，时长才与跑的时刻无关，能写死成 5m
  dup_sub="$(cd "$smoke_dsub" && printf '{"columns":160,"transcript_path":"sess.jsonl","tasks":[{"id":"dup","description":"重复","status":"completed","startTime":1789524000000}]}' \
    | python "${statusline_src}/subagent-statusline.py" 2>/dev/null)"
  [ "$dup_sub" = '{"id": "dup", "content": "重复  ¥1.27(峰) · 缓存命中 90.0% · 总token 2.10M · 5m"}' ] \
    || fail "子代理状态栏把同一个 message.id 的多条记录重复累加了（实际：${dup_sub}）"

  # ── fork 型子代理不能把父代理的历史算成自己的 ──
  # fork 是把父代理的上下文整个复制出去另开一个代理：它的记录文件开头带着父代理那几次
  # 调用，message.id 与父代理文件里的完全相同——同一份记录被抄了一份，不是新发生的调用。
  # 按 id 收敛只在本文件内做，跨文件就漏了，fork 那一行会把父代理的开销再加一遍。
  # 真实会话实测：3 个 fork 行各多算了父代理的 6 条调用，占该行 35%~45%。
  #
  # 这一组同时压住主状态栏：外层汇总要跨文件收敛，父代理那两次调用只算一次。
  # 主会话自己 1 次（msg_m）、父代理 2 次（msg_p1/p2）、fork 自己 1 次（msg_f1），
  # 合计 4 次 = ¥2.54 / 4.20M；不收敛的话会按 6 次算成 ¥3.82。
  smoke_fork="$(scratch_dir)"
  mkdir -p "${smoke_fork}/sess/subagents"
  cat > "${smoke_fork}/sess.jsonl" <<'SYNTHJSONL'
{"timestamp":"2026-09-16T02:00:00.000Z","message":{"id":"msg_m","stop_reason":"end_turn","model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
SYNTHJSONL
  cat > "${smoke_fork}/sess/subagents/agent-p.jsonl" <<'SYNTHJSONL'
{"timestamp":"2026-09-16T02:00:00.000Z","message":{"id":"msg_p1","stop_reason":"end_turn","model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
{"timestamp":"2026-09-16T02:05:00.000Z","message":{"id":"msg_p2","stop_reason":"end_turn","model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
SYNTHJSONL
  cat > "${smoke_fork}/sess/subagents/agent-f.jsonl" <<'SYNTHJSONL'
{"timestamp":"2026-09-16T02:00:00.000Z","message":{"id":"msg_p1","stop_reason":"end_turn","model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
{"timestamp":"2026-09-16T02:05:00.000Z","message":{"id":"msg_p2","stop_reason":"end_turn","model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
{"timestamp":"2026-09-16T02:10:00.000Z","message":{"id":"msg_f1","stop_reason":"end_turn","model":"deepseek-flash","usage":{"input_tokens":100000,"cache_read_input_tokens":900000,"cache_creation_input_tokens":0,"output_tokens":50000}}}
SYNTHJSONL
  printf '{"agentType":"general-purpose","spawnDepth":1}' \
    > "${smoke_fork}/sess/subagents/agent-p.meta.json"
  printf '{"agentType":"fork","isFork":true,"parentAgentId":"p","spawnDepth":2}' \
    > "${smoke_fork}/sess/subagents/agent-f.meta.json"

  fork_main="$(cd "$smoke_fork" && printf '{"transcript_path":"sess.jsonl"}' \
    | python "${statusline_src}/statusline.py" 2>/dev/null)"
  expect_contains "主状态栏（fork 复制的历史只算一次）" "$fork_main" '¥2.54(峰)' '总token 4.20M'

  # 不给 startTime，时长那一截整段不显示，行内容因此与跑的时刻无关
  fork_sub="$(cd "$smoke_fork" && printf '{"columns":160,"transcript_path":"sess.jsonl","tasks":[{"id":"p","description":"父代理","status":"running"},{"id":"f","description":"fork 出来的","status":"running"}]}' \
    | python "${statusline_src}/subagent-statusline.py" 2>/dev/null)"
  line_of() { printf '%s\n' "$fork_sub" | grep -F "\"id\": \"$1\""; }
  [ "$(line_of f)" = '{"id": "f", "content": "fork 出来的  ¥0.64(峰) · 缓存命中 90.0% · 总token 1.05M"}' ] \
    || fail "fork 子代理把父代理的历史算成了自己的（实际：$(line_of f)）"
  [ "$(line_of p)" = '{"id": "p", "content": "父代理  ¥1.27(峰) · 缓存命中 90.0% · 总token 2.10M"}' ] \
    || fail "父代理自己的开销被算少了（实际：$(line_of p)）"
fi

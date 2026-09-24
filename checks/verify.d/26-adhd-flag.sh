# ── ADHD 常驻标记文件 ──────────────────────────────────────────────
# 上游 i-have-adhd 插件的 SessionStart 钩子只在 <配置目录>/.i-have-adhd-always
# 存在时才注入它那套输出形状规则，所以本仓库的 session-start 要替它建这个文件。
# 步骤断了、或者建错了地方，表现都是静默的：那套规则一个字不进上下文，会话照开。
# 建文件那一段往 stdout 写东西会让 10 那块解析 JSON 失败，那条已经在拦了，这里不重复。
# test_home 由入口提供。
# watch: plugin/hooks/session-start
test_cfg="${test_home}/.claude"
adhd_flag="${test_cfg}/.i-have-adhd-always"

# 先删掉再从「文件不存在」这个初态跑：单独跑这一块时 10、25 不会执行，而 25 那一跑
# 已经顺手把文件建出来了，直接断言「它在」就分不清是本模块建的和是先前留下的。
rm -f "$adhd_flag"
HOME="$test_home" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1
[ -f "$adhd_flag" ] \
  || fail "session-start 没有建 ${adhd_flag}（没有它，上游插件的常驻注入不会触发）"

# 已存在就不该再动它——上游只判文件在不在，内容没有意义，覆盖只会抹掉用户自己塞的东西。
# 判据同 25 那块：把时间戳拨回 2000-01-01，跑一遍，拿 2000-01-02 的参照文件去比。
# 用参照文件而不是比源文件的 mtime，是因为源文件的 mtime 就是「刚刚」。
# 内容也要比：时间戳没动、内容被重写成空文件的话，只比时间会漏掉。
printf '哨兵内容\n' > "$adhd_flag"
touch -t 200001010000 "$adhd_flag"
idem_ref="$(scratch_file)"
touch -t 200001020000 "$idem_ref"
HOME="$test_home" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1
[ "$adhd_flag" -ot "$idem_ref" ] \
  || fail "标记文件已存在时仍被重写（应原样不动）"
[ "$(cat "$adhd_flag")" = "哨兵内容" ] \
  || fail "标记文件已存在时内容被改掉了"

# 设了 CLAUDE_CONFIG_DIR 就该建到那儿，而不是继续建到 $HOME/.claude
cfg_alt="$(scratch_dir)"
home_alt="$(scratch_dir)"
CLAUDE_CONFIG_DIR="$cfg_alt" HOME="$home_alt" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1
[ -f "${cfg_alt}/.i-have-adhd-always" ] \
  || fail "设了 CLAUDE_CONFIG_DIR 时没有把 .i-have-adhd-always 建到该目录"
if [ -f "${home_alt}/.claude/.i-have-adhd-always" ]; then
  fail "设了 CLAUDE_CONFIG_DIR 时仍往 HOME/.claude 建了标记文件"
fi

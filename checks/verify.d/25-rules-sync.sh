# ── rules 常驻规则同步 ─────────────────────────────────────────────
# rules/ 下的规则要落到 <配置目录>/rules/ 才会被 Claude Code 当用户级常驻规则加载，
# 而插件安装目录带版本号、指不得，所以只能靠 session-start 每次会话同步过去。
# 这一步断了，表现是静默的：规则不再进上下文，会话照开，没有任何报错。
# test_home 与 rules_src 由入口提供。
test_cfg="${test_home}/.claude"

# 自己先跑一次，别指望 20 跑过：单独跑这一块时 20 不会执行
HOME="$test_home" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1

rules_found=0
for f in "${rules_src}"/*.md; do
  [ -f "$f" ] || continue
  rules_found=1
  name="${f##*/}"
  if [ ! -f "${test_cfg}/rules/${name}" ]; then
    fail "session-start 没有把 rules/${name} 同步到配置目录的 rules/ 下"
  elif ! cmp -s "$f" "${test_cfg}/rules/${name}"; then
    fail "同步到配置目录的 rules/${name} 与仓库里的不一致"
  fi
done

if [ "$rules_found" -eq 0 ]; then
  fail "仓库里缺 rules/*.md（同步的源文件）"
fi

# 幂等：内容一致时不该重写。判据同 20 那块——把目标的时间戳拨回 2000-01-01 再跑一次，
# 拿一个 2000-01-02 的参照文件去比。用参照文件而不是拿源文件的 mtime 比，是因为源文件的
# mtime 是 checkout 时间，刚克隆完就跑校验时它会和「现在」撞在同一秒。
for f in "${rules_src}"/*.md; do
  [ -f "$f" ] || continue
  name="${f##*/}"
  [ -f "${test_cfg}/rules/${name}" ] || continue
  touch -t 200001010000 "${test_cfg}/rules/${name}"
  idem_ref="$(scratch_file)"
  touch -t 200001020000 "$idem_ref"
  HOME="$test_home" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1
  [ "${test_cfg}/rules/${name}" -ot "$idem_ref" ] \
    || fail "内容一致时仍重写了 rules/${name}（同步不幂等）"
done

# 目标被改坏要能修回，否则「仓库是唯一真相」这句话不成立。
# 这条对规则尤其要紧：本地改副本是唯一能让规则变样的路子，得确保它下一会话就被抹掉，
# 不然「仓库是唯一真相」就只是句口号，两份内容会悄悄分叉。
for f in "${rules_src}"/*.md; do
  [ -f "$f" ] || continue
  name="${f##*/}"
  [ -f "${test_cfg}/rules/${name}" ] || continue
  printf '\n# 校验脚本塞的杂质\n' >> "${test_cfg}/rules/${name}"
  HOME="$test_home" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1
  cmp -s "$f" "${test_cfg}/rules/${name}" \
    || fail "rules/${name} 被改坏后没能同步回仓库版本"
done

# 设了 CLAUDE_CONFIG_DIR 就该写到那儿，而不是继续写 $HOME/.claude
cfg_alt="$(scratch_dir)"
home_alt="$(scratch_dir)"
CLAUDE_CONFIG_DIR="$cfg_alt" HOME="$home_alt" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1
for f in "${rules_src}"/*.md; do
  [ -f "$f" ] || continue
  name="${f##*/}"
  [ -f "${cfg_alt}/rules/${name}" ] || fail "设了 CLAUDE_CONFIG_DIR 时没有把 rules/${name} 同步到该目录"
done
if [ -d "${home_alt}/.claude/rules" ]; then
  fail "设了 CLAUDE_CONFIG_DIR 时仍往 HOME/.claude/rules 写了"
fi

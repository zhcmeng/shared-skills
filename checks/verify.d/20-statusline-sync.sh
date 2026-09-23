# ── statusline 脚本同步 ────────────────────────────────────────────
# settings.json 里的 statusLine 命令指向的是配置目录下的固定路径（插件安装目录带版本号，
# 指不得），所以这两个脚本有没有被放到那儿，直接决定状态栏能不能用。
# test_home 与 statusline_src 由入口提供。
# watch: plugin/hooks/session-start plugin/statusline/
test_cfg="${test_home}/.claude"

# 自己先跑一次，别指望 10 跑过：单独跑这一块时 10 不会执行，否则会假报「没同步过去」
HOME="$test_home" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1

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
  idem_ref="$(scratch_file)"
  touch -t 200001020000 "$idem_ref"
  HOME="$test_home" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1
  [ "${test_cfg}/statusline.py" -ot "$idem_ref" ] \
    || fail "内容一致时仍重写了 statusline.py（同步不幂等）"
fi

# 目标被改坏要能修回，否则「仓库是唯一真相」这句话不成立
if [ -f "${test_cfg}/statusline.py" ]; then
  printf '\n# 校验脚本塞的杂质\n' >> "${test_cfg}/statusline.py"
  HOME="$test_home" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1
  cmp -s "${statusline_src}/statusline.py" "${test_cfg}/statusline.py" \
    || fail "目标被改坏后没能同步回仓库版本"
fi

# 设了 CLAUDE_CONFIG_DIR 就该写到那儿，而不是继续写 $HOME/.claude
cfg_alt="$(scratch_dir)"
home_alt="$(scratch_dir)"
CLAUDE_CONFIG_DIR="$cfg_alt" HOME="$home_alt" bash "${HOOKS_DIR}/session-start" >/dev/null 2>&1
[ -f "${cfg_alt}/statusline.py" ] || fail "设了 CLAUDE_CONFIG_DIR 时没有同步到该目录"
if [ -d "${home_alt}/.claude" ]; then
  fail "设了 CLAUDE_CONFIG_DIR 时仍往 HOME/.claude 写了"
fi

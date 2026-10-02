# ── test-case-design 这条链子 ──────────────────────────────────────
# 技能自己那四个测试，再加 evals/ 下批次配置的校验，一起接到这里。
# 这几样原先都没有自动跑：checks/ 里一处都不引 tests/，批次配置更没人过一遍。
# 这条链子上的毛病全是静默的——配置坏了整批用例跑不起来而盘上文件看着都在，
# 不跑就没人知道。2026-10-01 那天五笔提交（补覆盖率自检、补禁用词检查、
# 报告目录改名、重编小节号、补落成编号）都是这么攒出来的：人先撞见，再回头补。
#
# **不查 evals/ 下的产出**：仓库里不留存量产出（2026-10-02 起，老的几套已删）。
# 留着那段的话，一份产出都扫不到时它会以「这条链子没有可检查的东西」失败——
# 而那不是错，是仓库里本来就没有。真产出上跑两个检查器这一面由技能自己的测试
# 盖着：test_example 把范本拆成七份喂 check_docs，test_check_landing 在临时目录上
# 造整套产出跑真命令行。
#
# 批次配置那一段要机器上装着 skill-up 才跑（外部工具，不在仓库依赖里），没装就打一句
# 提示跳过；校验只读配置、不碰网络。
#
# 判失败，不降成提示：配置是签进仓库的东西，跑不过就是坏的。
# 缺 python 时跳过（同 30 那块的分寸）——技能自己的测试是 python 写的，
# 本机没装 python 时这条链子本来也跑不起来。
#
# watch 声明整个 evals/：产出那一层不再查，但批次配置就在 `evals/<批>/*.yaml`，
# 只声明技能与测试那两处的话，单改配置不会触发这一段。
# watch: evals/ plugin/skills/test-case-design/ tests/test-case-design/

# 跑一条子命令，过了就算了，没过先把它的输出原样打出来再记一笔失败——
# 只留一句「没过」的话，还得自己再跑一遍才知道是哪里没过。
tcd_run() {   # tcd_run <在哪个目录跑> <说明> <命令...>
  local where="$1" desc="$2"; shift 2
  local log; log="$(scratch_file)"
  if ( cd "$where" && "$@" ) > "$log" 2>&1; then
    return 0
  fi
  echo "── ${desc}：输出 ──"
  cat "$log"
  echo "── 输出到此 ──"
  fail "${desc}"
}

if ! command -v python >/dev/null 2>&1; then
  echo "提示：没找到 python，跳过 test-case-design 这条链子的检查（测试与两个检查器都是 python 写的）"
else
  tcd_tests=0
  for t in "${REPO_ROOT}"/tests/test-case-design/test_*.py; do
    [ -f "$t" ] || continue
    tcd_tests=$((tcd_tests + 1))
    tcd_run "$REPO_ROOT" "test-case-design 的测试 ${t##*/}" python "$t"
  done

  # 一份测试都没扫到，说明这条链子空了。别放行：静默跳过等于这个模块永远不会跑，
  # 而人以为检查过了——正是本仓库其他模块一直在防的那类失败。
  if [ "$tcd_tests" -eq 0 ]; then
    fail "tests/test-case-design/ 下一份测试都没有，这条链子没有可检查的东西"
  fi

  # 批次配置（跑测的入口）住在 evals/ 那一层。装了 skill-up 就逐份过一遍校验——
  # 配置坏了的表现是静默的：整批用例跑不起来，而盘上文件看着都在。
  if command -v skill-up >/dev/null 2>&1; then
    tcd_cfgs=0
    for tcd_cfg in "${REPO_ROOT}"/evals/*/*.yaml; do
      [ -f "$tcd_cfg" ] || continue
      tcd_cfgs=$((tcd_cfgs + 1))
      tcd_run "$REPO_ROOT" "${tcd_cfg#"${REPO_ROOT}"/} 的校验（skill-up validate）" \
        skill-up validate "${tcd_cfg#"${REPO_ROOT}"/}"
    done
    # 一份都没扫到不是错：配置可以先于产出进仓库。但要说一声，不然输出里少一行，
    # 看着像查过了。
    if [ "$tcd_cfgs" -eq 0 ]; then
      echo "提示：evals/ 下一份批次配置都没有，跳过配置校验"
    fi
  else
    echo "提示：没找到 skill-up，跳过 evals/ 下批次配置的校验"
  fi
fi

# ── test-case-design 这条链子 ──────────────────────────────────────
# 技能自己那四个测试，加上真产出的两个检查器，一起接到这里。这三样原先一样都没有自动跑：
# checks/ 里一处都不引 tests/，产出也只靠人想起来才跑一次 check_docs 与 check_landing。
# 这条链子上的毛病全是静默的——文档与盘上各说各的，不跑就没人知道。2026-10-01 那天
# 五笔提交（补覆盖率自检、补禁用词检查、报告目录改名、重编小节号、补落成编号）都是
# 这么攒出来的：人先撞见，再回头补。
#
# 判失败，不降成提示：产出与技能都是签进仓库的东西，跑不过就是坏的。
# 缺 python 时跳过（同 30 那块的分寸）——测试与两个检查器都是 python 写的，
# 本机没装 python 时这条链子本来也跑不起来。
#
# 落成对照要在仓库根下跑、且不给成品路径：那样它按测试用例规格说明的「成品落点」表去取
# 成品，顺带把那张表也验了——表里的路径写错时，它报「读不到」。
#
# watch 声明整个 evals/，不只产出那一层：产出在 `evals/<批>/test-case-design/` 下，
# 成品（用例配置与批次配置）在它上一级，只声明产出那一层的话，单改成品不会触发。
# watch: evals/ plugin/skills/test-case-design/ tests/test-case-design/

tcd_scripts="${PLUGIN_DIR}/skills/test-case-design/scripts"

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
  for t in "${REPO_ROOT}"/tests/test-case-design/test_*.py; do
    [ -f "$t" ] || continue
    tcd_run "$REPO_ROOT" "test-case-design 的测试 ${t##*/}" python "$t"
  done

  tcd_batches=0
  for tcd_root in "${REPO_ROOT}"/evals/*/test-case-design; do
    [ -d "$tcd_root" ] || continue
    tcd_batches=$((tcd_batches + 1))
    tcd_name="$(basename "$(dirname "$tcd_root")")"
    tcd_run "$REPO_ROOT" "${tcd_name} 的六份自检（check_docs）" \
      python "${tcd_scripts}/check_docs.py" "$tcd_root"
    tcd_run "$REPO_ROOT" "${tcd_name} 的落成对照（check_landing）" \
      python "${tcd_scripts}/check_landing.py" "$tcd_root"
  done

  # 一份产出都没扫到，说明这条链子空了。别放行：静默跳过等于这个模块永远不会跑，
  # 而人以为检查过了——正是本仓库其他模块一直在防的那类失败。
  if [ "$tcd_batches" -eq 0 ]; then
    fail "evals/ 下一份 test-case-design 产出都没有，这条链子没有可检查的东西"
  fi
fi

# ── test-case-design 这条链子 ──────────────────────────────────────
# 技能自己那四个测试、真产出的两个检查器，再加 evals/ 下批次配置的校验，一起接到这里。
# 这几样原先都没有自动跑：checks/ 里一处都不引 tests/，产出也只靠人想起来才跑一次
# check_docs 与 check_landing，批次配置更没人过一遍。
# 这条链子上的毛病全是静默的——文档与盘上各说各的，配置坏了整批用例跑不起来而盘上文件
# 看着都在，不跑就没人知道。2026-10-01 那天五笔提交（补覆盖率自检、补禁用词检查、
# 报告目录改名、重编小节号、补落成编号）都是这么攒出来的：人先撞见，再回头补。
#
# 批次配置那一段要机器上装着 skill-up 才跑（外部工具，不在仓库依赖里），没装就打一句
# 提示跳过；校验只读配置、不碰网络。
#
# 判失败，不降成提示：产出与技能都是签进仓库的东西，跑不过就是坏的。
# 缺 python 时跳过（同 30 那块的分寸）——测试与两个检查器都是 python 写的，
# 本机没装 python 时这条链子本来也跑不起来。
#
# 落成对照要在仓库根下跑、且不给成品路径：那样它按测试用例规格说明的「成品落点」表去取
# 成品，顺带把那张表也验了——表里的路径写错时，它报「读不到」。
#
# 只有成品已经落成的批次才跑落成对照：产出可以先于成品进仓库（技能允许先出六份），
# 那种批次没有可对照的东西，跑出来只有一句「还没落成」，记成失败就成了假警报。
# 分法是 check_landing 自己的退出码：3 就是「还没落成」，见下面那段循环。
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

# 跑一条子命令，退出码当返回值；输出落在 $tcd_log，要打的时候自己 cat。
#
# 别写成 `st="$(tcd_try ...)"`：那样整个函数跑在子 shell 里，它设的 $tcd_log 传不出来
# （verify.sh 头上记着同一类坑），调用方 cat 到的是个空变量。就写成两句：
# `tcd_try ...; st=$?`。
#
# 与 tcd_run 的分工：tcd_run 把非 0 一律当失败，适合「要么过要么坏」的命令；
# check_landing 退几各有各的意思（0 对上了、1 有错、2 用错了、3 还没落成），
# 得让调用方分着看，所以另走这一条。
tcd_try() {   # tcd_try <在哪个目录跑> <命令...>
  local where="$1"; shift
  tcd_log="$(scratch_file)"
  ( cd "$where" && "$@" ) > "$tcd_log" 2>&1
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
    tcd_try "$REPO_ROOT" python "${tcd_scripts}/check_landing.py" "$tcd_root"
    tcd_st=$?
    case "$tcd_st" in
      0) ;;   # 编号在两边对得上
      3) # 这一批的成品还没落成，没有可对照的东西。产出的正常状态，不是错。
         # 跳过时要说一声：不说的话输出里少一行，看着像这一批查过了。
         echo "提示：${tcd_name} 的成品还没落成，跳过落成对照（落成之后回来填上那张表）" ;;
      *) echo "── ${tcd_name} 的落成对照（check_landing）：输出 ──"
         cat "$tcd_log"
         echo "── 输出到此 ──"
         fail "${tcd_name} 的落成对照（check_landing）" ;;
    esac
  done

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
    # 一份都没扫到不是错：产出可以先于成品进仓库（同 check_landing 退 3 的那种状态）。
    # 但要说一声，不然输出里少一行，看着像查过了。
    if [ "$tcd_cfgs" -eq 0 ]; then
      echo "提示：evals/ 下一份批次配置都没有，跳过配置校验"
    fi
  else
    echo "提示：没找到 skill-up，跳过 evals/ 下批次配置的校验"
  fi

  # 一份产出都没扫到，说明这条链子空了。别放行：静默跳过等于这个模块永远不会跑，
  # 而人以为检查过了——正是本仓库其他模块一直在防的那类失败。
  if [ "$tcd_batches" -eq 0 ]; then
    fail "evals/ 下一份 test-case-design 产出都没有，这条链子没有可检查的东西"
  fi
fi

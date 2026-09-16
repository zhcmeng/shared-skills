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
  # 光有 reminder 不够。系统会静默忽略它——本机实测：只有 reminder 的通知 25 秒后照样
  # 自己消失（正是 duration="long" 的时长），而且不报错，所以 notify.ps1 里那个「系统
  # 不接受就退成长时间显示」的兜底也永远不会触发。
  # 给它一个可点的按钮才真常驻：同样条件下实测，带按钮的通知挂了 100 秒仍在屏幕上，
  # 不带按钮的 25 秒就没了。
  # 上面那条断言原先只查 reminder 在不在，盯的是写法不是结果，所以它一直绿着，通知却
  # 照旧自己消失。这条查的是「能不能点」，那才是常驻与否的分界。
  case "$ps_out" in
    *'arguments="dismiss"'*) ;;
    *) fail "notify.ps1 的通知没有可点的按钮（常驻档会被系统忽略，通知 25 秒后自己消失）" ;;
  esac
fi

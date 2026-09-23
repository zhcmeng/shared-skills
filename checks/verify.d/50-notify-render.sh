# ── 通知渲染层 ────────────────────────────────────────────────────
# notify.ps1 的源码里带中文注释，Windows PowerShell 5.1 只在文件带 UTF-8 BOM 时才按
# UTF-8 解析；没有 BOM 它按 GBK 解，中文注释的字节错位还会连带吞掉换行，报出来的行号
# 都对不上（本机实测）。失败方式是静默的：脚本解析不了，通知就再也不弹，会话照开。
# 所以既查 BOM，也真跑一次让 PowerShell 解析全文、顺便验证转义和中文输出。
# watch: plugin/hooks/notify.ps1
ps1="${HOOKS_DIR}/notify.ps1"
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

  # ── 标题跟会话名怎么算对上 ──────────────────────────────────────
  # 这一层唯一有判断的地方就是这条比对规则，而它最容易错在「名字短一截就撞上」。
  # 真窗口在测试里摆不出来，所以留了口子：-Mode match 只比一对字符串，不碰窗口。
  #
  # 规则是「标题等于会话名，或者以『空格 + 会话名』结尾」。窗口标题由 CLI 按
  # `${状态图标} ${会话名}` 写上去（2.1.274 的拼装代码如此），图标会在 ◐ / ◑ / ✳ 之间
  # 变、还有个开关能把它整个去掉，而名字后面什么都没有。所以整条相等不行（栽在图标上），
  # 「名字在里面就行」也不行（栽在撞名上）。
  # PowerShell 往管道里写的是 CRLF，比对前得削掉行尾。源码里写不出反斜杠（会被中转链
  # 路吃掉一个，本仓库栽过），所以回车换行现造 —— 40 那块造反斜杠是同一个道理
  cr="$(awk 'BEGIN{printf "%c",13}')"
  lf="$(awk 'BEGIN{printf "%c",10}')"
  verdict() {
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ps_path" -Mode match -Name "$1" -WindowTitle "$2" 2>&1 | tr -d "${cr}${lf}"
  }
  check_verdict() {   # 会话名 窗口标题 期望 说明
    local got; got="$(verdict "$1" "$2")"
    [ "$got" = "$3" ] && return
    fail "标题比对「$4」：期望 ${3:-（空）}，实际 ${got:-（空）}（会话名=「$1」，标题=「$2」）"
  }
  check_verdict "每日新闻3" "✳ 每日新闻3" yes "标题带着状态图标"
  check_verdict "每日新闻"  "✳ 每日新闻3" no  "名字只是别人的前半截，不能算对上"
  check_verdict "新闻3"    "✳ 每日新闻3" no  "名字只是别人的后半截，也不能算对上"
  check_verdict "每日新闻"  "每日新闻"     yes "没有图标时标题就等于名字"
  check_verdict "每日新闻"  "别的窗口"     no  "标题里没有这个名字"
  check_verdict "每日新闻"  ""             ""  "读不到标题 → 不知道，交给标记"
  check_verdict ""         "✳ 每日新闻3" ""  "会话还没名字 → 不知道，交给标记"
  # 会话名自己带空格是常态（本机在跑的就有「插件的 evals 设置」「claude code 弹窗提醒」
  # 「alphaxiv 研究」）。只要求「以空格 + 名字结尾」的话，名字内部那个空格会被当成前缀
  # 分隔符：名字「设置」会跟「◑ 插件的 evals 设置」对上，把别人的提醒压掉。
  # 标题的格式是死的 —— 第 0 位图标、第 1 位空格、第 2 位起才是名字 —— 所以卡死第 2 位
  check_verdict "设置"           "◑ 插件的 evals 设置" no  "名字只是别人内部的一段"
  check_verdict "evals 设置"     "◑ 插件的 evals 设置" no  "名字带空格时，内部空格不算前缀分隔符"
  check_verdict "插件的 evals 设置" "◑ 插件的 evals 设置" yes "名字里有空格也能对上"
  check_verdict "claude code 弹窗提醒" "◑ claude code 弹窗提醒" yes "名字和格式里都有空格"
  check_verdict "弹窗提醒"        "◑ claude code 弹窗提醒" no  "同一标题里，后半截不算数"
fi

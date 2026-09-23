# ── 插件版本号 ────────────────────────────────────────────────────
# 两件事：
#
# 1. 两个清单里的版本号必须一样。插件按版本号分目录装，两处不一致时，市场上装出去的
#    和 plugin.json 声明的是两个数，升级行为不可预期。
# 2. 改了插件内容却没抬版本号。插件缓存按版本号分目录、内容一致就不再重装，不抬版本
#    就是「改了仓库、跑的仍是旧的那份」，全程不报错。第二会话读技能时读的正是那份副本。
#
# 第 2 条只提示不判失败：抬版本号是按批次做的（一批内容改完统一抬一次），中途红是正常的，
# 判失败只会让人把这个检查当噪声。入口里那条 CR 提示用的是同一个分寸。
#
# 用 node 解析 JSON 而不是 grep：换个缩进、换个字段顺序，grep 就会骗人（60 那块同理）。
# fail 由入口提供，别在这儿重定义；SCRIPT_DIR 指 checks/。
#
# 插件清单位置按两种布局都试：内容整体挪进 plugin/ 之后是 plugin/.claude-plugin/，
# 没挪就是仓库根的 .claude-plugin/。两种布局并存时以 plugin/ 那份为准。
# watch: plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json plugin/skills/ plugin/hooks/ plugin/rules/ plugin/statusline/
ver_root="$(cd "${SCRIPT_DIR}/.." && pwd)"
ver_plugin=""
for ver_p in "${ver_root}/plugin/.claude-plugin/plugin.json" \
             "${ver_root}/.claude-plugin/plugin.json"; do
  if [ -f "$ver_p" ]; then ver_plugin="$ver_p"; break; fi
done
ver_market="${ver_root}/.claude-plugin/marketplace.json"

if [ -z "$ver_plugin" ]; then
  fail "缺插件清单：plugin/.claude-plugin/plugin.json 与 .claude-plugin/plugin.json 都没有"
elif [ ! -f "$ver_market" ]; then
  fail "缺 .claude-plugin/marketplace.json"
else
  # marketplace 的版本号在 plugins[] 里，不在顶层；按名字找本插件那一项
  ver_verdict="$(node -e '
const fs = require("fs");
const [pj, mj] = process.argv.slice(1);
let a;
try {
  a = JSON.parse(fs.readFileSync(pj, "utf8")).version;
} catch (e) {
  console.log("坏 plugin.json：" + e.message); process.exit(0);
}
if (!a) { console.log("plugin.json 里没有 version"); process.exit(0); }

let j;
try {
  j = JSON.parse(fs.readFileSync(mj, "utf8"));
} catch (e) {
  console.log("坏 marketplace.json：" + e.message); process.exit(0);
}
const list = j.plugins || [];
const mine = list.find((p) => p.name === "shared-skills") || list[0];
if (!mine) { console.log("marketplace.json 的 plugins 是空的"); process.exit(0); }
const b = mine.version;
if (!b) { console.log("marketplace.json 里那一项没有 version"); process.exit(0); }

console.log(a === b ? "OK " + a : "MISMATCH " + a + " " + b);
' "$ver_plugin" "$ver_market" 2>&1)"

  case "$ver_verdict" in
    OK\ *)
      ;;
    MISMATCH\ *)
      ver_a="${ver_verdict#MISMATCH }"
      fail "插件版本号两处不一致：plugin.json 是 ${ver_a%% *}，marketplace.json 是 ${ver_a##* }"
      ;;
    *)
      fail "读不出插件版本号：${ver_verdict}"
      ;;
  esac
fi

# 内容动过但没抬版本号：比对「最后一次抬版本」与「最后一次改插件内容」两笔提交的先后。
# 只在 git 可用、且那两笔提交都存在时判；工作区里还没提交的改动不在这一步的射程内。
# 内容路径也按两种布局一起给：git 对没匹配上的路径不作声，多余的几个不影响结果。
if command -v git >/dev/null 2>&1 && [ -d "${ver_root}/.git" ]; then
  ver_bump="$(git -C "$ver_root" log -1 --format=%H -- plugin/.claude-plugin/plugin.json .claude-plugin/plugin.json 2>/dev/null)"
  ver_content="$(git -C "$ver_root" log -1 --format=%H -- \
      plugin/skills plugin/rules plugin/statusline plugin/hooks \
      skills rules statusline hooks 2>/dev/null)"
  if [ -n "$ver_bump" ] && [ -n "$ver_content" ] && [ "$ver_bump" != "$ver_content" ]; then
    # bump 是 content 的祖先 = 抬完版本之后内容又动过
    if git -C "$ver_root" merge-base --is-ancestor "$ver_bump" "$ver_content" 2>/dev/null; then
      ver_short="$(git -C "$ver_root" log -1 --format=%h "$ver_bump" 2>/dev/null)"
      ver_n="$(git -C "$ver_root" rev-list --count "${ver_bump}..${ver_content}" 2>/dev/null)"
      echo "提示：插件内容动过、版本号还没抬——最后一次抬版本是 ${ver_short}，之后又有 ${ver_n:-若干} 个提交改了 plugin/ 下的内容。交付前把 plugin.json 与 marketplace.json 两个版本号一起抬上去。"
    fi
  fi
fi

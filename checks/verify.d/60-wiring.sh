# ── hooks.json 接线 ────────────────────────────────────────────────
# 四条通知 hook 少一条，对应那个时刻就再也不提醒，而且不报错。
# 用 node 解析而不是 grep —— JSON 换个缩进、换个字段顺序，grep 就会骗人。
# watch: plugin/hooks/hooks.json
hook_err="$(node -e '
const fs = require("fs");
const j = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const errs = [];
const hooks = j.hooks || {};
if (!hooks.SessionStart) errs.push("SessionStart 那条被改没了");
const events = ["UserPromptSubmit", "Stop", "PreToolUse", "Notification"];
for (const ev of events) {
  const groups = hooks[ev];
  if (!Array.isArray(groups) || groups.length === 0) { errs.push("缺 " + ev); continue; }
  let hit = null;
  for (const g of groups) for (const h of (g.hooks || [])) {
    if (/run-hook\.cmd"\s+notify/.test(h.command || "")) hit = h;
  }
  if (!hit) { errs.push(ev + " 没有指向 run-hook.cmd notify"); continue; }
  if (hit.async !== true) errs.push(ev + " 没挂后台（async 不是 true），会挡住操作");
}
let pre = false;
for (const g of (hooks.PreToolUse || [])) if (g.matcher === "AskUserQuestion") pre = true;
if (!pre) errs.push("PreToolUse 没有匹配 AskUserQuestion（弹选择题那一刻接不住）");
if (errs.length) { console.error(errs.join("；")); process.exit(1); }
' "${HOOKS_DIR}/hooks.json" 2>&1)" || fail "hooks.json 接线不对：${hook_err}"

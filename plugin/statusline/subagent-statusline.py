#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude Code 子代理面板行：每个子代理显示自己的费用 / 缓存命中率 / token / 已运行多久。

Claude Code 从 stdin 喂进来 {"columns": N, "tasks": [...], ...}；其中每个 task 是
面板里的一行，字段为 id / name / type / status / description / label / startTime /
model / effort / contextWindowSize / tokenCount / tokenSamples / cwd。

同一条回复会被按内容块拆成多条记录、每条都带同一份完整 usage，所以先按
message.id 收敛成一条再累加，否则费用和 token 会按内容块个数翻倍。

行数据里只有 tokenCount 一个总数，没有缓存命中/未命中的拆分，算不出费用。
但 task 的 id 就是 agent id，其用量记录在
    <会话记录同名目录>/subagents/agent-<id>.jsonl
里，带完整的 hit / miss / output 三类计数，因此本脚本去读那份记录来算。

fork 型代理（把一个代理的上下文整个复制出去另开一个）的记录文件开头带着父代理那几次
调用，message.id 与父代理文件里的完全一样——同一份记录被抄了一份，不是它自己发起的。
按 id 收敛只在本文件内做，跨文件就漏了，会把父代理的开销算到 fork 头上（实测多出
三到四成）。所以遇到有父代理的，还要读一遍父代理的记录，把那些 id 排掉，见
inherited_ids()。

时长：口径与主状态栏一致，都算挂钟时间（含等待与停顿）。还在跑的取「现在 −
      startTime」；已结束的必须停在它末条记录的时刻——任务行里只有 startTime、
      没有结束时刻，用「现在」会让跑完的代理一直涨下去。

输出：每个要覆盖的行写一行 JSON 到 stdout —— {"id": "<task id>", "content": "<行内容>"}。
不输出的行保持默认渲染。
"""

import datetime
import json
import os
import sys

# ── 价目表：元 / 百万 tokens，{计费项: (空闲, 高峰)} ──────────────
RATES = {
    "deepseek-flash": {"hit": (0.02, 0.04), "miss": (1.00, 2.00), "out": (4.00, 8.00)},
    "deepseek-v4-pro": {"hit": (0.15, 0.30), "miss": (4.50, 9.00), "out": (13.50, 27.00)},
}
FALLBACK_MODEL = "deepseek-flash"
MODEL_ALIASES = {
    "deepseek-v4-flash": "deepseek-flash",
    "deepseek-chat": "deepseek-flash",
    "deepseek-reasoner": "deepseek-flash",
    "deepseek-v4-flash-vision-exp": "deepseek-flash",
}

PEAK_WINDOWS = (
    (datetime.time(9, 0), datetime.time(12, 0)),
    (datetime.time(14, 0), datetime.time(18, 0)),
)
CN_TZ = datetime.timezone(datetime.timedelta(hours=8))


def is_peak(ts):
    if ts is None:
        return True
    local = ts.astimezone(CN_TZ)
    if local.weekday() >= 5:
        return False
    t = local.time()
    return any(start <= t < end for start, end in PEAK_WINDOWS)


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def rates_for(model):
    if not isinstance(model, str):
        return RATES[FALLBACK_MODEL]
    return RATES.get(MODEL_ALIASES.get(model, model), RATES[FALLBACK_MODEL])


def dedup_rank(msg):
    """同一条回复被拆成多条记录时，用这个分数挑出该留下的一条。

    Claude Code 把一条回复的思考、正文、工具调用各写成一条记录，每条都带同一份完整
    usage 和同一个 message.id；流式过程中的中间记录则是 output_tokens 偏小、
    stop_reason 还没有值。所以先比有没有 stop_reason（有的大），再比 output_tokens。
    主状态栏 statusline.py 里有一份同样的，见那边的说明。
    """
    usage = msg.get("usage")
    out = usage.get("output_tokens") if isinstance(usage, dict) else 0
    return (1 if msg.get("stop_reason") else 0, out or 0)


def summarize(path, skip_ids=frozenset()):
    """读某个 agent 的记录，返回 (命中, 未命中, 输出, 费用, 是否跨高峰, 是否跨空闲, 末条时间)。

    读不到返回 None。末条时间给已结束的代理当终点用，见文件头的时长说明。
    同一条回复的多条记录先按 message.id 收敛成一条再累加，否则费用和 token 会按
    内容块个数翻倍（真实会话实测被放大 2.6~4.2 倍）。
    skip_ids 是父代理那边已经有的 id（fork 抄过来的历史），整条跳过不计数。
    """
    kept = {}

    try:
        f = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return None
    with f:
        for line in f:
            if '"usage"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message")
            if not isinstance(msg, dict) or not isinstance(msg.get("usage"), dict):
                continue

            key = msg.get("id")
            if not isinstance(key, str) or not key:
                key = ("无 id", len(kept))
            elif key in skip_ids:
                continue
            prev = kept.get(key)
            if prev is None or dedup_rank(msg) > dedup_rank(prev[0]):
                kept[key] = (msg, rec)

    if not kept:
        return None

    hit = miss = out = 0
    cost = 0.0
    saw_peak = saw_off = False
    last_ts = None

    for msg, rec in kept.values():
        usage = msg["usage"]

        h = usage.get("cache_read_input_tokens") or 0
        m = (usage.get("input_tokens") or 0) + (
            usage.get("cache_creation_input_tokens") or 0
        )
        o = usage.get("output_tokens") or 0
        hit += h
        miss += m
        out += o

        ts = parse_ts(rec.get("timestamp"))
        if ts is not None and (last_ts is None or ts > last_ts):
            last_ts = ts
        peak = is_peak(ts)
        if peak:
            saw_peak = True
        else:
            saw_off = True

        rate = rates_for(msg.get("model"))
        k = 1 if peak else 0
        cost += (
            h * rate["hit"][k] + m * rate["miss"][k] + o * rate["out"][k]
        ) / 1_000_000

    return hit, miss, out, cost, saw_peak, saw_off, last_ts


def agent_transcript(session_dir, agent_id):
    if not session_dir or not agent_id:
        return None
    p = os.path.join(session_dir, "subagents", f"agent-{agent_id}.jsonl")
    return p if os.path.isfile(p) else None


# 兄弟 fork 常常指向同一个父代理，记录读过一次就留着，别每个 task 重读一遍
_IDS_CACHE = {}


def message_ids(path):
    """一个记录文件里出现过的 message.id 集合。读不到就给空集。"""
    if path not in _IDS_CACHE:
        ids = set()
        try:
            f = open(path, encoding="utf-8", errors="replace")
        except OSError:
            _IDS_CACHE[path] = ids
            return ids
        with f:
            for line in f:
                if '"usage"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                msg = rec.get("message")
                if isinstance(msg, dict) and isinstance(msg.get("id"), str):
                    ids.add(msg["id"])
        _IDS_CACHE[path] = ids
    return _IDS_CACHE[path]


def inherited_ids(session_dir, agent_id):
    """这个代理从父代理那里抄来的 message.id 集合，算自己的开销时整条跳过。

    fork 型代理（meta 里 isFork 为真）的记录文件开头是父代理那几次调用的整份复制，
    它自己没发起过；这些 id 在父代理的记录里也有，不排掉就会把父代理的开销再算一遍
    （实测这样的行多出三到四成）。

    只看 parentAgentId 存在与否，不看 isFork：同一次调用只可能由一个代理发起，凡是在
    父代理记录里出现过的 id 都不可能是子代理自己的。非 fork 的子代理本来就没有这种记录，
    排了也是空集，不影响。读不到 meta、或父代理的记录不在，一律给空集，维持原样。
    """
    if not session_dir or not agent_id:
        return frozenset()
    meta_path = os.path.join(session_dir, "subagents", f"agent-{agent_id}.meta.json")
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return frozenset()
    if not isinstance(meta, dict):
        return frozenset()
    parent = meta.get("parentAgentId")
    if not isinstance(parent, str) or not parent:
        return frozenset()
    parent_path = agent_transcript(session_dir, parent)
    return frozenset(message_ids(parent_path)) if parent_path else frozenset()


def resolve_session_dir(data):
    """定位本会话的 subagents 目录。优先用 transcript_path，退化到按 session_id 搜。"""
    tp = data.get("transcript_path")
    if isinstance(tp, str) and tp:
        d = os.path.join(os.path.splitext(tp)[0], "subagents")
        if os.path.isdir(d):
            return os.path.dirname(d)

    sid = data.get("session_id")
    if not isinstance(sid, str) or not sid:
        return None
    root = os.path.expanduser("~/.claude/projects")
    try:
        projects = os.listdir(root)
    except OSError:
        return None
    for proj in projects:
        d = os.path.join(root, proj, sid)
        if os.path.isdir(os.path.join(d, "subagents")):
            return d
    return None


def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def fmt_money(y):
    if y == 0:
        return "0"
    return f"{y:.4f}" if y < 0.01 else f"{y:.2f}"


def fmt_duration(ms):
    """挂钟时长，紧凑写：45s / 12m / 2h05m / 1d03h。

    取不到就返回 None，由调用方决定不显示这一截——不编一个数出来充数。
    主状态栏 statusline.py 里有一份同样的。两份独立放着，是因为 hook 只把这两个
    文件复制到配置目录，抽成共享模块就得多同步一个文件，不划算。
    """
    if not isinstance(ms, (int, float)) or ms < 0:
        return None
    secs = int(ms // 1000)
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m"
    hours, mins = divmod(mins, 60)
    if hours < 24:
        return f"{hours}h{mins:02d}m"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours:02d}h"


# 已经跑完的代理，时长要停在末条记录；其余（pending / running / paused）按「现在」算
FINISHED_STATUSES = ("completed", "failed", "killed")

# 起点字段是外部喂进来的，不能全信。0 在这套数据里是「未设置」的哨兵值（不是 1970 年），
# 顺着算会得出「20712d01h」这种荒谬结果——那等于编一个数出来充数，不如不显示。
# 一年是给「算出来的时长」兜底的上限：没有代理能跑这么久。
MAX_ELAPSED_MS = 365 * 24 * 60 * 60 * 1000


def parse_start(v):
    """任务行里的 startTime 是 Date.now() 的毫秒整数；字符串形式也认，以防格式变。"""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(v / 1000, tz=datetime.timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    return parse_ts(v)


def elapsed_ms(task, last_ts):
    """这个代理已经跑了多久（挂钟，含等待与停顿，与主状态栏同口径）。

    起点取不到、或算出来的数不可信（倒挂、超过 MAX_ELAPSED_MS），一律返回 None，
    由 fmt_duration 决定不显示这一截。
    """
    start = parse_start(task.get("startTime"))
    if start is None:
        return None
    if task.get("status") in FINISHED_STATUSES:
        # 跑完的代理必须停在末条记录。没有记录就没有终点，这时宁可这一截不显示，
        # 也不能退回用「现在」——那样数字会一直涨，比不显示更误导。
        if last_ts is None:
            return None
        end = last_ts
    else:
        end = datetime.datetime.now(datetime.timezone.utc)
    delta = (end - start).total_seconds() * 1000
    if delta < 0 or delta > MAX_ELAPSED_MS:
        return None
    return delta


def clip(s, width):
    s = str(s or "")
    return s if len(s) <= width else s[: max(0, width - 1)] + "…"


def main():
    # 按字节读再显式按 UTF-8 解码：Windows 上文本模式 stdin 默认用 GBK，
    # 会把 Claude Code 喂进来的中文描述解成乱码。
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
    except Exception:
        return

    try:
        data = json.loads(raw)
    except ValueError:
        return

    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        return

    columns = data.get("columns")
    width = columns if isinstance(columns, int) and columns > 20 else 120
    session_dir = resolve_session_dir(data)

    out_lines = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        if not isinstance(tid, str) or not tid:
            continue

        stats = None
        path = agent_transcript(session_dir, tid)
        if path:
            stats = summarize(path, inherited_ids(session_dir, tid))

        # 行首放描述，替代被覆盖掉的默认渲染（默认是 name · description · token 数）
        label = task.get("description") or task.get("label") or task.get("name") or tid

        if stats:
            hit, miss, out, cost, saw_peak, saw_off, last_ts = stats
            total = hit + miss + out
            denom = hit + miss
            pct = (hit / denom * 100) if denom else 0.0
            zone = (
                "峰" if saw_peak and not saw_off
                else "闲" if saw_off and not saw_peak
                else "峰闲"
            )
            body = (
                f"¥{fmt_money(cost)}({zone}) · 缓存命中 {pct:.1f}% · "
                f"总token {fmt_tokens(total)}"
            )
        else:
            last_ts = None
            # 拿不到记录（子代理可能还没落盘）：退回行数据里的 tokenCount
            body = f"{fmt_tokens(task.get('tokenCount') or 0)} tok"

        elapsed = fmt_duration(elapsed_ms(task, last_ts))
        if elapsed:
            body += f" · {elapsed}"

        text = clip(label, max(10, width - len(body) - 4)) + "  " + body
        out_lines.append(json.dumps({"id": tid, "content": text}, ensure_ascii=False))

    if out_lines:
        sys.stdout.write("\n".join(out_lines) + "\n")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()

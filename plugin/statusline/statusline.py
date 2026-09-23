#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude Code 状态栏：本会话总 token / 缓存命中率 / 费用 / 已运行多久。

输入：Claude Code 从 stdin 喂进来的会话 JSON（取其中的 transcript_path，以及
      cost.total_duration_ms）。
数据：会话累计 token 不在 stdin JSON 里（context_window.current_usage 只是最后一次
      调用的数字），只能逐条累计会话记录里的 usage。同一条回复会被按内容块拆成多条
      记录、每条都带同一份 usage，累计前先按 message.id 收敛成一条（见 dedup_rank）。
      收敛是在本会话的**所有**记录文件之间做的，不限于单个文件——fork 型子代理会把
      父代理的记录抄进自己的文件，同一份记录因此出现在多个文件里，跨文件收敛才不会
      重复计。
时长：直接取 stdin 里的 cost.total_duration_ms（会话挂钟时长，含等待与停顿），
      不从记录里推。记录只能给出「首末两条之间」的跨度，开头到第一条、最后一条
      到现在这两段都会漏掉，代理越闲漏得越多。
计价：按每条记录自己的时间戳判定空闲/高峰，按该条记录的模型选价目，逐条累加。

价目来源：DeepSeek 官方定价页 https://api-docs.deepseek.com/zh-cn/quick_start/pricing
  高峰时段（官方脚注 3）：北京时间周一至周五 9:00-12:00、14:00-18:00，其余为空闲。
  注意：官方未说明跨时段请求按发起还是完成时刻计价，此处按记录写入时刻近似。
"""

import datetime
import json
import os
import sys

# ── 价目表：元 / 百万 tokens，{计费项: (空闲, 高峰)} ──────────────
RATES = {
    "deepseek-flash": {
        "hit": (0.02, 0.04),    # 输入 · 缓存命中
        "miss": (1.00, 2.00),   # 输入 · 缓存未命中
        "out": (4.00, 8.00),    # 输出
    },
    "deepseek-v4-pro": {
        "hit": (0.15, 0.30),
        "miss": (4.50, 9.00),
        "out": (13.50, 27.00),
    },
}
FALLBACK_MODEL = "deepseek-flash"

# 模型别名 → 价目表键（官方旧名仍由 V4.1-Flash 服务，按 Flash 价计费）
MODEL_ALIASES = {
    "deepseek-v4-flash": "deepseek-flash",
    "deepseek-chat": "deepseek-flash",
    "deepseek-reasoner": "deepseek-flash",
    "deepseek-v4-flash-vision-exp": "deepseek-flash",
}

# ── 高峰时段：北京时间、周一至周五 ────────────────────────────────
PEAK_WINDOWS = (
    (datetime.time(9, 0), datetime.time(12, 0)),
    (datetime.time(14, 0), datetime.time(18, 0)),
)

CN_TZ = datetime.timezone(datetime.timedelta(hours=8))


def is_peak(ts):
    """ts 为带时区的 datetime。取不到时间时按高峰算（宁可高估，不低估）。"""
    if ts is None:
        return True
    local = ts.astimezone(CN_TZ)
    if local.weekday() >= 5:  # 周六、周日全天空闲
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
    key = MODEL_ALIASES.get(model, model)
    return RATES.get(key, RATES[FALLBACK_MODEL])


def dedup_rank(msg):
    """同一条回复被拆成多条记录时，用这个分数挑出该留下的一条。

    Claude Code 把一条回复的思考、正文、工具调用各写成一条记录，每条都带同一份完整
    usage 和同一个 message.id；流式过程中的中间记录则是 output_tokens 偏小、
    stop_reason 还没有值。所以先比有没有 stop_reason（有的大），再比 output_tokens。
    """
    usage = msg.get("usage")
    out = usage.get("output_tokens") if isinstance(usage, dict) else 0
    return (1 if msg.get("stop_reason") else 0, out or 0)


def collect(paths):
    # 先按 message.id 把同一次调用的多条记录收敛成一条，再统一累加：照着行数累加
    # 会把一次调用算成内容块的个数倍（真实会话实测被放大 2.6~4.2 倍）。取不到 id 的
    # 记录各算各的——宁可多算，也不能把两次不同的调用并成一次。
    kept = {}

    for path in paths:
        try:
            f = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with f:
            for line in f:
                if '"usage"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                msg = rec.get("message")
                if not isinstance(msg, dict):
                    continue
                if not isinstance(msg.get("usage"), dict):
                    continue

                key = msg.get("id")
                if not isinstance(key, str) or not key:
                    key = ("无 id", len(kept))
                prev = kept.get(key)
                if prev is None or dedup_rank(msg) > dedup_rank(prev[0]):
                    kept[key] = (msg, rec)

    hit = miss = out = 0
    cost = 0.0
    saw_peak = saw_off = False

    for msg, rec in kept.values():
        usage = msg["usage"]

        h = usage.get("cache_read_input_tokens") or 0
        # 缓存创建按"未命中输入"计价：官方价目表无独立的缓存写入计费项
        m = (usage.get("input_tokens") or 0) + (
            usage.get("cache_creation_input_tokens") or 0
        )
        o = usage.get("output_tokens") or 0

        hit += h
        miss += m
        out += o

        peak = is_peak(parse_ts(rec.get("timestamp")))
        if peak:
            saw_peak = True
        else:
            saw_off = True

        rate = rates_for(msg.get("model"))
        k = 1 if peak else 0
        cost += (h * rate["hit"][k] + m * rate["miss"][k] + o * rate["out"][k]) / 1_000_000

    return hit, miss, out, cost, saw_peak, saw_off


def transcript_set(main_path):
    """主会话记录 + 该会话派生的全部子代理记录。

    子代理记录位于 <会话记录同名目录>/subagents/agent-*.jsonl，
    它们的用量不在主记录里，必须一并计入才算"本会话"的完整开销。
    """
    paths = [main_path]
    sub_dir = os.path.join(os.path.splitext(main_path)[0], "subagents")
    try:
        names = os.listdir(sub_dir)
    except OSError:
        return paths
    paths.extend(
        os.path.join(sub_dir, n)
        for n in names
        if n.startswith("agent-") and n.endswith(".jsonl")
    )
    return paths


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
    本函数在 subagent-statusline.py 里有一份同样的，见那边的说明。
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


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    path = data.get("transcript_path")
    if not path:
        return

    try:
        hit, miss, out, cost, saw_peak, saw_off = collect(transcript_set(path))
    except OSError:
        return

    total = hit + miss + out
    if total == 0:
        return

    denom = hit + miss
    rate = (hit / denom * 100) if denom else 0.0
    zone = "峰" if saw_peak and not saw_off else ("闲" if saw_off and not saw_peak else "峰闲")

    cost_info = data.get("cost")
    elapsed = fmt_duration(
        cost_info.get("total_duration_ms") if isinstance(cost_info, dict) else None
    )
    tail = f" · {elapsed}" if elapsed else ""

    print(
        f"本会话 ¥{fmt_money(cost)}({zone}) · 缓存命中 {rate:.1f}% · "
        f"总token {fmt_tokens(total)}{tail}"
    )


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()

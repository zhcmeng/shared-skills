#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude Code 状态栏：本会话总 token / 缓存命中率 / 费用。

输入：Claude Code 从 stdin 喂进来的会话 JSON（取其中的 transcript_path）。
数据：会话累计 token 不在 stdin JSON 里（context_window.current_usage 只是最后一次
      调用的数字），只能逐条累计会话记录里的 usage。
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


def collect(paths):
    hit = miss = out = 0
    cost = 0.0
    saw_peak = saw_off = False

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
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue

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
                cost += (
                    h * rate["hit"][k] + m * rate["miss"][k] + o * rate["out"][k]
                ) / 1_000_000

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

    print(
        f"本会话 ¥{fmt_money(cost)}({zone}) · 缓存命中 {rate:.1f}% · "
        f"总token {fmt_tokens(total)}"
    )


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()

#!/usr/bin/env python3
"""每日网关审阅：从流量日志里找出该写进规则的域名，以及白烧代理出口额度的流量。

与 clash_traffic.py 的分工：那个负责采集（launchd 每 10 分钟 collect），这个负责审阅。
配套 ROUTING.md「维护 SOP」。不需要 API 密钥，只读本地 JSONL。

  python3 daily_review.py              # 审阅最近 1 天，输出 markdown 到 stdout
  python3 daily_review.py 7            # 审阅最近 7 天
  python3 daily_review.py 1 --out DIR  # 写入 DIR/<日期>.md

判据说明（出口一律取链路最后一跳，`Bilibili>DIRECT` 算直连）：
  - 命中 `Match:` 兜底且走代理 = 没有任何规则覆盖它 → 规则候选
  - 走了一个「可选 DIRECT」的策略组却选在代理上 → 改组选择即可，不必加规则
  - AI 流量出现多个出口 = 出口 IP 在切换，有风控风险
"""
import glob
import json
import os
import sys
import time
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LOG_DIR = os.environ.get("CLASH_LOG_DIR", os.path.join(REPO, "inno", "traffic-logs"))

# 风控敏感：这些域名必须走住宅，走别处就是账号风险
AI_KEYWORDS = ("openai", "chatgpt", "anthropic", "claude", "gemini", "oaistatic",
               "oaiusercontent", "perplexity", "cursor", "x.ai", "grok", "copilot")
MB = 1e6


def load(days):
    files = sorted(glob.glob(os.path.join(LOG_DIR, "*.jsonl")))[-days:]
    if not files:
        sys.exit(f"{LOG_DIR} 下没有日志，确认 launchd 采集还在跑（见 ROUTING.md）")
    rows = []
    for fp in files:
        for line in open(fp):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return files, rows


def base_domain(host):
    """把 cache11-lax2.steamcontent.com 归并到 steamcontent.com，便于给出一条规则覆盖一片。"""
    parts = host.rstrip(".").split(".")
    if len(parts) < 2 or not parts[-1].isalpha():
        return host  # IP 或 sniff 失败的 hash
    if len(parts) >= 3 and parts[-2] in ("com", "net", "org", "co", "gov", "edu"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def unsniffed(host):
    """TLS sniff 失败时 host 是一串 hex，没有域名可写规则。"""
    return "." not in host and all(c in "0123456789abcdef" for c in host.lower())


def exit_of(r):
    """链路最后一跳就是实际出口：节点名或 DIRECT。"""
    return ",".join(sorted({c.split(">")[-1] for c in r["chains"]}))


def is_direct(r):
    return exit_of(r) == "DIRECT"


def group_of(r):
    return ",".join(sorted({c.split(">")[0] for c in r["chains"]}))


def analyze(rows):
    exits = defaultdict(int)
    ai = defaultdict(lambda: {"b": 0, "n": 0})
    uncovered = defaultdict(lambda: {"b": 0, "hosts": set(), "groups": set()})
    by_group = defaultdict(lambda: {"b": 0, "rule": set(), "groups": set()})
    totals = defaultdict(int)

    for r in rows:
        byte = r["down"] + r["up"]
        totals["all"] += byte
        totals["direct" if is_direct(r) else "proxy"] += byte
        exits[exit_of(r)] += byte
        if any(k in r["host"].lower() for k in AI_KEYWORDS):
            ai[exit_of(r)]["b"] += byte
            ai[exit_of(r)]["n"] += 1
        if is_direct(r):
            continue
        dom = base_domain(r["host"])
        if all(ru.startswith("Match") for ru in r["rule"]):
            if unsniffed(dom):
                totals["unsniffed"] += byte
                continue  # 没域名可写规则，单独统计
            d = uncovered[dom]
            d["b"] += byte
            d["hosts"].add(r["host"])
            d["groups"].add(group_of(r))
        else:
            m = by_group[dom]
            m["b"] += byte
            m["rule"] |= set(r["rule"])
            m["groups"].add(group_of(r))
    return exits, ai, uncovered, by_group, totals


def render(files, rows, days):
    exits, ai, uncovered, by_group, totals = analyze(rows)
    out = []
    w = out.append
    w(f"# 家庭网关审阅 {time.strftime('%Y-%m-%d %H:%M')}")
    w("")
    w(f"数据窗口：最近 {days} 天（{os.path.basename(files[0])} ~ {os.path.basename(files[-1])}），"
      f"{len(rows)} 条聚合记录，总流量 {totals['all'] / 1e9:.2f} GB"
      f"（直连 {totals['direct'] / 1e9:.2f} GB / 代理 {totals['proxy'] / 1e9:.2f} GB）")
    w("")

    w("## 1. 实际出口分布")
    w("")
    w("| 出口 | 流量 |")
    w("|---|---|")
    for k, b in sorted(exits.items(), key=lambda kv: -kv[1])[:10]:
        w(f"| `{k[:48]}` | {b / 1e9:.2f} GB |")
    w("")

    w("## 2. AI / 风控敏感流量出口")
    w("")
    if not ai:
        w("本窗口无 AI 流量。")
    else:
        w("| 出口 | 流量 | 连接数 |")
        w("|---|---|---|")
        for k, s in sorted(ai.items(), key=lambda kv: -kv[1]["b"]):
            w(f"| `{k[:48]}` | {s['b'] / MB:.1f} MB | {s['n']} |")
        if len([k for k in ai if k != "DIRECT"]) > 1:
            w("")
            w("**AI 流量出现了多个代理出口**：出口 IP 在切换，账号风控风险更高，确认是否有意为之。")
    w("")

    w("## 3. 规则候选：走代理但没有任何规则覆盖（命中 `Match:` 兜底）")
    w("")
    if not uncovered:
        w("无。")
    else:
        w("| 注册域 | 流量 | 子域数 | 当前组 |")
        w("|---|---|---|---|")
        for d, s in sorted(uncovered.items(), key=lambda kv: -kv[1]["b"])[:20]:
            w(f"| `{d}` | {s['b'] / MB:.1f} MB | {len(s['hosts'])} | {','.join(sorted(s['groups']))[:28]} |")
    if totals.get("unsniffed"):
        w("")
        w(f"另有 {totals['unsniffed'] / MB:.1f} MB 走代理的流量 TLS sniff 失败（host 是 hex 串），"
          "无域名可写规则，本次不作为候选。")
    w("")

    w("## 4. 已有规则命中、走代理的流量大户")
    w("")
    w("如果所在策略组可选 DIRECT（如 Apple / Steam / Microsoft），改组选择比加规则更直接。")
    w("")
    if not by_group:
        w("无。")
    else:
        w("| 注册域 | 流量 | 命中规则 | 策略组 |")
        w("|---|---|---|---|")
        for d, s in sorted(by_group.items(), key=lambda kv: -kv[1]["b"])[:15]:
            w(f"| `{d}` | {s['b'] / MB:.1f} MB | {','.join(sorted(s['rule']))[:34]} "
              f"| {','.join(sorted(s['groups']))[:24]} |")
    w("")
    return "\n".join(out)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    days = int(args[0]) if args else 1
    files, rows = load(days)
    text = render(files, rows, days)
    if "--out" in sys.argv:
        out_dir = sys.argv[sys.argv.index("--out") + 1]
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, time.strftime("%Y-%m-%d") + ".md")
        with open(path, "w") as f:
            f.write(text + "\n")
        print(f"审阅报告 -> {path}")
    else:
        print(text)

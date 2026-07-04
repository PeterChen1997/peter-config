#!/usr/bin/env python3
"""流量画像工具：轮询 OpenClash API /connections，按域名聚合流量，找出该挪去「大流量」组的流量大户。

配套 ROUTING.md「维护 SOP」使用。密钥不落盘，从环境变量读取：

  export CLASH_API_SECRET=xxx        # OpenClash → 插件设置 → 管理页面密码
  python3 clash_traffic.py                    # 单次快照（含存活连接的累计流量）
  python3 clash_traffic.py poll 300           # 持续轮询 300 秒（能覆盖短连接）

可选环境变量：CLASH_API_BASE（默认 http://192.168.2.190:9090）
"""
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict

BASE = os.environ.get("CLASH_API_BASE", "http://192.168.2.190:9090")
SECRET = os.environ.get("CLASH_API_SECRET", "")


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + SECRET})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.load(r)


def host_of(c):
    m = c["metadata"]
    return m.get("host") or m.get("sniffHost") or m.get("destinationIP") or "?"


def snapshot():
    d = fetch("/connections")
    conns = d.get("connections") or []
    best = {c["id"]: row_of(c) for c in conns}
    report(d, best)


def row_of(c):
    chains = ">".join(reversed(c.get("chains", [])))
    rule = c.get("rule", "") + ":" + c.get("rulePayload", "")
    return (host_of(c), c.get("download", 0), c.get("upload", 0), chains, rule)


def poll(seconds):
    """按连接 id 记录累计流量最大值，结束后按域名汇总（覆盖轮询期间开启/关闭的连接）"""
    best = {}
    t0 = time.time()
    total = None
    while time.time() - t0 < seconds:
        try:
            total = fetch("/connections")
            for c in total.get("connections") or []:
                row = row_of(c)
                prev = best.get(c["id"])
                if not prev or row[1] + row[2] > prev[1] + prev[2]:
                    best[c["id"]] = row
        except Exception as e:
            print("poll error:", e, file=sys.stderr)
        time.sleep(4)
    report(total or {}, best)


def report(d, best):
    stats = defaultdict(lambda: {"down": 0, "up": 0, "chains": set(), "rule": set()})
    for host, down, up, chains, rule in best.values():
        s = stats[host]
        s["down"] += down
        s["up"] += up
        s["chains"].add(chains)
        s["rule"].add(rule)
    print(f"连接数(累计观测): {len(best)}  内核总下载: {d.get('downloadTotal', 0) / 1e9:.2f} GB  总上传: {d.get('uploadTotal', 0) / 1e9:.2f} GB")
    rows = sorted(stats.items(), key=lambda kv: -(kv[1]["down"] + kv[1]["up"]))
    print(f"{'域名/IP':<46} {'下载MB':>9} {'上传MB':>9}  出口链路 | 命中规则")
    for host, s in rows[:40]:
        chains = ",".join(sorted(s["chains"]))[:60]
        rule = ",".join(sorted(s["rule"]))[:70]
        print(f"{host:<46} {s['down'] / 1e6:>9.1f} {s['up'] / 1e6:>9.1f}  {chains} | {rule}")


if __name__ == "__main__":
    if not SECRET:
        sys.exit("请先 export CLASH_API_SECRET=<OpenClash 管理页面密码>")
    if sys.argv[1:2] == ["poll"]:
        poll(int(sys.argv[2]) if len(sys.argv) > 2 else 240)
    else:
        snapshot()

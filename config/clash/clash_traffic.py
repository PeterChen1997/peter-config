#!/usr/bin/env python3
"""流量画像工具：轮询 OpenClash API /connections，按域名聚合流量，找出该挪去「大流量」组的流量大户。

配套 ROUTING.md「维护 SOP」使用。密钥不落盘进仓库，从环境变量读取：

  export CLASH_API_SECRET=xxx        # OpenClash → 插件设置 → 管理页面密码
  python3 clash_traffic.py                    # 单次快照（含存活连接的累计流量）
  python3 clash_traffic.py poll 300           # 持续轮询 300 秒并打印报告
  python3 clash_traffic.py collect 240        # 轮询 240 秒，聚合结果追加到 JSONL 日志（launchd 定时用）
  python3 clash_traffic.py report 7           # 汇总最近 7 天日志，按出口分组列流量大户

日志目录：默认 <repo>/inno/traffic-logs/（gitignored），可用 CLASH_LOG_DIR 覆盖。
可选环境变量：CLASH_API_BASE（默认 http://192.168.2.190:9090）
"""
import glob
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict

BASE = os.environ.get("CLASH_API_BASE", "http://192.168.2.190:9090")
SECRET = os.environ.get("CLASH_API_SECRET", "")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.environ.get("CLASH_LOG_DIR", os.path.join(REPO, "inno", "traffic-logs"))


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + SECRET})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.load(r)


def host_of(c):
    m = c["metadata"]
    return m.get("host") or m.get("sniffHost") or m.get("destinationIP") or "?"


def row_of(c):
    chains = ">".join(reversed(c.get("chains", [])))
    rule = c.get("rule", "") + ":" + c.get("rulePayload", "")
    return (host_of(c), c.get("download", 0), c.get("upload", 0), chains, rule)


def sample(seconds):
    """按连接 id 记录累计流量最大值（覆盖轮询期间开启/关闭的连接）"""
    best = {}
    t0 = time.time()
    while time.time() - t0 < seconds:
        try:
            for c in fetch("/connections").get("connections") or []:
                row = row_of(c)
                prev = best.get(c["id"])
                if not prev or row[1] + row[2] > prev[1] + prev[2]:
                    best[c["id"]] = row
        except Exception as e:
            print("poll error:", e, file=sys.stderr)
        time.sleep(4)
    return best


def aggregate(rows):
    stats = defaultdict(lambda: {"down": 0, "up": 0, "chains": set(), "rule": set()})
    for host, down, up, chains, rule in rows:
        s = stats[host]
        s["down"] += down
        s["up"] += up
        s["chains"].add(chains)
        s["rule"].add(rule)
    return stats


def print_report(stats, nconn, title=""):
    if title:
        print(title)
    print(f"连接数(累计观测): {nconn}")
    rows = sorted(stats.items(), key=lambda kv: -(kv[1]["down"] + kv[1]["up"]))
    print(f"{'域名/IP':<46} {'下载MB':>9} {'上传MB':>9}  出口链路 | 命中规则")
    for host, s in rows[:40]:
        chains = ",".join(sorted(s["chains"]))[:60]
        rule = ",".join(sorted(s["rule"]))[:70]
        print(f"{host:<46} {s['down'] / 1e6:>9.1f} {s['up'] / 1e6:>9.1f}  {chains} | {rule}")


def snapshot():
    d = fetch("/connections")
    best = {c["id"]: row_of(c) for c in d.get("connections") or []}
    print_report(aggregate(best.values()), len(best))


def poll(seconds):
    best = sample(seconds)
    print_report(aggregate(best.values()), len(best))


def collect(seconds):
    """采样后按域名聚合，追加到当日 JSONL 文件（launchd 每 10 分钟调用一次）"""
    best = sample(seconds)
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = int(time.time())
    path = os.path.join(LOG_DIR, time.strftime("%Y-%m-%d") + ".jsonl")
    with open(path, "a") as f:
        for host, s in aggregate(best.values()).items():
            if s["down"] + s["up"] < 100_000:  # 忽略 <100KB 的噪音
                continue
            f.write(json.dumps({"ts": ts, "host": host, "down": s["down"], "up": s["up"],
                                "chains": sorted(s["chains"]), "rule": sorted(s["rule"])},
                               ensure_ascii=False) + "\n")
    print(f"collected {len(best)} conns -> {path}")


def report(days):
    """汇总最近 N 天日志：按出口分类，突出「走住宅但流量大」的优化候选"""
    files = sorted(glob.glob(os.path.join(LOG_DIR, "*.jsonl")))[-days:]
    if not files:
        sys.exit(f"{LOG_DIR} 下没有日志，先配置 launchd 定时跑 collect（见 ROUTING.md）")
    by_exit = defaultdict(lambda: defaultdict(lambda: {"down": 0, "up": 0, "rule": set()}))
    for fp in files:
        for line in open(fp):
            r = json.loads(line)
            chains = ",".join(r["chains"])
            if "住宅" in chains and "大流量" not in chains:
                exit_key = "住宅（贵，重点优化）"
            elif "大流量" in chains:
                exit_key = "大流量（便宜）"
            elif "DIRECT" in chains:
                exit_key = "直连"
            else:
                exit_key = "其他"
            s = by_exit[exit_key][r["host"]]
            s["down"] += r["down"]
            s["up"] += r["up"]
            s["rule"] |= set(r["rule"])
    print(f"数据文件: {len(files)} 天 ({files[0].split('/')[-1]} ~ {files[-1].split('/')[-1]})\n")
    for exit_key in ["住宅（贵，重点优化）", "大流量（便宜）", "直连", "其他"]:
        hosts = by_exit.get(exit_key)
        if not hosts:
            continue
        total = sum(s["down"] + s["up"] for s in hosts.values())
        print(f"== {exit_key}  合计 {total / 1e9:.2f} GB ==")
        rows = sorted(hosts.items(), key=lambda kv: -(kv[1]["down"] + kv[1]["up"]))
        for host, s in rows[:15]:
            rule = ",".join(sorted(s["rule"]))[:60]
            print(f"  {host:<46} {(s['down'] + s['up']) / 1e6:>9.1f} MB  {rule}")
        print()
    print("优化动作：「住宅」区里流量大且非 AI/风控敏感的域名 → 加进 rule-providers/heavy-rules.yaml")


if __name__ == "__main__":
    if not SECRET:
        sys.exit("请先 export CLASH_API_SECRET=<OpenClash 管理页面密码>")
    mode = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    if mode == "poll":
        poll(arg or 240)
    elif mode == "collect":
        collect(arg or 240)
    elif mode == "report":
        report(arg or 7)
    else:
        snapshot()

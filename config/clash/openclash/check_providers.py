#!/usr/bin/env python3
"""Check actual provider freshness. CLASH_API_SECRET uses the same env as clash_traffic.py.

python3 check_providers.py            # read-only
python3 check_providers.py --refresh  # ask mihomo to refresh both providers
"""
import argparse
from datetime import datetime, timezone
import json
import os
import urllib.error
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    base = os.environ.get("CLASH_API_BASE", "http://192.168.2.190:9090").rstrip("/")
    secret = os.environ.get("CLASH_API_SECRET")
    if not secret:
        parser.exit(1, "请设置 CLASH_API_SECRET（与 clash_traffic.py 相同）\n")

    def api(path, method="GET"):
        req = urllib.request.Request(base + path, method=method,
                                     headers={"Authorization": "Bearer " + secret})
        with urllib.request.urlopen(req, timeout=40) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}

    failed = False
    try:
        if args.refresh:
            for name in ["equalvpn", "huayun"]:
                try:
                    api("/providers/proxies/" + urllib.parse.quote(name), "PUT")
                    print(f"{name}: 已请求更新")
                except (OSError, ValueError) as exc:
                    print(f"{name}: 更新失败 ({type(exc).__name__})，请检查日志中的 403/订阅过期")
                    failed = True
        providers = api("/providers/proxies").get("providers", {})
        now = datetime.now(timezone.utc)
        for name in ["equalvpn", "huayun"]:
            p = providers.get(name)
            if not p or p.get("vehicleType") != "HTTP":
                print(f"{name}: 没有 HTTP provider，仍是旧配置或尚未迁移")
                failed = True
                continue
            updated = p.get("updatedAt", "")
            try:
                age = (now - datetime.fromisoformat(updated.replace("Z", "+00:00"))).total_seconds()
            except (ValueError, TypeError, OverflowError):
                age = float("inf")
            count = len(p.get("proxies", []))
            print(f"{name}: {count} 节点；最后更新 {updated}；距今 {age / 3600:.1f} 小时")
            if age > 3 * 3600 or count == 0:
                print(f"{name}: 超过 3 小时未更新成功或节点为空，需要排查")
                failed = True
        groups = api("/proxies").get("proxies", {})
        group = groups.get("大流量自动", {})
        choice = group.get("now", "未知")
        print(f"大流量自动当前选择: {choice}")
        manual = groups.get("大流量", {})
        print(f"大流量手动选择: {manual.get('now', '未知')}")
        if manual.get("now") == "AI 专线":
            print("用户已手动选择 AI 专线承载大流量")
        if group.get("type") != "URLTest":
            print("大流量自动尚未使用仅含便宜节点的测速结构")
            failed = True
        forbidden = {"AI 专线", "住宅节点"} | set(groups.get("住宅节点", {}).get("all", []))
        if forbidden.intersection(group.get("all", [])):
            print("大流量自动错误包含 AI/住宅入口")
            failed = True
        if "AI 专线" not in manual.get("all", []):
            print("大流量菜单缺少 AI 专线手动入口")
            failed = True
    except (OSError, ValueError) as exc:
        parser.exit(1, f"无法读取 Clash API ({type(exc).__name__})\n")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()

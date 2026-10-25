#!/usr/bin/env python3
"""用公开模板 stash.yaml 生成手机可直接导入的 Stash 配置。

真实订阅链接和自建节点只在本机 Git 忽略的 inno/ 目录里：
  inno/auto-update/sources.json               {"equalvpn": "订阅 URL", ...}（与 openclash/build_config.py 共用）
  inno/auto-update/stash-private-nodes.yaml   {"proxies": [自建住宅出口节点, ...]}，可选

  python3 config/clash/stash/build_stash.py            # 输出 inno/stash/peter-phone.yaml
  python3 config/clash/stash/build_stash.py --out PATH

输出含凭据，以 0600 写入；终端只打印节点名和数量。需要 PyYAML。
"""
import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PRIVATE = os.path.join(REPO, "inno", "auto-update")
BUILTIN = {"DIRECT", "REJECT"}


def check(cfg):
    """所有策略组 / 规则引用的名字都必须存在，否则 Stash 导入后会报错或静默失效。"""
    names = BUILTIN | {p["name"] for p in cfg.get("proxies", [])} | {g["name"] for g in cfg["proxy-groups"]}
    errors = []
    for g in cfg["proxy-groups"]:
        errors += [f"组「{g['name']}」引用了不存在的「{p}」" for p in g.get("proxies", []) if p not in names]
        errors += [f"组「{g['name']}」引用了不存在的 provider「{u}」" for u in g.get("use", [])
                   if u not in cfg.get("proxy-providers", {})]
    for r in cfg["rules"]:
        parts = r.split(",")
        target = parts[1] if parts[0] == "MATCH" else (parts[-2] if parts[-1] == "no-resolve" else parts[-1])
        if target not in names:
            errors.append(f"规则「{r}」的目标不存在")
        if parts[0] == "RULE-SET" and parts[1] not in cfg["rule-providers"]:
            errors.append(f"规则「{r}」引用的规则集不存在")
    for name, p in cfg.get("proxy-providers", {}).items():
        if "_SUB_URL" in str(p.get("url", "")):
            errors.append(f"provider「{name}」的订阅链接还是占位符")
    return errors


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(REPO, "inno", "stash", "peter-phone.yaml")
    cfg = yaml.safe_load(open(os.path.join(HERE, "stash.yaml")))
    sources = json.load(open(os.path.join(PRIVATE, "sources.json")))
    cfg["proxy-providers"]["equalvpn"]["url"] = sources["equalvpn"]

    nodes_path = os.path.join(PRIVATE, "stash-private-nodes.yaml")
    nodes = yaml.safe_load(open(nodes_path))["proxies"] if os.path.exists(nodes_path) else []
    if nodes:
        cfg["proxies"] = nodes
        group = next(g for g in cfg["proxy-groups"] if g["name"] == "住宅节点")
        group["proxies"] = [n["name"] for n in nodes] + group["proxies"]

    errors = check(cfg)
    if errors:
        sys.exit("生成失败，未写文件：\n  " + "\n  ".join(errors))

    os.makedirs(os.path.dirname(out), mode=0o700, exist_ok=True)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("# 由 config/clash/stash/build_stash.py 生成，含订阅链接与节点凭据，不要提交或分享\n")
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    print(f"已生成 {out}")
    print(f"  私有节点: {', '.join(n['name'] for n in nodes) or '无'}")
    print(f"  订阅: {', '.join(cfg['proxy-providers'])}；策略组 {len(cfg['proxy-groups'])} 个；规则 {len(cfg['rules'])} 条")


if __name__ == "__main__":
    main()

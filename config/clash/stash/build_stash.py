#!/usr/bin/env python3
"""用公开模板 stash.yaml 生成手机可直接导入的 Stash 配置。

真实订阅链接和自建节点只在本机 Git 忽略的 inno/ 目录里：
  inno/auto-update/sources.json               {"equalvpn": "订阅 URL", ...}（与 openclash/build_config.py 共用）
  inno/auto-update/stash-private-nodes.yaml   {"proxies": [...], "node-groups": {策略组: [节点名]}}，可选

  python3 config/clash/stash/build_stash.py            # 旧模板输出 inno/stash/peter-phone-legacy.yaml
  python3 config/clash/stash/build_stash.py --out PATH

输出含凭据，以 0600 写入；终端只打印节点名和数量。需要 PyYAML。
"""
import json
import ipaddress
import os
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PRIVATE = os.path.join(REPO, "inno", "auto-update")
BUILTIN = {"DIRECT", "REJECT"}


def inject_private_nodes(cfg, private):
    """Explicit groups prevent a data-center node becoming the residential default."""
    nodes = private.get("proxies", [])
    if not nodes:
        return []
    names = [n["name"] for n in nodes]
    if len(names) != len(set(names)):
        raise ValueError("私有节点名称重复")
    bindings = private.get("node-groups")
    if not isinstance(bindings, dict):
        raise ValueError("请在私有节点文件填写 node-groups，明确住宅与机房节点的分组")
    groups = {g["name"]: g for g in cfg["proxy-groups"]}
    assigned = set()
    for group_name, members in bindings.items():
        if group_name not in groups or not isinstance(members, list):
            raise ValueError("私有节点分组不存在或格式不正确")
        if any(name not in names for name in members):
            raise ValueError("私有分组引用了不存在的节点")
        group = groups[group_name]
        existing = group.get("proxies", [])
        # Preserve the established first choice outside the residential group.
        merged = members + existing if group_name == "住宅节点" else existing + members
        group["proxies"] = list(dict.fromkeys(merged))
        assigned.update(members)
    if assigned != set(names):
        raise ValueError("部分私有节点没有明确分组，停止生成")
    cfg["proxies"] = nodes
    endpoints = []
    for server in sorted({n["server"] for n in nodes}):
        try:
            address = ipaddress.ip_address(server)
            endpoints.append(f"IP-CIDR{'6' if address.version == 6 else ''},{address}/{address.max_prefixlen},DIRECT,no-resolve")
        except ValueError:
            endpoints.append(f"DOMAIN,{server},DIRECT")
    cfg["rules"] = endpoints + cfg["rules"]
    return nodes


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
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(REPO, "inno", "stash", "peter-phone-legacy.yaml")
    with open(os.path.join(HERE, "stash.yaml")) as stream:
        cfg = yaml.safe_load(stream)
    with open(os.path.join(PRIVATE, "sources.json")) as stream:
        sources = json.load(stream)
    cfg["proxy-providers"]["equalvpn"]["url"] = sources["equalvpn"]

    nodes_path = os.path.join(PRIVATE, "stash-private-nodes.yaml")
    try:
        private = {}
        if os.path.exists(nodes_path):
            with open(nodes_path) as stream:
                private = yaml.safe_load(stream)
        nodes = inject_private_nodes(cfg, private or {})
    except yaml.YAMLError:
        sys.exit("生成失败：私有节点YAML格式错误，未打印内容")
    except (ValueError, KeyError, TypeError):
        sys.exit("生成失败：私有节点及 node-groups 分组不完整，未打印凭据")

    errors = check(cfg)
    if errors:
        sys.exit("生成失败，未写文件：\n  " + "\n  ".join(errors))

    os.makedirs(os.path.dirname(out), mode=0o700, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".stash-private-", dir=os.path.dirname(out))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write("# 由 config/clash/stash/build_stash.py 生成；含凭据，仅在自己的设备间私密传输，禁止公开或上传\n")
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        os.replace(temporary, out)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"已生成 {out}")
    print(f"  私有节点: {', '.join(n['name'] for n in nodes) or '无'}")
    print(f"  订阅: {', '.join(cfg['proxy-providers'])}；策略组 {len(cfg['proxy-groups'])} 个；规则 {len(cfg['rules'])} 条")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build a private OpenClash bundle; browser permission must precede gated downloads.

python3 build_config.py --sources ../../../inno/auto-update/sources.json
Requires PyYAML. URLs and node credentials are never printed.
"""
import argparse
import base64
import concurrent.futures
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
META = re.compile(r"Traffic:|Expire:|剩余流量|到期时间|套餐到期", re.I)


def flower_origin(url):
    """Unwrap only the provider's known converter, never arbitrary URLs."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.hostname in {"api-huacloud.com", "api-huacloud.net"}:
        nested = urllib.parse.parse_qs(parsed.query).get("url", [])
        if len(nested) != 1:
            raise ValueError("花云转换 URL 必须包含一个原始订阅地址")
        origin = urllib.parse.urlsplit(nested[0])
        if origin.scheme != "https" or origin.hostname != "api.xmancdn.net":
            raise ValueError("未知花云原始订阅域名，请直接填写官方原始订阅 URL")
        return nested[0]
    return url


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mihomo/1.19"})
    # Avoid inheriting workstation HTTP_PROXY; the router also downloads via DIRECT.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=30) as response:
        body = response.read(4 * 1024 * 1024 + 1)
    if len(body) > 4 * 1024 * 1024:
        raise ValueError("订阅超过 4 MiB")
    return body


def decode64(text):
    text = "".join(text.split())
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4)).decode("utf-8")


def parse_subscription(body):
    """Normalize current providers (YAML or SIP002 SS) to a validated cache."""
    text = body.decode("utf-8-sig").strip()
    if re.search(r"<(?:!doctype|html)", text[:500], re.I):
        raise ValueError("订阅返回 HTML 验证/登录页")
    data = yaml.safe_load(text)
    if isinstance(data, dict):
        nodes = data.get("proxies")
    else:
        if "://" not in text:
            text = decode64(text)
        nodes = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = urllib.parse.urlsplit(line)
            if parts.scheme != "ss":
                raise ValueError("构建器仅规范化 YAML/SS；其他 URI 请使用原生 provider")
            name = urllib.parse.unquote(parts.fragment)
            if META.search(name):
                continue
            query = urllib.parse.parse_qs(parts.query)
            plugin_options = None
            if query:
                if set(query) != {"plugin"} or len(query["plugin"]) != 1:
                    raise ValueError("未知 SS 参数，不能静默丢弃")
                plugin, *options = query["plugin"][0].split(";")
                options = dict(option.split("=", 1) for option in options)
                if plugin not in {"simple-obfs", "obfs-local"} or set(options) - {"obfs", "obfs-host"}:
                    raise ValueError("未知 SS plugin，不能静默丢弃")
                if options.get("obfs") not in {"http", "tls"}:
                    raise ValueError("未知 obfs 模式")
                plugin_options = {"mode": options["obfs"], "host": options.get("obfs-host", "")}
            # SIP002 credentials may be base64 or cleartext user:password.
            userinfo = parts.netloc.rsplit("@", 1)[0]
            credential = urllib.parse.unquote(userinfo)
            if ":" not in credential:
                credential = decode64(credential)
            cipher, password = credential.split(":", 1)
            nodes.append({"name": name, "type": "ss", "server": parts.hostname,
                          "port": parts.port, "cipher": cipher, "password": password,
                          "udp": True})
            if plugin_options:
                nodes[-1].update({"plugin": "obfs", "plugin-opts": plugin_options})
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("订阅没有节点")
    nodes = [n for n in nodes if isinstance(n, dict) and not META.search(str(n.get("name", "")))]
    names = set()
    for node in nodes:
        if not all(node.get(k) for k in ("name", "type", "server", "port")):
            raise ValueError("节点缺少必要字段")
        if node["name"] in names:
            raise ValueError("同一订阅内节点重名")
        names.add(node["name"])
    if not nodes:
        raise ValueError("订阅只有套餐提示，没有可用节点")
    return nodes


def endpoint_rules(nodes):
    result = []
    for server in sorted({n["server"] for n in nodes}):
        try:
            addr = ipaddress.ip_address(server)
            result.append(f"IP-CIDR{'6' if addr.version == 6 else ''},{addr}/{addr.max_prefixlen},DIRECT,no-resolve")
        except ValueError:
            result.append(f"DOMAIN,{server},DIRECT")
    return result


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".peter-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def build(sources, output):
    cfg = yaml.safe_load((HERE / "home-template.yaml").read_text())
    urls = {"equalvpn": sources["equalvpn"], "huayun": flower_origin(sources["huayun"])}
    nodes = {}
    for name, url in urls.items():
        if urllib.parse.urlsplit(url).scheme != "https":
            raise ValueError(f"{name}: 订阅必须使用 HTTPS")
        try:
            nodes[name] = parse_subscription(fetch(url))
        except Exception as exc:
            # Error bodies / exception messages may include tokens; suppress them.
            code = getattr(exc, "code", None)
            raise ValueError(f"{name}: 拉取/解析失败 ({type(exc).__name__}, HTTP={code})；已有配置保留") from None
        cfg["proxy-providers"][name]["url"] = url
    residential = [n for n in nodes["equalvpn"] if re.search("住宅|静态", n["name"])]
    if not residential:
        raise ValueError("EqualVPN 未匹配住宅节点，停止构建，保留现有配置")
    # This bootstrap snapshot prevents Stash-in-home tunnels from double proxying.
    # Refreshing node credentials inside mihomo does not update these endpoint rules.
    endpoints = endpoint_rules(nodes["equalvpn"] + nodes["huayun"])
    cfg["rules"] = endpoints + cfg["rules"]
    # Fetch all rule seeds before replacing anything. Future refreshes remain native.
    seeds = {}
    def rule_seed(item):
        name, provider = item
        try:
            raw = fetch(provider["url"])
            parsed = yaml.safe_load(raw)
            if not isinstance(parsed, dict) or not isinstance(parsed.get("payload"), list):
                raise ValueError("rule payload")
            return name, raw.decode("utf-8")
        except Exception as exc:
            raise ValueError(f"规则 {name}: 拉取/解析失败 ({type(exc).__name__})；已有配置保留") from None
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for name, content in executor.map(rule_seed, cfg["rule-providers"].items()):
            seeds[name] = content
    for name, group in ((g["name"], g) for g in cfg["proxy-groups"]):
        for provider in group.get("use", []):
            if provider not in nodes:
                raise ValueError(f"{name}: 引用了不存在的 provider")
    output = Path(output)
    bundle = output.parent
    for name, values in nodes.items():
        atomic_write(bundle / "proxy_provider" / f"peter-{name}.yaml",
                     yaml.safe_dump({"proxies": values}, allow_unicode=True, sort_keys=False))
    for name, content in seeds.items():
        atomic_write(bundle / "rule_provider" / f"{name}.yaml", content)
    # Write the main config last, only after both providers and all rules validated.
    atomic_write(output, "# 私有配置：包含订阅凭据，禁止公开。由 build_config.py 生成。\n" +
                 yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))
    print(f"配置已生成: {output}")
    print(f"EqualVPN: {len(nodes['equalvpn'])} 节点（住宅 {len(residential)}）；花云: {len(nodes['huayun'])} 节点")
    print("订阅更新 1 小时；健康检查 5 分钟；规则更新 24 小时；原始 URL 不输出")
    return cfg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=REPO / "inno/auto-update/bundle/peter-home.yaml")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        build(json.loads(args.sources.read_text()), args.output)
    except (ValueError, KeyError, OSError, yaml.YAMLError) as exc:
        # File and YAML errors may contain credentials, too.
        message = str(exc) if type(exc) is ValueError else type(exc).__name__
        parser.exit(1, message + "\n")


if __name__ == "__main__":
    main()

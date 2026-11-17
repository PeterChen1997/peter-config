#!/usr/bin/env python3
"""Export the live home routing policy to a private, standalone Stash file.

Only --sync writes to the owner's configured iCloud folder. SSH, policy settings,
receipts and rollback copies remain local. Requires PyYAML; never logs YAML/errors
that could include credentials. See README.md for the separate legacy builder.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
from urllib.parse import urlsplit

import yaml

REPO = Path(__file__).resolve().parents[3]
LOCAL = REPO / "inno/stash"
SETTINGS = LOCAL / "export-settings.PRIVATE.json"
SOURCE_MEMBERS = ["Home-Auto.yaml", "config/Home-Auto.yaml"] + [
    f"rule_provider/simple-{n}.yaml"
    for n in ("ai", "domestic", "general", "gemini", "priority")
]
GROUPS = {"普通出网", "AI出网", "Gemini-US"}
PHONE_WEBSHARE_BWH = "AI-Webshare-BWH"
PHONE_WEBSHARE_RACKNERD = "AI-Webshare-RackNerd"
PHONE_WEBSHARE_SOCKS_SUFFIX = "-SOCKS5"
PHONE_WEBSHARE_SOCKS = tuple(name + PHONE_WEBSHARE_SOCKS_SUFFIX
                             for name in (PHONE_WEBSHARE_BWH, PHONE_WEBSHARE_RACKNERD))
PHONE_ORDINARY_AUTO = "普通自动"
NODE_FIELDS = {
    "name", "type", "server", "port", "uuid", "network", "tls", "udp",
    "flow", "servername", "sni", "client-fingerprint", "reality-opts",
    "dialer-proxy", "fingerprint", "skip-cert-verify", "cipher", "password",
    "plugin", "plugin-opts",
}
RULE_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6", "GEOIP", "GEOSITE"}


class ExportError(Exception):
    """Safe, fixed diagnostic messages only; do not include source values."""


def require(condition, reason):
    if not condition:
        raise ExportError(reason)


def digest_node(node):
    return hashlib.sha256(json.dumps(node, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def gaming_source_rule(policy):
    network = ipaddress.ip_network(policy["source_cidr"])
    require(network.version == 4 and network.prefixlen == 32 and network.is_private
            and policy.get("group") == "PS5出网", "Invalid reviewed console source policy")
    return f"AND,((SRC-IP-CIDR,{network}),(NOT,((GEOIP,CN)))),PS5出网"


def fixed_home_ai_policy(settings, nodes, groups, metered_model):
    """Recognize the switchable BWH/RackNerd topology around one Webshare endpoint."""
    policy = settings.get("ai_path_policy", {})
    trusted = settings.get("dynamic_egress_policy", {}).get("nodes", {})
    original = policy.get("preferred")
    ordinary, ai = groups["普通出网"], groups["AI出网"]
    auto = groups.get("普通自动")
    variants = [(PHONE_WEBSHARE_BWH, "BWH-Direct"), (PHONE_WEBSHARE_RACKNERD, "RackNerd-Direct")]
    require(ordinary.get("proxies") == ["BWH-Direct", "RackNerd-Direct", PHONE_ORDINARY_AUTO]
            and ordinary.get("default-selected") == "BWH-Direct"
            and ai.get("proxies") == [name for name, _ in variants]
            and ai.get("default-selected") == PHONE_WEBSHARE_BWH
            and all(group.get("type") == "select" and group.get("disable-udp") is True
                    and not any(group.get(key) for key in
                                ("use", "include-all", "include-all-proxies", "include-all-providers"))
                    for group in (ordinary, ai)), "Fixed home egress groups changed; review required")
    require(auto is not None and auto.get("type") == "url-test"
            and auto.get("proxies") == ["BWH-Direct", "RackNerd-Direct"]
            and auto.get("interval") == 180 and auto.get("tolerance") == 100
            and auto.get("hidden") is True
            and not any(auto.get(key) for key in
                        ("use", "include-all", "include-all-proxies", "include-all-providers")),
            "Fixed ordinary automatic group changed; review required")
    metered_nodes = {metered_model["node"]} if metered_model else set()
    require(set(nodes) == set(trusted) | {name for name, _ in variants} | metered_nodes
            and all(digest_node(nodes[node]) == pin for node, pin in trusted.items()),
            "Fixed home proxy identities changed; review required")
    approved = policy.get("upstreams", {}).get("BWH-Direct")
    require(original == "Webshare-via-BWH" and approved and approved == trusted.get("BWH-Direct"),
            "Fixed Webshare transit changed; review required")
    for name, upstream in variants:
        require(upstream in trusted and nodes[name].get("dialer-proxy") == upstream,
                "Fixed Webshare transit changed; review required")
        canonical = dict(nodes[name], name=original, **{"dialer-proxy": "BWH-Direct"})
        require(digest_node(canonical) == policy.get("nodes", {}).get(original),
                "Fixed Webshare endpoint changed; review required")
    return dict(policy, preferred=PHONE_WEBSHARE_BWH,
                nodes={name: digest_node(nodes[name]) for name, _ in variants},
                upstreams={upstream: trusted[upstream] for _, upstream in variants})


def atomic_write(path, data):
    path = Path(path)
    require(not path.is_symlink(), "Destination symlink rejected")
    fd, temporary = tempfile.mkstemp(prefix=".stash-export-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_router(settings):
    # Fixed command: no secrets, untrusted source paths or shell interpolation.
    command = (
        'test "$(uci -q get openclash.config.config_path)" = '
        '/etc/openclash/config/Home-Auto.yaml && '
        'tar -cf - -C /etc/openclash ' + " ".join(SOURCE_MEMBERS)
    )
    result = subprocess.run(
        ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
         "-o", "ConnectTimeout=8", settings["router_alias"], command],
        capture_output=True, timeout=40,
    )
    require(result.returncode == 0, "Router unavailable or active configuration changed; previous export retained")
    return result.stdout


def unpack_source(data):
    require(len(data) < 8_000_000, "Source archive too large")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        members = archive.getmembers()
        require(len(members) == len(SOURCE_MEMBERS), "Unexpected source archive members")
        for member in members:
            require(member.name in SOURCE_MEMBERS and member.isfile() and member.size < 2_000_000,
                    "Unsafe source archive member")
            require(member.name not in files, "Duplicate source archive member")
            files[member.name] = yaml.safe_load(archive.extractfile(member))
    require(set(files) == set(SOURCE_MEMBERS), "Incomplete source archive")
    live, saved = files["Home-Auto.yaml"], files["config/Home-Auto.yaml"]
    for section in ("proxies", "proxy-groups", "rules", "rule-providers"):
        require(live.get(section) == saved.get(section), "Live and persistent routing differ; previous export retained")
    return live, files


def convert(source, files, settings):
    """Whitelist phone fields, preserve route order, and enforce the reviewed egress policy."""
    nodes = {n["name"]: n for n in source["proxies"]}
    groups = {g["name"]: g for g in source["proxy-groups"]}
    policy = settings.get("ai_path_policy")
    fixed = settings.get("fixed_home_egress") is True
    dynamic = None if fixed else settings.get("dynamic_egress_policy")
    require(not dynamic or policy, "Dynamic egress requires a reviewed routing baseline")
    allowed_groups = {"普通出网", "AI出网"} if policy else GROUPS
    gaming = settings.get("gaming_path_policy")
    if gaming:
        allowed_groups = allowed_groups | {"PS5出网"}
    model_download = settings.get("model_download_policy")
    metered_model = model_download.get("metered") if model_download else None
    if model_download:
        allowed_groups = allowed_groups | {"模型下载"}
    if metered_model:
        allowed_groups = allowed_groups | {"模型华云"}
    if fixed:
        allowed_groups = allowed_groups | {PHONE_ORDINARY_AUTO}
    require(set(groups) == allowed_groups and len(groups) == len(source["proxy-groups"]), "Unexpected routing groups")
    reserved = GROUPS | allowed_groups | {"DIRECT", "REJECT", *PHONE_WEBSHARE_SOCKS}
    require(not set(nodes).intersection(reserved), "Reserved proxy name")
    require(not source.get("proxy-providers"), "External proxy providers need explicit export review")
    if fixed:
        policy = fixed_home_ai_policy(settings, nodes, groups, metered_model)
    for group in groups.values():
        ordinary_policy = settings.get("ordinary_path_policy") if group["name"] == "普通出网" else None
        model_selector = bool(metered_model and group["name"] == "模型下载")
        model_carriers = bool(metered_model and group["name"] == "模型华云")
        shared_ai = bool(dynamic and group["name"] == "AI出网")
        allowed_types = {"url-test", "fallback"} if group["name"] == "AI出网" or ordinary_policy else {"url-test"}
        if model_selector:
            allowed_types = {"select"}
        if model_carriers:
            allowed_types = {"fallback"}
        if shared_ai:
            allowed_types = {"select"}
        if fixed and group["name"] in {"普通出网", "AI出网"}:
            allowed_types = {"select"}
        require(group["type"] in allowed_types and group.get("proxies"), "Empty or changed automatic group rejected")
        members = set(nodes) | ({"模型华云"} if model_selector else set())
        if fixed and group["name"] == "普通出网":
            members.add(PHONE_ORDINARY_AUTO)
        if shared_ai:
            members.add("普通出网")
        require(not group.get("use") and all(n in members for n in group["proxies"]), "Unresolved group member")
        if ordinary_policy:
            preferred = ordinary_policy.get("preferred")
            require(group["type"] == ("select" if fixed else "fallback") and group["proxies"][0] == preferred
                    and preferred in nodes, "Ordinary priority changed; review required")
            transport = nodes[preferred]
            require(digest_node(transport) == ordinary_policy.get("node_sha256")
                    and transport.get("type") == "vless" and transport.get("tls") is True
                    and not transport.get("dialer-proxy"), "Ordinary preferred transport identity changed")
        elif group["type"] == "fallback" and not model_carriers:
            preferred = policy.get("preferred") if policy else "Lisa-via-BWH"
            trusted = policy.get("nodes", {}) if policy else settings["verified_server_side_ai_nodes"]
            require(group["proxies"][0] == preferred and preferred in trusted,
                    "AI priority must start with the verified residential path")
    default_target = "普通出网" if policy else "AI出网"
    require(source["rules"][-1] == "MATCH," + default_target, "Default route changed")
    require(sum(r.startswith("MATCH,") for r in source["rules"]) == 1, "Unexpected default routes")
    gemini_target = "AI出网" if policy else "Gemini-US"
    required = ["RULE-SET,simple-gemini," + gemini_target, "RULE-SET,simple-ai,AI出网", "RULE-SET,peter-ai,AI出网"]
    require(all(r in source["rules"] for r in required)
            and source["rules"].index(required[0]) < source["rules"].index(required[1])
            and source["rules"].index(required[0]) < source["rules"].index(required[2]),
            "AI or Gemini routing changed; review required")
    home_only_rules = set()
    if gaming:
        group = groups["PS5出网"]
        require(group["type"] == "url-test" and group.get("hidden") is True
                and group.get("disable-udp") is (not bool(gaming.get("udp_verified")))
                and group["proxies"] == list(gaming.get("nodes", {})), "Gaming candidates changed; review required")
        for name in group["proxies"]:
            node = nodes[name]
            require(node.get("type") == "ss" and not node.get("dialer-proxy")
                    and node.get("udp") is bool(gaming.get("udp_verified"))
                    and digest_node(node) == gaming["nodes"][name], "Gaming node identity changed")
        console_rule = gaming_source_rule(gaming)
        domain_rules = ["DOMAIN-SUFFIX," + domain + ",PS5出网" for domain in gaming.get("domains", [])]
        require(all(re.fullmatch(r"[a-z0-9.-]+", d) for d in gaming.get("domains", [])),
                "Invalid reviewed gaming domains")
        require(source["rules"].count(console_rule) == 1
                and all(r in source["rules"] for r in domain_rules)
                and all(source["rules"].index(console_rule) > source["rules"].index(r) for r in required)
                and all(source["rules"].index(r) < source["rules"].index(console_rule) for r in domain_rules),
                "Reviewed console routing changed")
        home_only_rules.add(console_rule)
        if fixed:
            console_tcp = f'AND,((SRC-IP-CIDR,{gaming["source_cidr"]}),(NETWORK,tcp)),DIRECT'
            if console_tcp in source["rules"]:
                position = source["rules"].index(console_rule)
                require(position > 0 and source["rules"][position - 1] == console_tcp
                        and source["rules"].count(console_tcp) == 1, "Reviewed console TCP rule changed")
                home_only_rules.add(console_tcp)
    if model_download:
        model_group = groups["模型下载"]
        require(gaming and model_group.get("disable-udp") is True
                and not any(model_group.get(key) for key in
                            ("include-all", "include-all-proxies", "include-all-providers")),
                "Model downloads require only the reviewed carrier pool")
        if metered_model:
            name = metered_model.get("node")
            mark = metered_model.get("routing_mark")
            require(name == "BWH-Model-Metered" and type(mark) is int and mark > 0
                    and settings.get("ordinary_path_policy", {}).get("preferred") == "BWH-Direct"
                    and model_group["type"] == "select" and model_group.get("default-selected") == "模型华云"
                    and model_group["proxies"] == [name, "模型华云"], "Unexpected metered model routing")
            carrier_group = groups["模型华云"]
            carrier_order = carrier_group["proxies"]
            require(carrier_order == metered_model.get("carrier_order")
                    and len(carrier_order) == len(groups["PS5出网"]["proxies"])
                    and set(carrier_order) == set(groups["PS5出网"]["proxies"])
                    and carrier_group.get("disable-udp") is True and carrier_group.get("hidden") is True
                    and not any(carrier_group.get(key) for key in
                                ("include-all", "include-all-proxies", "include-all-providers")),
                    "Metered fallback must use only the reviewed carrier nodes")
            expected = dict(nodes["BWH-Direct"], name=name, **{"routing-mark": mark})
            require(nodes.get(name) == expected
                    and all(name not in group["proxies"] for group in groups.values() if group is not model_group)
                    and all(node.get("dialer-proxy") != name for node in nodes.values()),
                    "Metered model transport differs from the reviewed home-only node")
        else:
            require(model_group["type"] == "url-test" and model_group["proxies"] == groups["PS5出网"]["proxies"],
                    "Unreviewed model download members")
        matches = model_download.get("matches", [])
        require(matches and len(matches) == len(set(matches))
                and all(re.fullmatch(r"DOMAIN-(?:SUFFIX|KEYWORD),[a-z0-9.-]+", match)
                        for match in matches), "Invalid reviewed model download matches")
        model_rules = [match + ",模型下载" for match in matches]
        start = max(source["rules"].index(rule) for rule in required) + 1
        require(source["rules"][start:start + len(model_rules)] == model_rules
                and [rule for rule in source["rules"] if rule.endswith(",模型下载")] == model_rules,
                "Reviewed model download routes changed")
    if dynamic:
        ordinary, ai = groups["普通出网"], groups["AI出网"]
        trusted = dynamic.get("nodes", {})
        require(ordinary["type"] == "fallback" and ordinary["proxies"] == list(trusted)
                and ai["proxies"] == ["普通出网"]
                and all(group.get("disable-udp") is True and not any(group.get(key) for key in
                        ("include-all", "include-all-proxies", "include-all-providers")) for group in (ordinary, ai))
                and not set(nodes).intersection(policy.get("nodes", {})),
                "Shared egress or candidate order changed; review required")
        for name, identity in trusted.items():
            node = nodes[name]
            require(node["type"] in {"ss", "vless"} and (node["type"] != "vless" or node.get("tls") is True)
                    and not node.get("dialer-proxy") and not node.get("routing-mark")
                    and digest_node(node) == identity, "Shared egress candidate identity changed")
    for name in (() if dynamic else groups["AI出网"]["proxies"]):
        node = nodes[name]
        if policy:
            require(policy.get("authentication") == "source-ip"
                    and policy.get("default_target") == default_target
                    and policy.get("gemini_target") == gemini_target,
                    "Reviewed AI policy required")
            require(groups["AI出网"]["type"] == ("select" if fixed else "fallback")
                    and groups["AI出网"]["proxies"] == list(policy.get("nodes", {})),
                    "AI paths or priority changed; review required")
            require(digest_node(node) == policy["nodes"].get(name),
                    "Approved fixed proxy identity changed; review required")
            require(node.get("type") == "http" and node.get("tls") is False
                    and "username" not in node and "password" not in node
                    and node.get("udp") is False and node.get("skip-cert-verify") is False,
                    "AI proxy must use reviewed passwordless TCP access")
            upstream = node.get("dialer-proxy")
            require(upstream in nodes and upstream in policy.get("upstreams", {}),
                    "Unapproved AI transport")
            transport = nodes[upstream]
            require(digest_node(transport) == policy["upstreams"][upstream]
                    and transport.get("type") == "vless" and transport.get("tls") is True
                    and not transport.get("dialer-proxy"),
                    "AI transport identity or encryption changed; review required")
            require(not set(groups["AI出网"]["proxies"]).intersection(groups["普通出网"]["proxies"]),
                    "Paid AI proxy cannot be in ordinary routing")
            continue
        trusted = settings["verified_server_side_ai_nodes"].get(name)
        if trusted:
            require(digest_node(node) == trusted, "Server-side residential path identity changed; review required")
        else:
            require(node.get("server") == settings["residential_server"], "Non-residential AI destination rejected")
            require(node.get("type") == "vless" and node.get("tls") is True,
                    "AI path must use authenticated TLS")
            require(node.get("fingerprint") == settings["residential_certificate_sha256"]
                    and node.get("skip-cert-verify") is False, "AI certificate verification changed")
            require(node.get("dialer-proxy") in nodes, "AI path needs a concrete upstream")
    # An unresolved or cyclic dialer must never fall through to a direct route.
    def visit(name, seen):
        require(name not in seen, "Proxy chain cycle rejected")
        upstream = nodes[name].get("dialer-proxy")
        if upstream:
            require(upstream in nodes, "Unresolved dialer proxy")
            visit(upstream, seen | {name})
    for name in nodes:
        visit(name, set())

    phone_nodes = []
    for node in source["proxies"]:
        if metered_model and node["name"] == metered_model["node"]:
            # Linux packet metering applies at home. Stash keeps the carrier-only pool.
            continue
        allowed_type = node["type"] in {"vless", "ss"} or (
            policy and node["type"] == "http" and node["name"] in policy.get("nodes", {})
            and node["name"] in groups["AI出网"]["proxies"])
        require(set(node) <= NODE_FIELDS and allowed_type, "Unsupported node fields require review")
        require(node.get("skip-cert-verify") is not True, "Disabled certificate verification rejected")
        require(set(node.get("reality-opts", {})) <= {"public-key", "short-id", "support-x25519mlkem768"}, "Unexpected Reality options")
        require(set(node.get("plugin-opts", {})) <= {"mode", "host"}, "Unexpected plugin options")
        phone = copy.deepcopy(node)
        if "servername" in phone:
            require("sni" not in phone or phone["sni"] == phone["servername"], "Conflicting TLS server names")
            phone["sni"] = phone.pop("servername")
        if "fingerprint" in phone:
            pin = phone.pop("fingerprint").replace(":", "")
            require(re.fullmatch(r"[0-9a-fA-F]{64}", pin), "Invalid certificate fingerprint")
            phone["server-cert-fingerprint"] = pin
        phone["benchmark-url"] = "https://cp.cloudflare.com/generate_204"
        phone["benchmark-timeout"] = 4
        if gaming and not gaming.get("domains") and node["name"] in gaming["nodes"]:
            # The console-only group is absent on the phone. Preserve the
            # ordinary group's TCP-only policy when sharing its SS nodes.
            if groups["普通出网"].get("disable-udp") is True:
                phone["udp"] = False
        if fixed and node["name"] == "RackNerd-Direct":
            # The now-selectable ordinary route follows the home's TCP-only policy.
            phone["udp"] = False
        phone_nodes.append(phone)

    providers = {}
    expanded = []
    for rule in source["rules"]:
        if rule in home_only_rules:
            # A phone does not forward the home console's packets. Keep the PSN
            # domain policy, while omitting this one reviewed router source rule.
            continue
        parts = rule.split(",")
        target = parts[-2] if parts[-1] == "no-resolve" else parts[-1]
        require(target in allowed_groups | {"DIRECT", "REJECT", "BWH-Direct"}, "Unknown rule target")
        if target == "BWH-Direct":
            require(target in nodes and target in groups["普通出网"]["proxies"],
                    "Fixed service node missing from ordinary routing")
            require(nodes[target]["type"] == "vless" and not nodes[target].get("dialer-proxy"),
                    "Fixed service route must use the direct VPS node")
            require(parts[0] in {"DOMAIN", "DOMAIN-SUFFIX"}
                    and all(source["rules"].index(rule) > source["rules"].index(r) for r in required),
                    "Fixed service rules must follow AI exceptions")
        if parts[0] == "RULE-SET":
            require(len(parts) in {3, 4}, "Unsupported rule-set reference")
            provider = source["rule-providers"][parts[1]]
            if provider["type"] == "file":
                require(provider["behavior"] == "classical", "Unsupported local rule behavior")
                path = provider["path"].removeprefix("./")
                require(path in files, "Missing portable rule payload")
                for entry in files[path]["payload"]:
                    bits = entry.split(",")
                    # iOS Network Extension cannot inspect processes. The router's
                    # own-process exceptions do not describe forwarded phone apps.
                    if bits[0] == "PROCESS-NAME":
                        continue
                    require(bits[0] in RULE_TYPES and len(bits) in {2, 3}, "Unsupported nested rule")
                    require(len(bits) == 2 or bits[-1] == "no-resolve", "Unexpected local rule target")
                    expanded.append(",".join(bits[:2] + [parts[2]] + bits[2:]))
                continue
            require(provider["type"] == "http", "Unsupported remote rule provider")
            url = provider["url"]
            parsed = urlsplit(url)
            require(url in settings["public_rule_urls"] and parsed.scheme == "https"
                    and not parsed.username and not parsed.query and not parsed.fragment,
                    "Unapproved or authenticated remote rule URL rejected")
            providers[parts[1]] = {k: provider[k] for k in ("behavior", "format", "url", "interval")}
        elif parts[0] != "MATCH":
            require(parts[0] in RULE_TYPES and len(parts) in {3, 4}, "Unsupported main rule")
        expanded.append(rule)

    phone_groups = []
    for group in source["proxy-groups"]:
        if gaming and not gaming.get("domains") and group["name"] == "PS5出网":
            continue
        if metered_model and group["name"] == "模型华云":
            continue
        if metered_model and group["name"] == "模型下载":
            group = dict(groups["PS5出网"], name=group["name"], hidden=group.get("hidden", False))
        if dynamic and group["name"] == "普通出网":
            group = dict(group, type="url-test", interval=180, tolerance=100, lazy=False)
        phone_groups.append({k: group[k] for k in ("name", "type", "proxies", "interval", "tolerance", "lazy", "hidden")
                             if k in group})
    if fixed:
        # Build phone-only choices after validating the entire home policy. Each
        # SOCKS5 alternative inherits its own reviewed, source-IP transit.
        webshare = {node["name"]: node for node in phone_nodes
                    if node["name"] in (PHONE_WEBSHARE_BWH, PHONE_WEBSHARE_RACKNERD)}
        members = []
        for name in (PHONE_WEBSHARE_BWH, PHONE_WEBSHARE_RACKNERD):
            node = webshare[name]
            phone_nodes.append(dict(node, name=name + PHONE_WEBSHARE_SOCKS_SUFFIX, type="socks5"))
            members += [name, name + PHONE_WEBSHARE_SOCKS_SUFFIX]
        selectors = {group["name"]: group for group in phone_groups}
        selectors["AI出网"]["proxies"] = members
    return {
        "mode": "rule", "log-level": "warning", "ipv6": False, "allow-lan": False,
        "dns": {
            "ipv6": False, "default-nameserver": ["223.5.5.5", "119.29.29.29"],
            "proxy-server-nameserver": ["https://dns.alidns.com/dns-query", "https://doh.pub/dns-query"],
            "nameserver": ["https://dns.alidns.com/dns-query", "https://doh.pub/dns-query"],
            "fallback": ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query"],
            "fallback-filter": {"geoip": True, "geoip-code": "CN"},
            "fake-ip-filter": ["*.lan", "*.local", "+.stun.*.*", "*.msftconnecttest.com", "*.msftncsi.com"],
        },
        "proxies": phone_nodes, "proxy-groups": phone_groups,
        "rule-providers": providers, "rules": expanded,
    }


def export(settings, archive, sync=False):
    source, files = unpack_source(archive)
    phone = convert(source, files, settings)
    data = ("# Private device configuration. Contains proxy credentials.\n"
            "# Only for the owner's devices/iCloud; never publish or create a public share link.\n"
            "# Stash 3.6+ recommended. Re-import/reload after file updates.\n"
            + yaml.safe_dump(phone, allow_unicode=True, sort_keys=False)).encode()
    output = Path(settings["local_output"]).expanduser()
    cloud = Path(settings["icloud_output"]).expanduser()
    require(output.parent.is_dir(), "Local output directory missing")
    if sync:
        require(cloud.parent.is_dir() and not cloud.parent.is_symlink(), "iCloud folder unavailable; previous export retained")
    # All conversion/validation happens before either previous file is touched.
    changed = not output.exists() or output.read_bytes() != data
    if changed:
        if output.exists():
            atomic_write(output.parent / "previous-phone.PRIVATE.yaml", output.read_bytes())
        atomic_write(output, data)
    else:
        output.chmod(0o600)
    cloud_changed = False
    if sync:
        cloud_changed = not cloud.exists() or cloud.read_bytes() != data
        if cloud_changed:
            if cloud.exists():
                atomic_write(output.parent / "previous-icloud-phone.PRIVATE.yaml", cloud.read_bytes())
            atomic_write(cloud, data)
        else:
            cloud.chmod(0o600)
        require(cloud.read_bytes() == data, "iCloud local-file readback failed")
    receipt = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "local_changed": changed,
        "icloud_file_written_or_verified": sync, "icloud_changed": cloud_changed,
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
        "proxies": len(phone["proxies"]), "rules": len(phone["rules"]),
        "group_members": {g["name"]: len(g["proxies"]) for g in phone["proxy-groups"]},
        "ios_unsupported_process_rules_omitted": sum(
            rule.startswith("PROCESS-NAME,") for path, content in files.items()
            if path.startswith("rule_provider/") for rule in content["payload"]),
        "apple_remote_delivery_verified": False, "iphone_activation_verified": False,
    }
    atomic_write(output.parent / "export-receipt.json", json.dumps(receipt, ensure_ascii=False, indent=2).encode())
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="Sync this one phone file to the owner's configured iCloud")
    args = parser.parse_args()
    try:
        settings = json.loads(SETTINGS.read_text())
        print(json.dumps(export(settings, read_router(settings), args.sync), ensure_ascii=False))
    except ExportError as e:
        print(f"Export stopped: {e}")
        return 1
    except Exception as e:
        # YAML parser and network exception text may contain secret input.
        print(f"Export stopped ({type(e).__name__}); inspect locally, do not print private inputs")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

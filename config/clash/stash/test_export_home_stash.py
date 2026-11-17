"""Synthetic fixtures only: no local network, credentials or iCloud writes."""
import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

import yaml

import export_home_stash as export


def fixture():
    pin = "ab" * 32
    carrier = {"name": "carrier", "type": "ss", "server": "192.0.2.1", "port": 443,
               "cipher": "aes-128-gcm", "password": "TEST-ONLY"}
    residential = {"name": "residential", "type": "vless", "server": "192.0.2.2",
                   "port": 443, "uuid": "TEST-ONLY", "tls": True, "servername": "test.invalid",
                   "skip-cert-verify": False, "fingerprint": pin, "dialer-proxy": "carrier"}
    providers = {"simple-" + n: {"type": "file", "behavior": "classical", "path": f"./rule_provider/simple-{n}.yaml"}
                 for n in ("ai", "domestic", "general", "gemini", "priority")}
    url = "https://example.com/public-rules.yaml"
    providers["peter-ai"] = {"type": "http", "behavior": "classical", "format": "yaml", "url": url, "interval": 86400}
    source = {
        "secret": "DO-NOT-EXPORT", "external-controller": "0.0.0.0:9090",
        "dns": {"nameserver": ["127.0.0.1:5335"]},
        "proxies": [carrier, residential],
        "proxy-groups": [{"name": n, "type": "url-test", "proxies": members, "interval": 180, "tolerance": 100}
                         for n, members in [("普通出网", ["carrier"]), ("AI出网", ["residential"]), ("Gemini-US", ["carrier"])]],
        "rule-providers": providers,
        "rules": ["RULE-SET,simple-gemini,Gemini-US", "RULE-SET,simple-ai,AI出网", "RULE-SET,peter-ai,AI出网",
                  "RULE-SET,simple-domestic,DIRECT", "MATCH,AI出网"],
    }
    files = {f"rule_provider/simple-{n}.yaml": {"payload": [f"DOMAIN-SUFFIX,{n}.example"]}
             for n in ("ai", "domestic", "general", "gemini", "priority")}
    files["rule_provider/simple-domestic.yaml"]["payload"] += ["IP-CIDR,192.0.2.0/24,no-resolve", "PROCESS-NAME,ssh"]
    settings = {"verified_server_side_ai_nodes": {}, "residential_server": "192.0.2.2",
                "residential_certificate_sha256": pin, "public_rule_urls": [url]}
    return source, files, settings


def archive(source, files, saved=None):
    contents = dict(files, **{"Home-Auto.yaml": source, "config/Home-Auto.yaml": saved or source})
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as tar:
        for name, value in contents.items():
            data = yaml.safe_dump(value).encode()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
    return output.getvalue()


def source_ip_fixture():
    source, files, settings = fixture()
    transport = {"name": "BWH-Direct", "type": "vless", "server": "192.0.2.3",
                 "port": 443, "uuid": "TEST-TRANSPORT", "tls": True}
    exit_node = {"name": "Fixed-via-BWH", "type": "http", "server": "192.0.2.4",
                 "port": 6151, "tls": False, "skip-cert-verify": False,
                 "udp": False, "dialer-proxy": "BWH-Direct"}
    source["proxies"] = [transport, exit_node]
    source["proxy-groups"] = source["proxy-groups"][:2]
    source["proxy-groups"][0]["proxies"] = [transport["name"]]
    source["proxy-groups"][1].update(type="fallback", proxies=[exit_node["name"]])
    source["rules"][0] = "RULE-SET,simple-gemini,AI出网"
    source["rules"][-1] = "MATCH,普通出网"
    settings["ai_path_policy"] = {
        "preferred": exit_node["name"], "authentication": "source-ip",
        "nodes": {exit_node["name"]: export.digest_node(exit_node)},
        "upstreams": {transport["name"]: export.digest_node(transport)},
        "default_target": "普通出网", "gemini_target": "AI出网",
    }
    return source, files, settings


class ExportTests(unittest.TestCase):
    def test_fixed_home_egress_exports_switchable_transits(self):
        source, files, settings = source_ip_fixture()
        bwh, webshare = source["proxies"]
        rack = dict(bwh, name="RackNerd-Direct", server="192.0.2.7", udp=True)
        trusted_webshare = dict(webshare, name="Webshare-via-BWH")
        via_bwh = dict(webshare, name="AI-Webshare-BWH", **{"dialer-proxy": "BWH-Direct"})
        via_rack = dict(webshare, name="AI-Webshare-RackNerd", **{"dialer-proxy": "RackNerd-Direct"})
        settings["ai_path_policy"].update(
            preferred=trusted_webshare["name"],
            nodes={trusted_webshare["name"]: export.digest_node(trusted_webshare)},
        )
        settings["dynamic_egress_policy"] = {
            "nodes": {node["name"]: export.digest_node(node) for node in (bwh, rack)},
        }
        settings["ordinary_path_policy"] = {
            "preferred": bwh["name"], "node_sha256": export.digest_node(bwh),
        }
        settings["fixed_home_egress"] = True
        source["proxies"] = [bwh, rack, via_bwh, via_rack]
        ordinary = {"name": "普通出网", "type": "select", "proxies": ["BWH-Direct", "RackNerd-Direct", "普通自动"],
                    "default-selected": "BWH-Direct", "disable-udp": True}
        auto = {"name": "普通自动", "type": "url-test", "proxies": ["BWH-Direct", "RackNerd-Direct"],
                "interval": 180, "tolerance": 100, "hidden": True}
        ai = {"name": "AI出网", "type": "select", "proxies": ["AI-Webshare-BWH", "AI-Webshare-RackNerd"],
              "default-selected": "AI-Webshare-BWH", "disable-udp": True}
        source["proxy-groups"] = [ordinary, auto, ai]
        phone = export.convert(source, files, settings)
        proxies = {node["name"]: node for node in phone["proxies"]}
        self.assertIs(proxies["RackNerd-Direct"]["udp"], False)
        self.assertEqual(proxies["AI-Webshare-BWH"]["dialer-proxy"], "BWH-Direct")
        self.assertEqual(proxies["AI-Webshare-RackNerd"]["dialer-proxy"], "RackNerd-Direct")
        for name in ("AI-Webshare-BWH", "AI-Webshare-RackNerd"):
            with self.subTest(name=name):
                self.assertEqual(proxies[name + "-SOCKS5"],
                                 dict(proxies[name], name=name + "-SOCKS5", type="socks5"))
        groups = {group["name"]: group for group in phone["proxy-groups"]}
        self.assertEqual(groups["普通出网"]["proxies"], ["BWH-Direct", "RackNerd-Direct", "普通自动"])
        self.assertEqual(groups["普通自动"]["proxies"], ["BWH-Direct", "RackNerd-Direct"])
        self.assertEqual(groups["AI出网"]["proxies"],
                         ["AI-Webshare-BWH", "AI-Webshare-BWH-SOCKS5",
                          "AI-Webshare-RackNerd", "AI-Webshare-RackNerd-SOCKS5"])
        self.assertEqual(len([g for g in phone["proxy-groups"] if g["name"] == "普通自动"]), 1)
        for change in ("endpoint", "transport", "transit", "automatic", "unreviewed"):
            with self.subTest(change=change):
                bad, approval = copy.deepcopy(source), copy.deepcopy(settings)
                if change == "endpoint":
                    bad["proxies"][3]["port"] = 1234
                elif change == "transport":
                    bad["proxies"][1]["server"] = "192.0.2.8"
                elif change == "transit":
                    bad["proxies"][3]["dialer-proxy"] = "BWH-Direct"
                elif change == "automatic":
                    bad["proxy-groups"][1]["interval"] = 60
                else:
                    approval.pop("fixed_home_egress")
                with self.assertRaises(export.ExportError):
                    export.convert(bad, files, approval)

    def test_reviewed_shared_egress_exports_portable_health_selection(self):
        source, files, settings = source_ip_fixture()
        bwh = source["proxies"][0]
        carrier = {"name": "carrier", "type": "ss", "server": "192.0.2.5", "port": 443,
                   "cipher": "aes-128-gcm", "password": "TEST-ONLY"}
        source["proxies"] = [bwh, carrier]
        source["proxy-groups"] = [
            {"name": "普通出网", "type": "fallback", "proxies": [bwh["name"], carrier["name"]], "disable-udp": True},
            {"name": "AI出网", "type": "select", "proxies": ["普通出网"], "disable-udp": True},
        ]
        settings["ordinary_path_policy"] = {"preferred": bwh["name"], "node_sha256": export.digest_node(bwh)}
        settings["dynamic_egress_policy"] = {"nodes": {n["name"]: export.digest_node(n) for n in source["proxies"]}}
        phone = export.convert(source, files, settings)
        self.assertEqual(phone["proxy-groups"][0]["type"], "url-test")
        self.assertEqual(phone["proxy-groups"][1]["proxies"], ["普通出网"])
        for change in ("direct", "identity", "include-all"):
            with self.subTest(change=change):
                bad = copy.deepcopy(source)
                if change == "direct":
                    bad["proxy-groups"][1]["proxies"] = ["DIRECT"]
                elif change == "identity":
                    bad["proxies"][1]["server"] = "192.0.2.6"
                else:
                    bad["proxy-groups"][0]["include-all"] = True
                with self.assertRaises(export.ExportError):
                    export.convert(bad, files, settings)

    def test_model_downloads_use_only_reviewed_carriers(self):
        source, files, settings = source_ip_fixture()
        carrier = {"name": "carrier", "type": "ss", "server": "192.0.2.5", "port": 443,
                   "cipher": "aes-128-gcm", "password": "TEST-ONLY", "udp": True}
        source["proxies"].append(carrier)
        pool = {"type": "url-test", "proxies": ["carrier"], "interval": 180, "tolerance": 100, "lazy": True}
        source["proxy-groups"].extend([
            dict(pool, name="PS5出网", hidden=True, **{"disable-udp": False}),
            dict(pool, name="模型下载", **{"disable-udp": True}),
        ])
        settings["gaming_path_policy"] = {
            "group": "PS5出网", "source_cidr": "192.168.1.200/32", "udp_verified": True,
            "nodes": {"carrier": export.digest_node(carrier)},
        }
        settings["model_download_policy"] = {"matches": ["DOMAIN-SUFFIX,hf.co"]}
        model_rule = "DOMAIN-SUFFIX,hf.co,模型下载"
        source["rules"][3:3] = [model_rule, export.gaming_source_rule(settings["gaming_path_policy"])]
        phone = export.convert(source, files, settings)
        self.assertIn(model_rule, phone["rules"])
        self.assertEqual(phone["proxy-groups"][-1]["proxies"], ["carrier"])
        for change in ("vps", "include-all", "rule-order"):
            with self.subTest(change=change):
                changed = copy.deepcopy(source)
                if change == "vps":
                    changed["proxy-groups"][-1]["proxies"].append("BWH-Direct")
                elif change == "include-all":
                    changed["proxy-groups"][-1]["include-all"] = True
                else:
                    changed["rules"].remove(model_rule)
                    changed["rules"].insert(-1, model_rule)
                with self.assertRaises(export.ExportError):
                    export.convert(changed, files, settings)
        metered, reviewed = copy.deepcopy(source), copy.deepcopy(settings)
        bwh = metered["proxies"][0]
        metered["proxy-groups"][0]["type"] = "fallback"
        reviewed["ordinary_path_policy"] = {"preferred": "BWH-Direct", "node_sha256": export.digest_node(bwh)}
        name = "BWH-Model-Metered"
        mark = 0x4D444C01
        reviewed["model_download_policy"]["metered"] = {"node": name, "routing_mark": mark,
                                                        "carrier_order": ["carrier"]}
        metered["proxies"].append(dict(bwh, name=name, **{"routing-mark": mark}))
        metered["proxy-groups"][-1].update(type="select", proxies=[name, "模型华云"],
                                          **{"default-selected": "模型华云"})
        metered["proxy-groups"].append(dict(pool, name="模型华云", type="fallback", hidden=True,
                                            **{"disable-udp": True}))
        phone = export.convert(metered, files, reviewed)
        self.assertEqual(phone["proxy-groups"][-1]["proxies"], ["carrier"])
        self.assertNotIn(name, {node["name"] for node in phone["proxies"]})
        metered["proxies"][-1].pop("routing-mark")
        with self.assertRaises(export.ExportError):
            export.convert(metered, files, reviewed)

    def test_reviewed_gaming_pool_never_uses_paid_or_preferred_transport(self):
        s, f, p = source_ip_fixture()
        game = {"name": "game-carrier", "type": "ss", "server": "192.0.2.5", "port": 443,
                "cipher": "aes-128-gcm", "password": "TEST-ONLY", "udp": False}
        s["proxies"].append(game)
        s["proxy-groups"].append({"name": "PS5出网", "type": "url-test", "proxies": [game["name"]],
                                  "hidden": True, "disable-udp": True})
        p["gaming_path_policy"] = {"group": "PS5出网", "source_cidr": "192.168.1.200/32",
                                    "nodes": {game["name"]: export.digest_node(game)}, "domains": ["playstation.com"]}
        source_rule = export.gaming_source_rule(p["gaming_path_policy"])
        domain_rule = "DOMAIN-SUFFIX,playstation.com,PS5出网"
        s["rules"][3:3] = [domain_rule, source_rule]
        phone = export.convert(s, f, p)
        self.assertIn(domain_rule, phone["rules"])
        self.assertNotIn(source_rule, phone["rules"])
        self.assertEqual(phone["proxy-groups"][-1]["proxies"], [game["name"]])
        udp_source, udp_policy = copy.deepcopy(s), copy.deepcopy(p)
        udp_source["proxies"][-1]["udp"] = True
        udp_source["proxy-groups"][-1]["disable-udp"] = False
        udp_policy["gaming_path_policy"].update(udp_verified=True, nodes={game["name"]: export.digest_node(udp_source["proxies"][-1])})
        self.assertTrue(export.convert(udp_source, f, udp_policy)["proxies"][-1]["udp"])
        console_only, console_settings = copy.deepcopy(udp_source), copy.deepcopy(udp_policy)
        console_only["rules"].remove(domain_rule)
        console_only["proxy-groups"][0]["disable-udp"] = True
        console_settings["gaming_path_policy"]["domains"] = []
        console_phone = export.convert(console_only, f, console_settings)
        self.assertNotIn("PS5出网", [g["name"] for g in console_phone["proxy-groups"]])
        self.assertNotIn(source_rule, console_phone["rules"])
        self.assertFalse(console_phone["proxies"][-1]["udp"])
        for change in ["member", "identity", "source", "precedence", "unreviewed", "visible", "udp"]:
            with self.subTest(change=change):
                bad, settings = copy.deepcopy(s), copy.deepcopy(p)
                if change == "member": bad["proxy-groups"][-1]["proxies"].append("BWH-Direct")
                elif change == "identity": bad["proxies"][-1]["password"] = "CHANGED"
                elif change == "source": bad["rules"] = [r.replace("192.168.1.200/32", "192.168.1.0/24") for r in bad["rules"]]
                elif change == "precedence": bad["rules"].remove(source_rule);bad["rules"].insert(0, source_rule)
                elif change == "unreviewed": settings.pop("gaming_path_policy")
                elif change == "visible": bad["proxy-groups"][-1]["hidden"] = False
                else: bad["proxy-groups"][-1]["disable-udp"] = False
                with self.assertRaises(export.ExportError): export.convert(bad, f, settings)

    def test_reviewed_ordinary_priority_preserves_ai_and_rejects_drift(self):
        source, files, settings = source_ip_fixture()
        ordinary = source["proxy-groups"][0]
        ordinary.update(type="fallback", proxies=["BWH-Direct", "backup"])
        ordinary.pop("tolerance", None)
        source["proxies"].append({"name": "backup", "type": "ss", "server": "192.0.2.5",
                                  "port": 443, "cipher": "aes-128-gcm", "password": "TEST-ONLY"})
        settings["ordinary_path_policy"] = {"preferred": "BWH-Direct",
                                            "node_sha256": export.digest_node(source["proxies"][0])}
        source["rules"].insert(3, "DOMAIN-SUFFIX,github.com,普通出网")
        phone = export.convert(source, files, settings)
        self.assertEqual(phone["proxy-groups"][0]["proxies"], ["BWH-Direct", "backup"])
        self.assertEqual(phone["proxy-groups"][0]["type"], "fallback")
        self.assertEqual(phone["proxy-groups"][1]["proxies"], ["Fixed-via-BWH"])
        self.assertIn("DOMAIN-SUFFIX,github.com,普通出网", phone["rules"])
        for change in ["order", "identity", "tls", "chained", "unreviewed", "type", "direct"]:
            with self.subTest(change=change):
                s, p = copy.deepcopy(source), copy.deepcopy(settings)
                if change == "order": s["proxy-groups"][0]["proxies"].reverse()
                elif change == "identity": s["proxies"][0]["uuid"] = "CHANGED"
                elif change == "tls": s["proxies"][0]["tls"] = False
                elif change == "chained": s["proxies"][0]["dialer-proxy"] = "backup"
                elif change == "unreviewed": p.pop("ordinary_path_policy")
                elif change == "type": s["proxy-groups"][0]["type"] = "url-test"
                else: s["proxy-groups"][0]["proxies"].append("DIRECT")
                with self.assertRaises(export.ExportError): export.convert(s, files, p)

    def test_passwordless_fixed_ai_keeps_gemini_and_saves_ordinary_traffic(self):
        source, files, settings = source_ip_fixture()
        phone = export.convert(source, files, settings)
        self.assertEqual({g["name"] for g in phone["proxy-groups"]}, {"普通出网", "AI出网"})
        self.assertEqual(phone["rules"][0], "DOMAIN-SUFFIX,gemini.example,AI出网")
        self.assertEqual(phone["rules"][-1], "MATCH,普通出网")
        self.assertEqual(phone["proxies"][1]["dialer-proxy"], "BWH-Direct")
        self.assertNotIn("password", phone["proxies"][1])
        self.assertNotIn("username", phone["proxies"][1])

    def test_passwordless_ai_rejects_identity_transport_and_route_drift(self):
        for change in ["exit_address", "exit_port", "transport_identity", "plain_transport",
                       "ordinary_member", "missing_path", "unknown_path", "default_ai",
                       "extra_default", "gemini_exception", "unapproved_http"]:
            with self.subTest(change=change):
                s, f, p = source_ip_fixture()
                if change == "exit_address": s["proxies"][1]["server"] = "192.0.2.99"
                elif change == "exit_port": s["proxies"][1]["port"] += 1
                elif change == "transport_identity": s["proxies"][0]["uuid"] = "CHANGED"
                elif change == "plain_transport": s["proxies"][0]["tls"] = False
                elif change == "ordinary_member": s["proxy-groups"][0]["proxies"].append("Fixed-via-BWH")
                elif change == "missing_path": s["proxy-groups"][1]["proxies"] = []
                elif change == "unknown_path": s["proxy-groups"][1]["proxies"].append("DIRECT")
                elif change == "default_ai": s["rules"][-1] = "MATCH,AI出网"
                elif change == "extra_default": s["rules"].insert(-1, "MATCH,DIRECT")
                elif change == "gemini_exception": s["rules"][0] = "RULE-SET,simple-gemini,Gemini-US"
                else:
                    node = copy.deepcopy(s["proxies"][1]);node["name"] = "UNAPPROVED"
                    s["proxies"].append(node)
                with self.assertRaises(export.ExportError): export.convert(s, f, p)

    def test_passwordless_policy_never_exports_proxy_password_even_if_hash_updated(self):
        s, f, p = source_ip_fixture()
        s["proxies"][1]["password"] = "MUST-NOT-EXPORT"
        p["ai_path_policy"]["nodes"]["Fixed-via-BWH"] = export.digest_node(s["proxies"][1])
        with tempfile.TemporaryDirectory() as tmp:
            p.update(local_output=str(Path(tmp)/"phone.yaml"), icloud_output=str(Path(tmp)/"cloud.yaml"))
            for path in [p["local_output"], p["icloud_output"]]: Path(path).write_text("KNOWN GOOD")
            with self.assertRaises(export.ExportError): export.export(p, archive(s, f), sync=True)
            for path in [p["local_output"], p["icloud_output"]]: self.assertEqual(Path(path).read_text(), "KNOWN GOOD")

    def test_ai_priority_fallback_preserves_verified_residential_paths(self):
        s, f, p = fixture()
        bwh = copy.deepcopy(s["proxies"][1])
        bwh["name"] = "Lisa-via-BWH"
        s["proxies"].append(bwh)
        p["verified_server_side_ai_nodes"][bwh["name"]] = export.digest_node(bwh)
        group = s["proxy-groups"][1]
        group.update(type="fallback", proxies=[bwh["name"], "residential"])
        phone = export.convert(s, f, p)
        self.assertEqual(phone["proxy-groups"][1]["type"], "fallback")
        self.assertEqual(phone["proxy-groups"][1]["proxies"], [bwh["name"], "residential"])
        for change in ["ordinary", "empty", "order", "identity", "ordinary_group", "untrusted"]:
            with self.subTest(change=change):
                bad, settings = copy.deepcopy(s), copy.deepcopy(p)
                if change == "ordinary":
                    bad["proxy-groups"][1]["proxies"].append("carrier")
                elif change == "empty":
                    bad["proxy-groups"][1]["proxies"] = []
                elif change == "order":
                    bad["proxy-groups"][1]["proxies"].reverse()
                elif change == "identity":
                    bad["proxies"][-1]["uuid"] = "CHANGED"
                elif change == "ordinary_group":
                    bad["proxy-groups"][0]["type"] = "fallback"
                else:
                    settings["verified_server_side_ai_nodes"] = {}
                with self.assertRaises(export.ExportError):
                    export.convert(bad, f, settings)

    def test_fixed_developer_route_preserves_node_and_ai_precedence(self):
        s, f, p = fixture()
        node = {"name": "BWH-Direct", "type": "vless", "server": "192.0.2.3",
                "port": 443, "uuid": "TEST-ONLY", "tls": True}
        s["proxies"].append(node)
        s["proxy-groups"][0]["proxies"].append("BWH-Direct")
        rule = "DOMAIN-SUFFIX,github.com,BWH-Direct"
        s["rules"].insert(3, rule)
        phone = export.convert(s, f, p)
        self.assertIn(node, [{k: v for k, v in n.items() if not k.startswith("benchmark-")}
                             for n in phone["proxies"]])
        self.assertLess(phone["rules"].index("RULE-SET,peter-ai,AI出网"), phone["rules"].index(rule))
        self.assertEqual(phone["rules"][-1], "MATCH,AI出网")
        for change in ["missing", "chained", "precedence"]:
            with self.subTest(change=change):
                bad = copy.deepcopy(s)
                if change == "missing":
                    bad["proxies"].pop()
                    bad["proxy-groups"][0]["proxies"].remove("BWH-Direct")
                elif change == "chained":
                    bad["proxies"][-1]["dialer-proxy"] = "carrier"
                else:
                    bad["rules"].remove(rule)
                    bad["rules"].insert(0, rule)
                with self.assertRaises(export.ExportError):
                    export.convert(bad, f, p)

    def test_portable_route_order_and_pinned_tls(self):
        source, files, settings = fixture()
        phone = export.convert(source, files, settings)
        text = yaml.safe_dump(phone)
        for forbidden in ["DO-NOT-EXPORT", "external-controller", "127.0.0.1:5335", "rule_provider/", "PROCESS-NAME"]:
            self.assertNotIn(forbidden, text)
        self.assertEqual(phone["rules"][:2], ["DOMAIN-SUFFIX,gemini.example,Gemini-US", "DOMAIN-SUFFIX,ai.example,AI出网"])
        self.assertIn("IP-CIDR,192.0.2.0/24,DIRECT,no-resolve", phone["rules"])
        self.assertEqual(phone["rules"][-1], "MATCH,AI出网")
        self.assertFalse(phone["ipv6"])
        self.assertEqual(phone["proxies"][1]["server-cert-fingerprint"], "ab" * 32)
        self.assertEqual(phone["proxies"][1]["sni"], "test.invalid")
        self.assertEqual(phone["proxies"][1]["dialer-proxy"], "carrier")

    def test_ai_cannot_fall_back_to_ordinary_or_empty_group(self):
        for members in [[], ["carrier"], ["DIRECT"]]:
            with self.subTest(members=members):
                s, f, p = fixture()
                s["proxy-groups"][1]["proxies"] = members
                with self.assertRaises(export.ExportError):
                    export.convert(s, f, p)

    def test_invalid_pin_disabled_verification_and_chain_cycle_rejected(self):
        for change in [{"fingerprint": "cd" * 32}, {"skip-cert-verify": True}, {"dialer-proxy": "residential"}]:
            with self.subTest(change=change):
                s, f, p = fixture()
                s["proxies"][1].update(change)
                with self.assertRaises(export.ExportError):
                    export.convert(s, f, p)

    def test_server_side_identity_is_not_silently_retrusted(self):
        s, f, p = fixture()
        p["verified_server_side_ai_nodes"] = {"residential": export.digest_node(s["proxies"][1])}
        s["proxies"][1]["uuid"] = "CHANGED"
        with self.assertRaises(export.ExportError):
            export.convert(s, f, p)

    def test_live_persistent_divergence_rejected(self):
        s, f, p = fixture()
        saved = copy.deepcopy(s)
        saved["rules"][-1] = "MATCH,DIRECT"
        with self.assertRaises(export.ExportError):
            export.unpack_source(archive(s, f, saved))

    def test_invalid_export_preserves_both_previous_files(self):
        s, f, p = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p.update(local_output=str(Path(tmp) / "phone.yaml"), icloud_output=str(Path(tmp) / "cloud.yaml"))
            for path in [p["local_output"], p["icloud_output"]]:
                Path(path).write_text("KNOWN GOOD")
            s["proxies"][1]["skip-cert-verify"] = True
            with self.assertRaises(export.ExportError):
                export.export(p, archive(s, f), sync=True)
            for path in [p["local_output"], p["icloud_output"]]:
                self.assertEqual(Path(path).read_text(), "KNOWN GOOD")

    def test_sync_is_private_idempotent_and_records_limits(self):
        s, f, p = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p.update(local_output=str(Path(tmp) / "phone.yaml"), icloud_output=str(Path(tmp) / "cloud.yaml"))
            export.export(p, archive(s, f), sync=True)
            receipt = export.export(p, archive(s, f), sync=True)
            self.assertFalse(receipt["icloud_changed"])
            self.assertFalse(receipt["iphone_activation_verified"])
            for name in ["phone.yaml", "cloud.yaml", "export-receipt.json"]:
                self.assertEqual((Path(tmp) / name).stat().st_mode & 0o777, 0o600)
            self.assertEqual(Path(p["local_output"]).read_bytes(), Path(p["icloud_output"]).read_bytes())


if __name__ == "__main__":
    unittest.main()

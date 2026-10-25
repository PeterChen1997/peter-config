"""Workflow checks, including a real mihomo outage/recovery exercise.

MIHOMO_BIN=/path/to/mihomo python3 -m unittest discover -s config/clash/openclash -v
The integration test uses only loopback fake subscriptions/proxies and temporary files.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import patch

import yaml

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_config", HERE / "build_config.py")
build_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_config)


class BuildTests(unittest.TestCase):
    def test_unwrap_only_known_provider(self):
        url = "https://api-huacloud.com/sub?url=https%3A%2F%2Fapi.xmancdn.net%2Fosubscribe.php%3Ftoken2%3Dfake"
        self.assertEqual(build_config.flower_origin(url), "https://api.xmancdn.net/osubscribe.php?token2=fake")
        with self.assertRaises(ValueError):
            build_config.flower_origin("https://api-huacloud.com/sub?url=https%3A%2F%2Fevil.example%2F")

    def test_preserve_obfs_and_exclude_metadata(self):
        import base64
        uri = "ss://YWVzLTEyOC1nY206ZmFrZQ@127.0.0.1:443/?plugin=simple-obfs%3Bobfs%3Dhttp%3Bobfs-host%3Dexample.com#日本"
        meta = uri.rsplit("#", 1)[0] + "#Traffic:%200%20GB"
        raw = base64.b64encode((uri + "\n" + meta).encode()).rstrip(b"=")
        nodes = build_config.parse_subscription(raw)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["plugin-opts"], {"mode": "http", "host": "example.com"})

    def test_failed_fetch_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "peter-home.yaml"
            output.write_text("previous working config")
            with patch.object(build_config, "fetch", side_effect=urllib.error.HTTPError("https://example.com/?token=secret", 403, "Forbidden", {}, None)):
                with self.assertRaises(ValueError) as result:
                    build_config.build({"equalvpn": "https://example.com", "huayun": "https://example.com"}, output)
            self.assertNotIn("secret", str(result.exception))
            self.assertEqual(output.read_text(), "previous working config")

    def test_no_residential_stops_build(self):
        body = yaml.safe_dump({"proxies": [{"name": "娱乐", "type": "ss", "server": "example.com", "port": 443}]}).encode()
        with tempfile.TemporaryDirectory() as directory, patch.object(build_config, "fetch", return_value=body):
            output = Path(directory) / "peter-home.yaml"
            with self.assertRaises(ValueError):
                build_config.build({"equalvpn": "https://example.com", "huayun": "https://example.com"}, output)
            self.assertFalse(output.exists())


@unittest.skipUnless(os.environ.get("MIHOMO_BIN"), "Set MIHOMO_BIN for real-core integration")
class CoreFailoverTests(unittest.TestCase):
    def test_native_refresh_cache_and_manual_only_residential(self):
        state = {"cheap_alive": True, "subscription_ok": True}

        class HealthProxy(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(204 if self.server.residential or state["cheap_alive"] else 503)
                self.send_header("Connection", "close")
                self.end_headers()

            do_HEAD = do_GET

            def do_CONNECT(self):
                self.send_response(200)
                self.end_headers()
                self.connection.settimeout(3)
                while self.rfile.readline().strip():
                    pass
                code = b"204 No Content" if self.server.residential or state["cheap_alive"] else b"503 Unavailable"
                self.wfile.write(b"HTTP/1.1 " + code + b"\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")

            def log_message(self, *args):
                pass

        servers = []
        def serve(handler):
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            return server

        cheap = serve(HealthProxy)
        cheap.residential = False
        residential = serve(HealthProxy)
        residential.residential = True
        def node(name, server):
            return {"name": name, "type": "http", "server": "127.0.0.1", "port": server.server_port}
        subscriptions = {
            "/equalvpn": {"proxies": [node("专属纯净静态住宅节点", residential), node("美国娱乐", cheap)]},
            "/huayun": {"proxies": [node("日本 IEPL", cheap), node("Traffic: 0 GB", cheap)]},
        }

        class Subscription(BaseHTTPRequestHandler):
            def do_GET(self):
                if not state["subscription_ok"]:
                    self.send_response(503)
                    self.end_headers()
                    return
                body = yaml.safe_dump(subscriptions[self.path], allow_unicode=True).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        subscription = serve(Subscription)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            controller_port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{controller_port}"
        def api(path, method="GET", data=None):
            req = urllib.request.Request(base + path, method=method,
                                         data=json.dumps(data).encode() if data else None,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=4) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}

        def await_status(predicate):
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                try:
                    data = api("/proxies")["proxies"]
                    providers = api("/providers/proxies")["providers"]
                    for provider in [providers["equalvpn"], providers["huayun"]]:
                        data.update({node["name"]: node for node in provider.get("proxies", [])})
                    if predicate(data):
                        return data
                except (OSError, KeyError):
                    pass
                time.sleep(0.25)
            status = {name: {k: value.get(k) for k in ["now", "all", "alive", "history", "extra"]}
                      for name, value in data.items()
                      if name in {"大流量自动", "大流量", "AI 专线", "住宅节点"} or name.startswith("[")}
            self.fail(f"Expected core state was not reached: {status}")

        def alive_at_health_url(node):
            return node.get("extra", {}).get(health_url, node).get("alive")

        def cheap_healthy(groups):
            group = groups["大流量自动"]
            return bool(group.get("all")) and all(alive_at_health_url(groups[name]) for name in group["all"])

        process = None
        try:
            with tempfile.TemporaryDirectory() as directory:
                cfg = yaml.safe_load((HERE / "home-template.yaml").read_text())
                cfg.update({"mixed-port": 0, "redir-port": 0, "tproxy-port": 0,
                            "external-controller": f"127.0.0.1:{controller_port}",
                            "dns": {"enable": False}, "rules": ["MATCH,大流量"], "rule-providers": {}})
                health_url = "http://health.invalid/generate_204"
                for name, provider in cfg["proxy-providers"].items():
                    provider["url"] = f"http://127.0.0.1:{subscription.server_port}/{name}"
                    provider["interval"] = 3600
                    provider["health-check"].update({"url": health_url, "interval": 1})
                for group in cfg["proxy-groups"]:
                    if group["type"] in {"url-test", "fallback"}:
                        group.update({"url": health_url, "interval": 1, "expected-status": 204})
                path = Path(directory) / "config.yaml"
                path.write_text(yaml.safe_dump(cfg, allow_unicode=True))
                with open(Path(directory) / "core.log", "w") as log:
                    process = subprocess.Popen([os.environ["MIHOMO_BIN"], "-d", directory, "-f", str(path)], stdout=log, stderr=log)
                    groups = await_status(cheap_healthy)
                    self.assertEqual(groups["大流量自动"]["type"], "URLTest")
                    self.assertNotIn("AI 专线", groups["大流量自动"]["all"])
                    self.assertNotIn("住宅节点", groups["大流量自动"]["all"])
                    self.assertTrue(set(groups["大流量自动"]["all"]).isdisjoint(groups["住宅节点"]["all"]))
                    self.assertIn("AI 专线", groups["大流量"]["all"])
                    # No cache was preloaded; these nodes must have come from native HTTP.
                    providers = api("/providers/proxies")["providers"]
                    self.assertEqual(len(providers["huayun"]["proxies"]), 1)
                    subscriptions["/huayun"]["proxies"].append(node("美国新增 IEPL", cheap))
                    api("/providers/proxies/huayun", "PUT")
                    self.assertEqual(len(api("/providers/proxies")["providers"]["huayun"]["proxies"]), 2)
                    state["subscription_ok"] = False
                    with self.assertRaises(urllib.error.HTTPError):
                        api("/providers/proxies/huayun", "PUT")
                    self.assertEqual(len(api("/providers/proxies")["providers"]["huayun"]["proxies"]), 2)
                    state["cheap_alive"] = False
                    groups = await_status(lambda g: all(not alive_at_health_url(g[name]) for name in g["大流量自动"]["all"]))
                    self.assertIn(groups["大流量自动"]["now"], groups["大流量自动"]["all"])
                    self.assertEqual(groups["大流量"]["now"], "大流量自动")
                    self.assertTrue(set(groups["大流量自动"]["all"]).isdisjoint(groups["住宅节点"]["all"]))
                    # Only an explicit menu selection may borrow the residential path.
                    manual_path = "/proxies/" + urllib.parse.quote("大流量")
                    api(manual_path, "PUT", {"name": "AI 专线"})
                    groups = api("/proxies")["proxies"]
                    self.assertEqual(groups["大流量"]["now"], "AI 专线")
                    self.assertEqual(groups["AI 专线"]["now"], "住宅节点")
                    delay = api(manual_path + "/delay?" + urllib.parse.urlencode({"url": health_url, "timeout": 3000}))
                    self.assertIn("delay", delay)
                    state["cheap_alive"] = True
                    await_status(cheap_healthy)
                    # Manual selection persists until the user switches back.
                    self.assertEqual(api("/proxies")["proxies"]["大流量"]["now"], "AI 专线")
                    api(manual_path, "PUT", {"name": "大流量自动"})
                    # Fresh start with no residential nodes: reject, never silently DIRECT.
                    process.terminate()
                    process.wait(timeout=5)
                    state["subscription_ok"] = True
                    subscriptions["/equalvpn"]["proxies"] = [node("美国娱乐", cheap)]
                    cache = Path(directory) / cfg["proxy-providers"]["equalvpn"]["path"]
                    cache.unlink(missing_ok=True)
                    process = subprocess.Popen([os.environ["MIHOMO_BIN"], "-d", directory, "-f", str(path)], stdout=log, stderr=log)
                    groups = await_status(cheap_healthy)
                    self.assertEqual(groups["住宅节点"]["now"], "REJECT")
        finally:
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            for server in servers:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()

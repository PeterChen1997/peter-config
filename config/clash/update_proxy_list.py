#!/usr/bin/env python3
"""Maintain the family Clash proxy rule list.

Examples:
  # Add URLs/domains to config/clash/proxy.list (default file)
  python config/clash/update_proxy_list.py https://example.com/path openai.com

  # Preview changes without writing
  python config/clash/update_proxy_list.py --dry-run https://example.com/path

  # Force a specific Clash rule type
  python config/clash/update_proxy_list.py --type DOMAIN-KEYWORD cursor
  python config/clash/update_proxy_list.py --type DOMAIN-SUFFIX example.com
  python config/clash/update_proxy_list.py --type DOMAIN api.example.com
  python config/clash/update_proxy_list.py --type IP-CIDR 1.2.3.4/32

  # Add a note comment above newly added rules
  python config/clash/update_proxy_list.py --comment "2026-05-31: dev tools" replit.com cursor.com

The script is intentionally conservative:
- It preserves the existing file order and comments.
- It appends only missing rules.
- It deduplicates case-insensitively.
- URL inputs become DOMAIN-SUFFIX rules for their hostname by default.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

VALID_RULE_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR"}
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?!-)(?:[A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,63}\.?$")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_proxy_list() -> Path:
    return Path(__file__).resolve().parent / "proxy.list"


def normalize_host(host: str) -> str:
    host = host.strip().lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def extract_target(raw: str) -> tuple[str, str]:
    """Return (kind, value), where kind is url/domain/ipcidr/keyword."""
    value = raw.strip()
    if not value:
        raise ValueError("empty input")

    # Existing Clash rule: TYPE,value
    if "," in value:
        maybe_type, maybe_value = value.split(",", 1)
        if maybe_type.strip().upper() in VALID_RULE_TYPES:
            return maybe_type.strip().upper().lower(), maybe_value.strip()

    # IP address or CIDR. Check this before host/path parsing because CIDR contains '/'.
    try:
        if "/" in value:
            return "ipcidr", str(ipaddress.ip_network(value, strict=False))
        ip = ipaddress.ip_address(value)
        return "ipcidr", f"{ip}/32"
    except ValueError:
        pass

    # URL without scheme is common in chat; add scheme only for parsing when it looks URL-ish.
    parse_value = value
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", parse_value):
        parsed = urlparse(parse_value)
        host = parsed.hostname
        if not host:
            raise ValueError(f"cannot extract hostname from URL: {raw}")
        return "domain", normalize_host(host)

    # Host/path without scheme, e.g. example.com/foo
    if "/" in parse_value and not parse_value.startswith("/"):
        parsed = urlparse("https://" + parse_value)
        if parsed.hostname:
            return "domain", normalize_host(parsed.hostname)

    normalized = normalize_host(value)
    if DOMAIN_RE.match(normalized):
        return "domain", normalized

    return "keyword", value.strip().lower()


def make_rule(raw: str, forced_type: str | None) -> str:
    kind, value = extract_target(raw)
    if forced_type:
        rule_type = forced_type.upper()
        if rule_type == "IP-CIDR":
            try:
                if "/" not in value:
                    value = f"{ipaddress.ip_address(value)}/32"
                else:
                    value = str(ipaddress.ip_network(value, strict=False))
            except ValueError as exc:
                raise ValueError(f"{raw!r} is not a valid IP/CIDR for IP-CIDR") from exc
        elif rule_type in {"DOMAIN", "DOMAIN-SUFFIX"}:
            value = normalize_host(value)
            if not DOMAIN_RE.match(value):
                raise ValueError(f"{raw!r} is not a valid domain for {rule_type}")
        elif rule_type == "DOMAIN-KEYWORD":
            value = value.strip().lower()
        return f"{rule_type},{value}"

    if kind == "ipcidr":
        return f"IP-CIDR,{value}"
    if kind in {"domain", "domain-suffix"}:
        return f"DOMAIN-SUFFIX,{value}"
    if kind == "domain-keyword" or kind == "keyword":
        return f"DOMAIN-KEYWORD,{value}"
    if kind == "domain":
        return f"DOMAIN,{value}"
    return f"DOMAIN-SUFFIX,{value}"


def normalized_rule_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "," not in stripped:
        return stripped.lower()
    rule_type, value = stripped.split(",", 1)
    return f"{rule_type.strip().upper()},{value.strip().lower()}"


def update_file(path: Path, rules: list[str], comment: str | None, dry_run: bool) -> tuple[list[str], list[str]]:
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = original.splitlines()
    existing = {key for line in lines if (key := normalized_rule_key(line))}

    added: list[str] = []
    skipped: list[str] = []
    seen_new: set[str] = set()
    for rule in rules:
        key = normalized_rule_key(rule)
        if key is None:
            skipped.append(rule)
            continue
        if key in existing or key in seen_new:
            skipped.append(rule)
            continue
        added.append(rule)
        seen_new.add(key)

    if added and not dry_run:
        new_lines = list(lines)
        if new_lines and new_lines[-1].strip():
            # append directly; proxy.list is a simple one-rule-per-line file
            pass
        if comment:
            new_lines.append(f"# {comment}")
        new_lines.extend(added)
        path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")

    return added, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add domains/URLs/IPs to config/clash/proxy.list")
    parser.add_argument("targets", nargs="+", help="URLs, domains, keywords, IPs/CIDRs, or full Clash rules")
    parser.add_argument("--file", type=Path, default=default_proxy_list(), help="proxy.list path")
    parser.add_argument("--type", choices=sorted(VALID_RULE_TYPES), help="force Clash rule type")
    parser.add_argument("--comment", help="optional comment inserted before newly added rules")
    parser.add_argument("--dry-run", action="store_true", help="print intended changes without writing")
    args = parser.parse_args(argv)

    try:
        rules = [make_rule(target, args.type) for target in args.targets]
        added, skipped = update_file(args.file, rules, args.comment, args.dry_run)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"DRY RUN: {args.file}")
    else:
        print(f"UPDATED: {args.file}")
    if added:
        print("Added:")
        for rule in added:
            print(f"  {rule}")
    else:
        print("Added: none")
    if skipped:
        print("Skipped existing/duplicate:")
        for rule in skipped:
            print(f"  {rule}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

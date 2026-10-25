# Local infrastructure handoff

For tasks about this user's home network, SSH, OpenWrt/OpenClash, DNS,
VPS, NAS, or cloud infrastructure, first read these local private documents:

1. `inno/network-inventory/AGENTS.md` — privacy and operating boundaries.
2. `inno/network-inventory/README.md` — inventory and evidence index.
3. `inno/network-inventory/CURRENT.md` — current state, recent changes, known gaps.
4. `inno/network-inventory/ACCESS.md` — persistent SSH aliases and access paths.

Read the relevant dated report before acting. Older deployment plans and chat
summaries are historical evidence; verify current runtime before changing it.
Reuse the documented SSH aliases and existing keys. A ControlPersist timeout
does not mean credentials expired. Never request private keys or passwords in chat.

This repository is public. `inno/` and `claude-ops/` are intentionally ignored,
local-only directories. Do not force-add or upload them, private backups,
credentials, or infrastructure coordinates. Keep public documentation sanitized.
If the private inventory is absent on another machine or cloud agent, say so;
do not infer access or recreate secrets from public examples.

After authorized infrastructure changes, update `CURRENT.md`, the applicable
access/asset records, and dated evidence. Record verification time and remaining
uncertainties; do not describe a past test as live monitoring.

Read-only investigation is the default for a diagnosis or inventory request.
Routing, firewall, DNS, service, purchase, and renewal changes require task scope
that authorizes those changes. Do not start recurring monitoring as part of a handoff.

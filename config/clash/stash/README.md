# iPhone Stash：怎么同步到最新

手机上的配置分三层，各自的更新方式不同：

| 层 | 内容 | 来源 | 怎么更新 |
|---|---|---|---|
| 规则 | 直连 / AI / 强制代理 / 大流量 | 本仓库 `config/clash/rule-providers/*.yaml`，以及 blackmatrix7 的公共规则 | **自动**，每 24 小时 |
| 节点 | 各家订阅里的服务器 | 订阅链接（proxy-providers）| **自动**，每 12 小时 |
| 配置骨架 | DNS、策略组、规则顺序 | 本目录 `stash.yaml` 模板 | **手动**重新导入 |

## 1. 规则：改 GitHub 就行

改 `config/clash/rule-providers/` 下的文件并合并到 `master`：

- 家里路由器（OpenClash）和手机 Stash 拉的是**同一份**文件，最迟 24 小时内两边都会生效。
- 想让手机马上生效：在 Stash 里对对应的规则集手动更新；不同版本菜单位置可能不同，找不到的话关掉再重新打开连接也会触发更新。
- 路由器侧由 `config/clash/openclash/peter_github_rules.rb` 在每次加载配置时注入这四个规则集，不需要单独操作。

## 2. 节点：订阅自己会更新

节点来自订阅链接，按 `interval` 自动刷新。服务商换了节点，通常不用做任何事；想立即刷新，在 Stash 里对对应的代理集手动更新即可。

## 3. 配置骨架：变了才需要重新导入

`stash.yaml` 是**公开模板**：订阅链接是 `EQUALVPN_SUB_URL` 占位符，家里自建的住宅出口节点也不写在里面。真实链接和节点只放在 Mac 上 Git 忽略的 `inno/` 目录：

| 文件 | 内容 |
|---|---|
| `inno/auto-update/sources.json` | 订阅链接（与 `openclash/build_config.py` 共用）|
| `inno/auto-update/stash-private-nodes.yaml` | 自建住宅出口节点（可选，从路由器的 provider 文件复制）|

只有模板本身变了（加策略组、改 DNS、调整规则顺序），或自建节点换了，才需要重新生成：

1. 在 Mac 上执行 `python3 config/clash/stash/build_stash.py`，输出 `inno/stash/peter-phone.yaml`（0600）。脚本会检查所有策略组、规则的引用都存在，订阅链接没有残留占位符，不通过就不写文件。
2. 用隔空投送把文件传到手机，**不要经过聊天工具或网盘**——里面有订阅链接和节点密钥。
3. Stash：**设置 → 配置文件**，导入这个文件并选中它（官方文档：<https://stash.wiki/en/get-started>）。
4. 回到首页重新连接，在「住宅节点」组里确认默认选的是自建住宅出口。

## 注意

- 家里的自建出口只配在路由器上，手机配置里没有这个节点。手机连家里 Wi-Fi 时，不在旁路由所在的网段，走的是手机自己的 Stash。
- 2026-10-25 起模板不再内联任何节点。早期写在模板里的自建 VLESS 节点凭据仍留在 Git 历史中，如果那台服务器还在用，应当更换 UUID 或停用。

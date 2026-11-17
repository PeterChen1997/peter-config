# iPhone Stash：怎么同步到最新

当前家庭两组架构使用 `export_home_stash.py`；下面的 EqualVPN 模板和 `build_stash.py` 是旧方案，不用于覆盖新版手机文件。

## 当前方案：从家庭现网导出到自己的 iCloud

生成器只读取得 OpenClash 当前运行和持久配置；两者的节点、组、规则必须一致。私有导出设置在 Git 忽略的 `inno/stash/export-settings.PRIVATE.json`，其中记录 SSH 别名、已验收的住宅路径身份、证书 pin、允许的公共规则 URL 和两个输出路径。不要自动重新生成信任基线。

```sh
inno/auto-update/.audit-venv/bin/python config/clash/stash/export_home_stash.py --sync
```

输出为本机 `inno/stash/peter-phone.yaml`，以及本人 iCloud Drive 的 `Stash/peter-phone.yaml`。只有带 `--sync` 才写 iCloud。定期运行由 Codex 本地自动任务管理，具体任务和验证时间见私有交接；Mac 必须运行且能访问家庭路由器。路由器不可达、主配置切换、引用错误、证书或住宅路径身份变化会停止导出，保留上一份手机文件。失败不会重置 SSH 信任或修改服务器。

- 国内/内网直连。普通及未知请求在 `普通出网` 里手选搬瓦工、RackNerd 或隐藏的 `普通自动`；AI（包括 Gemini）在 `AI出网` 里手选经搬瓦工或经 RackNerd 到同一个静态出口，默认经搬瓦工。
- AI 组是 `select`，两个成员是同一 Webshare 出口分别经两台自有 VPS 拨号；该出口按来源 IP 单授权，切换前必须把授权换到对应 VPS，否则 407，不会回落。手机另导出两个 SOCKS5 变体。普通组的 `普通自动` 只在两台自有 VPS 间按延迟，AI 失败不会改走普通或 DIRECT。
- 新的来源 IP 模式由私有设置中人工审阅的 `ai_path_policy` 显式启用：绑定出口节点和加密上游的精确身份摘要、批准的顺序及默认/Gemini目标。HTTP 出口不导出代理用户名密码，端点、端口、上游身份或路由变化均须重新审阅；不自动生成信任。旧 TLS 住宅策略仍可由旧设置校验，便于审慎回退。
- 所有节点内嵌，家庭本地规则按原顺序展开在同一个 YAML；4 份公共规则按各自间隔更新。机场节点是现网快照，不会单独拉取订阅，新增候选应先在家庭现网验收。
- 转换 Stash 的 `sni`、`server-cert-fingerprint`、节点测速字段；保留 `dialer-proxy` 与适用的证书验证。HTTP 来源 IP 接入本身没有 TLS，不能当作 TLS 证书已验证；网站 HTTPS 仍正常加密。AI 主组非空且不能包含 DIRECT/普通回退。进程匹配规则在 iOS 无效，因此省略。
- 手机有独立 DNS，使用 IPv4；不继承路由器的本地 DNS 地址、监听接口、controller secret、TUN、脚本或管理凭据。不会关闭家庭其他设备的 IPv6。
- 输出原子替换、Mac 文件权限0600；上一版本及回执只留本地。无变化不重写 iCloud 文件。

iPhone 建议使用 Stash 3.6 或以上：在“文件”App → iCloud Drive → Stash，打开 `peter-phone.yaml` 并导入 Stash，选中后重新连接。更新后检查/重新导入同名新版；**Mac 文件已更新不等于 iPhone 当前运行配置已更新**。Stash 自身 iCloud 配置同步与任意 Drive 文件导入是不同入口，不能未验收就承诺自动热加载。第一次要确认 Gemini/普通/AI 请求以及移动网络均可用；Mac 上的兼容核心测试不能替代 iOS 实测。

本人的 iCloud 同步是明确授权的私密设备分发例外。文件包含可用的代理凭据，只给自己的设备；不要创建公开分享链接。SSH 私钥、运维清单、备份、监控密码和管理令牌不在同步范围。公开仓库只保存工具、说明和合成测试数据。

官方参考：[本地文件导入](https://stash.wiki/en/get-started)、[Dialer 链](https://stash.wiki/en/proxy-protocols/dialer-proxy)、[TLS/REALITY 字段](https://stash.wiki/en/proxy-protocols/proxy-types)、[DNS 与 IPv4](https://stash.wiki/en/features/dns-server)、[iOS 不支持进程规则](https://stash.wiki/en/rules/rule-types)。

## 旧方案：EqualVPN 模板

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
| `inno/auto-update/stash-private-nodes.yaml` | 私有节点及 `node-groups` 显式分组；住宅与机房出口分别选择 |

只有模板本身变了（加策略组、改 DNS、调整规则顺序），或自建节点换了，才需要重新生成：

私有节点文件还需填写分组，生成器不会把机房出口自动当成住宅。`node-groups` 的键是模板策略组，值是该组要加入的节点名，例如住宅出口加入 `住宅节点`，机房出口加入 `大流量`。所有私有节点都必须显式分组。住宅组保留已配置的住宅默认；其他组加入新节点时保留原有首选。输出采用0600原子写入，节点端点自动添加DIRECT规则。

1. 在 Mac 上执行 `python3 config/clash/stash/build_stash.py`，输出 `inno/stash/peter-phone-legacy.yaml`（0600），与新版文件区分。脚本会检查所有策略组、规则的引用都存在，订阅链接没有残留占位符，不通过就不写文件。
2. 用隔空投送私密传给自己的手机；本人明确授权的私人 iCloud 文件夹也可使用，里面有订阅链接和节点密钥，不能公开共享。
3. Stash：**设置 → 配置文件**，导入这个文件并选中它（官方文档：<https://stash.wiki/en/get-started>）。
4. 回到首页重新连接，在「住宅节点」组里确认默认选的是自建住宅出口。

## 注意

- 自建节点是否在手机配置中，以本机私有节点文件和生成结果为准；不要把机房IP标成住宅。导出文件只在自己的设备之间私密传输。
- 2026-10-25 起模板不再内联任何节点。早期写在模板里的自建 VLESS 节点凭据仍留在 Git 历史中，如果那台服务器还在用，应当更换 UUID 或停用。
## 普通出口优先与游戏例外

2026-11-17 起，普通外网、未知请求和 Apple/Git 开发服务共用 `普通出网` 的手动选择；导出器要求已审阅的 `ordinary_path_policy`，校验首选为搬瓦工及其加密身份。AI（含 Gemini）有两个批准的出口链（经搬瓦工 / 经 RackNerd），失败时不转普通节点。

家庭 PS5 使用设备专属隐藏游戏组，只含已验证的机场 TCP/UDP 成员。`gaming_path_policy` 固定成员身份、UDP 能力和主机源规则；导出到手机时省略这一设备专属规则与游戏组，其他设备访问 PSN/Sony 仍走普通组，手机保留普通组原有 TCP 限制。原有 AI/证书信任字段不重建。个人文件写入 iCloud 本地目录后，仍需手机重新导入/重载，不能据文件更新就声称手机已经启用。

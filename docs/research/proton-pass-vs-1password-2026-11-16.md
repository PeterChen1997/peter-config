# Proton Pass Plus 与 1Password Individual 深度对比

调研日期为 2026 年 11 月 16 日。价格采用官网显示的美元个人年付。功能判断来自官方文档、公开源码、独立研究与行业标准。未实测设备自动填充、当地网络连通性、客户端实际导出和跨厂 passkey 登录。

在重视**供应商失联后仍能取回自己的数据**的前提下，我会先选 **Proton Pass Plus** 做个人密码库。它能直接导出用独立口令保护的 OpenPGP 数据，按本次核对的美元年付报价，每年少花 12 美元。若更常用 Mac 原生 App、重视 1Password 的额外 Secret Key，或明确要用已支持的 Agent 集成，**1Password Individual** 的体验和隔离方式值得这点差价。两款都能大幅降低从明文存放起步的风险，网站账号实际改密和 Agent 每次调用的约束需要独立处理。

## 一张表看主要取舍

| 问题 | Proton Pass Plus | 1Password Individual |
|---|---|---|
| 人登录时能否基本不看密码 | 可生成、保存和自动填充，支持 passkey 和 TOTP | 同样支持，另有 Mac 通用自动填充和 Quick Access |
| 高风险设备上凭证是否安全 | 已解锁客户端或拥有相同操作权限的 Agent 仍能使用凭证 | 同样受终端和已登录会话边界限制 |
| 已同步旧设备能否离线打开 | 付费含离线模式。Mac 先登录和启用并验证 | 已同步的客户端可离线读。同步与新增设备依赖服务 |
| 新设备能否在厂商不可达时取得旧数据 | PGP 口令 + 异地归档，可离线解密 JSON。附件需完整额外加密 | 异地加密容器 + 已导出的 1PUX，可离线查看 JSON 和附件。桌面导出本身是明文 |
| Passkey 能否跟备份走 | 官方原生 PGP JSON 包含注册在 Proton Pass 的 passkey 字段和密钥材料。跨产品登录需实测 | 桌面 1PUX 不含。iOS / iPadOS 26+、Android 14+ 可用 CXP 在兼容 App 间转移 |
| 普通第三方网站全自动改密 | 无通用个人版功能 | 无通用个人版功能 |
| 定时异地备份 | 界面手动导出，官方 CLI 可生成加密 HTML 归档，定时和异地复制需自行配置 | 桌面手动导出后自行加密和异地保存。官方 CLI 未提供 1PUX 导出命令 |
| Agent 如何使用凭证 | Vault 范围、权限、到期的访问 Token，可通过 CLI 取值 | 部分合作 Agent 提供网站授权，另有 CLI、SDK、Environments MCP |
| 首年／后续年付（USD） | $23.88 / $35.88 | $35.88 / $47.88 |

[Proton 价格](https://proton.me/pass/pricing) · [1Password 价格](https://1password.com/pricing/personal) · [Proton 导出说明](https://proton.me/support/pass-export) · [1Password 导出说明](https://support.1password.com/export/) · [Proton 访问 Token](https://proton.me/support/pass-access-tokens) · [1Password for Agents](https://support.1password.com/1password-for-agents/) · [1Password Environments MCP](https://www.1password.dev/environments/mcp-server)

## 安全模型和可信度

1Password 经典账户登录方式使用账户密码及客户端生成的随机 **128 位 Secret Key**。在只泄露厂商服务器上的加密库、攻击者没有拿到 Secret Key 的情况下，猜到账户密码仍不足以在离线解密。这是 1Password 相比 Proton 默认账户密码模式明确的设计优势。日常解锁已经授权的设备也无需输入 Secret Key。Proton 的安全模型同样由客户端加解密，采用分层的随机库密钥、条目密钥和 AES-GCM，网址和用户名等条目字段也受保护。Proton 的 Pass Extra Password 是单独的登录保护选项，账户的双密码模式是另一种设置。公开资料不足以把 Extra Password 等同于独立生成的 Secret Key。两款产品的安全密钥登录保护和云端密文的抗离线猜测是不同防线。[1Password 安全白皮书](https://1passwordstatic.com/files/security/1password-white-paper.pdf) · [Proton Pass 安全模型](https://proton.me/blog/proton-pass-security-model) · [Proton Pass Extra Password](https://proton.me/support/pass-extra-password) · [Proton 双密码模式](https://proton.me/support/switch-two-password-mode)

Proton AG 运营多个加密产品，Pass 自 2023 年运营，客户端公开源码。Cure53 2023 年公开审计报告可读。Proton 也发布了 Recurity Labs 对 2026 年浏览器扩展、手机、桌面和 CLI 测试的总结，其中所述未发现远程利用或绕过加密限于测试范围。本报告对 2026 审计引用厂商摘要，未单独验证完整第三方附件。1Password 持续公开安全评估入口，也有独立学术审查。ETH Zurich / USI 研究者在服务端能主动操纵协议的假设下发现部分共享及完整性保证的局限，研究也认可其双秘密设计的抗离线猜测优势。该研究未测试 Proton Pass，不能把两者排名。公开审计、有记录的安全更新和恢复演练，比比较两个产品的加密算法名更有决策价值。[Proton 公司](https://proton.me/about) · [Proton Pass 发布](https://proton.me/blog/proton-pass-launch) · [Proton 源码](https://proton.me/community/open-source) · [Cure53 原报告](https://cure53.de/pentest-report_proton-pass.pdf) · [Proton 2026 年审计摘要](https://proton.me/business/blog/proton-pass-audit-2026) · [1Password 安全评估](https://support.1password.com/security-assessments/) · [独立研究](https://zkae.io/) · [1Password 回应](https://1password.com/blog/eth-zurich-zero-knowledge-malicious-server-review)

| 事故 | 迁移后会改善的部分 | 仍可能出事的条件 |
| --- | --- | --- |
| 文档、历史版本或备份被其他人或工具访问 | 停止在普通文件和文档里存明文，换新后旧副本里的密码失效 | 只导入而不让旧值失效。旧会话、API token、恢复码通常也需要单独撤销或重新签发 |
| 某一个网站泄漏密码 | 每站独立随机密码，减少撞库波及的账户 | 泄漏网站自己的账户或已签发会话仍可能失守 |
| 厂商只泄漏加密的服务器存储副本 | 两款均有客户端加密。1Password 随机 Secret Key 加一道独立门槛 | 弱主密码、设备侧材料泄漏或厂商能主动篡改客户端交互时，需要另行分析 |
| 已解锁设备、浏览器或 Agent 运行环境被控制 | 锁库、域名匹配的自动填充、私人与 Agent 授权范围分离，缩小部分暴露面 | 有足够权限的恶意进程仍可能访问已解锁内容或使用浏览器会话 |
| 主邮箱、验证码和密码都只有同一个恢复入口 | 预先保留独立的恢复凭据和目标账户的备用认证 | 厂商不可达、设备遗失或库泄漏时，因素如果都在同一库里，可能同时丢失或泄漏 |

## 离线能打开、忘了密码能找回、厂商停摆后能退出

**只有网络到厂商断了，已有设备还在。** 1Password 已同步的客户端可使用本地数据。Proton 明确给付费订阅提供离线模式，macOS 有官方独立客户端说明。在准备作为后备的设备上，先保留登录状态，再关掉应用、断网并重开，验证能否解锁、检索及查看必要类型的存量凭证。各端可缓存的数据和交互会随版本不同，远端站点本身也须仍可访问。[1Password 同步与离线](https://support.1password.com/sync/) · [Proton macOS 设置](https://proton.me/support/set-up-proton-pass-macos) · [Proton 跨端与离线说明](https://proton.me/blog/proton-pass-all-devices)

**厂商还在线，忘记了账户密码或遗失设备。** Proton 恢复短语同时支持重置账户密码和恢复已加密数据。只以恢复邮件或短信重置密码，若没有数据恢复方式，可能出现账户可以登入但旧数据仍锁住的情况。1Password 的 Emergency Kit 记有登录域名、账号和 Secret Key，可在填入账户密码后作为换设备材料。预先生成的 Recovery Code 是在线恢复的另一条路，需要验证关联邮箱，近期登录可能触发 24 小时恢复限制。两边都应让主邮箱、第二因素与备用恢复材料形成可独立启动的路径。使用同一个 Proton 账户承载邮箱和密码库时，邮箱和密码库共享账户故障范围。[Proton 账户恢复方法](https://proton.me/support/set-account-recovery-methods) · [Proton 恢复短语](https://proton.me/support/recovery-phrase) · [1Password Emergency Kit](https://support.1password.com/emergency-kit/) · [1Password Recovery Code](https://support.1password.com/recovery-codes/)

**所有已登录设备都没了，厂商也无法访问。** 此时能拿到的是独立归档所含的、生成快照那一刻的数据。同步缓存、网站上的账户恢复、厂商承诺的冗余备份都需要自己的前置条件。归档应放在不同失效范围，解密口令另存，测试时模拟从一台未登录的新设备恢复。主邮箱、域名、云服务、设备账号这类能重置多个账户的入口，另注册一把备用硬件安全密钥，或保存该站提供的独立恢复码。[Proton PGP 文件说明](https://proton.me/support/pass-export) · [1Password 1PUX 格式](https://support.1password.com/1pux-format/) · [FIDO passkeys](https://fidoalliance.org/passkeys/)

### Proton Pass 的 PGP 归档覆盖什么

- **归档有两层。** 外层是普通 ZIP，内层 `Proton Pass/data.pgp` 是 PGP 加密 JSON。使用强的独立备份口令，拿到文件和口令可借 GnuPG 等离线读取 JSON，无需登录 Proton。官方指南列出浏览器扩展、网页版和 Windows App 为导出入口，手机 App 不提供文件导出。Mac 可用网页版或浏览器扩展导出。保存普通登录的密码和 TOTP 种子时，均视为高敏感数据。[Proton 导出和回导指南](https://proton.me/support/pass-export) · [Proton 导出实现](https://github.com/ProtonMail/WebClients/blob/main/packages/pass/lib/export/archive.ts#L64-L103)
- **附件会脱离这层 PGP 加密。** 公开源码显示，导出选择包含附件时，文件下载后解密，直接写进同一普通 ZIP 的 `files/`。异地备份只需核心凭证时，取消附件选项并只保存 `data.pgp`。如要备份附件，先把 ZIP 导出到本地加密卷，再独立加密完整 ZIP 并复制密文到异地。[Proton 附件导出实现](https://github.com/ProtonMail/WebClients/blob/main/packages/pass/lib/export/archive.ts#L30-L85) · [Proton 附件下载解密](https://github.com/ProtonMail/WebClients/blob/main/packages/pass/lib/file-attachments/download.ts#L52-L72)
- **原生 PGP 归档包含库内 passkey 数据。** 登录结构包含 `passkeys`，其中有密钥内容。导出保留登录 `content`，回导保留原条目字段。由公开源码可确认设计支持带出这份数据。要用另一产品承接，须实测目标 App 能完整导入并实际登录。Proton 在 2026 秋冬路线图列明计划增加 Credential Exchange。本文以已核验的 PGP 归档能力计入。设备或硬件安全钥匙上注册的另一把 passkey 应独立看待。[Proton 登录和 passkey 数据类型](https://github.com/ProtonMail/WebClients/blob/main/packages/pass/types/protobuf/item-v1.ts#L43-L147) · [Proton 导出字段](https://github.com/ProtonMail/WebClients/blob/main/packages/pass/store/selectors/export.ts#L22-L33) · [Proton 回导实现](https://github.com/ProtonMail/WebClients/blob/main/packages/pass/lib/import/providers/protonpass/protonpass.json.reader.ts#L89-L115) · [Proton 秋冬路线图](https://proton.me/blog/2026-autumn-winter-roadmaps)
- **归档也有权限和在线服务边界。** 导出逻辑选取自己拥有的库。邮件别名即使能找回地址，也需要 Proton/SimpleLogin 活着才能继续转发。重要账户应用独立邮箱或自己能控制域名和 DNS 的地址。使用自有域名时，停服切换仍需自己能管理域名并重建收信线路。[Proton 导出选择范围](https://github.com/ProtonMail/WebClients/blob/main/packages/pass/store/selectors/export.ts#L53-L79) · [Proton 邮件别名与域名](https://proton.me/support/pass-email-alias)

### Proton CLI 的离线归档

官方 CLI 从 2.5.0 开始能生成自包含的 HTML，给定归档口令后可在浏览器断网打开。2.7.0 的实现会将成功下载的附件嵌入同一个数据载荷。显式开启加密后，条目和附件统一用 AES-256-GCM 加密，归档密钥由 Argon2id 派生。文件外层仍有生成时间和条目数量等信息。只备份个别库时能指定范围，下载失败的附件会被略过并发出警告。HTML 只保留 passkey 的展示用元数据，无法据此恢复 passkey 登录，官方也未提供 HTML 回导。要恢复 passkey，保留有密钥材料的 PGP 归档并单独验证，或提前注册备用凭证。[Proton CLI 归档文档](https://protonpass.github.io/pass-cli/commands/export/) · [CLI 发布日志](https://github.com/protonpass/pass-cli/blob/main/CHANGELOG.md) · [2.7.0 归档模型](https://github.com/protonpass/pass-cli/blob/2.7.0/pass/src/domain/archive/model.rs#L117-L161) · [附件处理](https://github.com/protonpass/pass-cli/blob/2.7.0/pass-cli/src/commands/export/fetch.rs#L288-L323) · [加密写入](https://github.com/protonpass/pass-cli/blob/2.7.0/pass-cli/src/commands/export/mod.rs#L155-L184)

这条路线可接本地定时任务，实现日常无人值守的快照生成。备份任务需要独立的运行身份，按所需的库给只读权限，并处理令牌到期、归档口令、失效或缺附件报警及异地上传。归档口令应与密文分开。能读个人库的任务不能放进通用 Agent 环境。1Password CLI 的公开命令未给出对应的 1PUX 导出。[Proton CLI 认证和 PAT 权限](https://protonpass.github.io/pass-cli/get-started/configuration/#personal-access-tokens) · [1Password CLI 命令](https://www.1password.dev/cli/reference) · [1Password 支持论坛的 1PUX CLI 讨论](https://www.1password.community/1password-at-home-31/cli-export-to-1pux-23066)

### 1Password 的桌面备份与手机 passkey 转移

**桌面选 1PUX，保存到自己控制的本地加密容器。** 1PUX 是普通 ZIP，内有 JSON 格式的 `export.data`、导出版本信息和 `files/`，含比 CSV 更多的字段，如 1Password 的 TOTP 字段、文档与附件。它能在普通的解包/JSON 工具查看，也可以导入当前的 1Password 桌面 App。可将导出路径直接指向未同步的本地加密卷，关闭卷后再复制密文到异地。容器解锁需要的东西、离线打开后的临时文件，也会决定实际安全性。[1PUX 格式](https://support.1password.com/1pux-format/) · [1Password 导出](https://support.1password.com/export/) · [1Password 导入](https://support.1password.com/import/)

**Passkey 走独立的流程。** 1Password 明确说明桌面文件不导出 passkey。iOS 和 iPadOS 26+、Android 14+ 的 1Password 可以用 FIDO Credential Exchange 将 passkey 直接复制到支持的 App。这个能力适合仍有可解锁设备时提前迁移。作为事故后的兜底，关键站点可以预先注册一把独立安全密钥，或由另一台设备管理的 passkey，并保存站点恢复码。[1Password 导出](https://support.1password.com/export/) · [FIDO Credential Exchange](https://fidoalliance.org/specifications-credential-exchange-specifications/)

### 换密码之后，旧归档会发生什么

异地备份是时间点快照。快照里的旧密码会在网站改密后失效，旧 API key 会在吊销后失效。保存更久只能延长历史存档。重要账号完成迁移或变更后刷新快照，平时按能接受的丢失窗口安排刷新频率，并保留一份已试过能解密的前一版本。分别演练恢复一个测试登录、TOTP、附件和 passkey。变量多、轮转频繁的服务，恢复预案要能从签发端重新发放凭证。签发端本身的恢复入口适合单独保管。[Proton 导出](https://proton.me/support/pass-export) · [1Password 导出](https://support.1password.com/export/) · [AWS Secrets Manager 轮转](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)

## 能否在 App 里全自动轮转

**普通网站和手机 App 的个人登录。** 两款都能替你生成随机密码、填入页面并保存变更，可以做到平时不主动看密码。银行、邮件等网站的改密流程由站点控制，可能要旧密码、验证码、当前会话或人工确认。改密码要在站点提交成功，在密码库点编辑只改变记录。两款个人版都没有覆盖任意第三方网站的后台改密功能。Proton Pass Monitor 和 1Password Watchtower 属于发现风险和通知，收到泄露、重复使用或弱密码提醒后可到相应网站处理。曾长期以明文保存的重要账号在迁移时更换一次密码，后续按泄露、离职或权限变化等事件处理。NIST 明确建议验证方在存在凭证泄露证据时要求变更，避免无特定原因的强制定期更换。[Proton 自动保存](https://proton.me/support/proton-pass-autosave) · [Proton Pass Monitor](https://proton.me/support/how-to-use-pass-monitor) · [1Password 密码生成与改密](https://support.1password.com/generate-website-password/) · [1Password Watchtower](https://support.1password.com/watchtower/) · [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)

**机器、脚本和 Agent 用的 API token、数据库密码。** 两者的 CLI 可以取值，也能更新密码库里的记录。真正的自动轮转依赖签发方支持创建、验证和吊销，并让使用方切换到新值。有身份联邦的场景，优先让工作负载通过 OIDC 等机制拿短期凭证。必须持有静态凭证时，先挑能原生轮转的类型，配置新版验证、消费者切换、撤旧和失败提醒。AWS Secrets Manager 的轮转可作为支持相应后端时的例子。需测试目标服务适用性。[Proton CLI](https://protonpass.github.io/pass-cli/commands/item/) · [1Password CLI](https://developer.1password.com/docs/cli/) · [GitHub Actions OIDC](https://docs.github.com/en/actions/concepts/security/openid-connect) · [AWS Secrets Manager 轮转](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)

## Agent 登录与实际操作的分界

| 场景 | 1Password Individual | Proton Pass Plus |
| --- | --- | --- |
| 交互式浏览器 Agent 登录 | **1Password for Agents** 在受支持的托管集成中对单个登录项授权，适用于 .com 区域的 Individual 和 Families 账户，由 Agent 托管浏览器内的 1Password 扩展填充。当次授权最多可复用 30 天。当前此集成支持个人库的用户名、密码、TOTP，尚不支持 passkey、SSO 和共享库。另有 Mac 上的 Claude 桌面集成，授权与支持范围独立。 [托管集成列表和限制](https://support.1password.com/1password-for-agents/) · [Claude 桌面集成](https://support.1password.com/1password-claude/) | 查到的公开个人能力是以可撤销的令牌授权 CLI 读取凭证。其公开文档没有承诺同类的托管浏览器逐条审批和直接代填。 [Pass Access Tokens](https://proton.me/support/pass-access-tokens) |
| Codex 等本地开发 Agent | **Environments MCP** 运行于本机，支持对项目环境显式授权，经 MCP 可看到环境和变量名，接口不会返回 secret 值。注入后接收的应用进程可用该值，实际隔离仍取决于进程和 Agent 权限。 [MCP Server](https://www.1password.dev/environments/mcp-server) · [Environments](https://www.1password.dev/environments) | Web UI 可选授权 Vault，期限一小时至一年，可撤销。AI 模式记录凭证读取与 Agent 提供的理由。CLI 可读实际值，因此只能把低权限、专用凭证授权给 Agent。 [Access Tokens 指南](https://proton.me/support/pass-access-tokens) · [CLI 条目读取文档](https://protonpass.github.io/pass-cli/commands/item/) |
| 追查 Agent 高频操作并阻断 | 授权决定的是能否用凭证填登录表单，已有站点会话由目标服务管理。凭据从 1Password 机密计算环境送到扩展后，第三方托管运行时仍需信任。 [托管安全边界](https://support.1password.com/1password-for-agents-security/) | 日志能看到密码库是否被读取。拿到 key 后，Agent 可以再用它发请求，撤销取密令牌不会让已取得的下游 key 失效。 [访问日志及撤销](https://proton.me/support/pass-access-tokens) |

例子是同一个 Agent 读一次 API key，再向目标发 500 次请求。Proton 取密日志只覆盖第一次读取。1Password 的登录批准或变量授权也无法统计这些目标请求。要按调用身份、操作、对象和次数审计，并能对异常速率限流，控制点要放在目标服务或强制经过的 API、MCP 网关。给每个 Agent 单独的身份、短期授权和最小权限，网关保管上游凭证。把资金转移、删除和扩大权限等高风险动作留在目标端批准，并可终止已经签发的会话或凭证。若做产品，可以复用现成密码库和登录授权，优先验证能否跨不同工具建立逐笔操作审计、速率控制和会话止损。更广泛的竞品和试点设计见[此前行业调研](./ai-agent-native-1password-2026-11-16.md)。

## 日常体验和费用

网页和手机的常规登录，两款都提供生成、自动保存、自动填充、passkey 和跨设备同步。Mac 经常用原生应用时，1Password 的 Quick Access 与 Universal Autofill 有实际价值。Proton Plus 已有桌面 Auto-type，需要当前 App 的工作流实际验收，官方秋冬路线图同时把更深的 Mac 系统级自动填充列为后续能力。经常注册网站时，Proton Plus 自带可快速生成的无限邮件别名，少维护一个集成。邮箱转发依赖应计入恢复成本。[1Password Quick Access](https://support.1password.com/quick-access/) · [1Password Universal Autofill](https://support.1password.com/mac-universal-autofill/) · [Proton Auto-type](https://proton.me/support/pass-autotype) · [Proton 路线图](https://proton.me/blog/2026-autumn-winter-roadmaps) · [Proton 邮件别名](https://proton.me/support/pass-email-alias)

| 官网美元年付 | 首年 | 此后每年 | 三年合计 |
|---|---:|---:|---:|
| Proton Pass Plus | $23.88 | $35.88 | $95.64 |
| 1Password Individual | $35.88 | $47.88 | $131.64 |

三年差价为 **36 美元**，未计税、汇率、应用商店渠道、续费变动和自选储存成本。如果一个操作流程每年省约 36 分钟，以时间成本每小时 20 美元这个示例估算，两款的价差就很小。判断日常 ROI 的实测范围可限定在十个常用场景，包括 Mac 原生登录、手机应用、密码变更、passkey 和一次归档恢复。Proton Free 可以先确认同步、浏览器和手机行为，Plus 购买的增量包括离线、集成 TOTP、CLI、附件、无限别名和安全相关选项。1Password Individual 可用 14 天试用作同样验收。正式迁移前应确认两款在常用网络上能正常首次登录和跨设备同步。[Proton 定价及方案](https://proton.me/pass/pricing) · [1Password 定价及试用](https://1password.com/pricing/personal)

## 个人落地顺序

1. 先给主邮箱和密码管理器建立独立的登录恢复路径。单独保管强的主密码、恢复材料和备用第二因素。启用后在另一台个人设备验证解锁。
2. 迁移最能重置其他账户的登录，然后迁移其余项目。原来在明文中存放过的高影响登录，逐一在签发站换新、验证新登录，再处理原明文副本和共享权限。若有可能外泄的 API key，验证新凭证后撤销旧的，按实际影响检查已有会话和日志。
3. 用几个无敏感性的测试项目走一遍跨设备自动填充、离线打开、异地快照解密和恢复。选定厂商后保留一个日常库和经过验证的独立快照，明确附件、passkey、别名、共享库各自由谁负责恢复。
4. 为需要联网操作的 Agent 单独开权限，个人密码库只给人使用。高风险工作走可限定授权范围、可撤销和可记录调用的专用入口。人的本地恢复材料要与 Agent 运行身份隔开。

这一迁移的主要净收益来自撤掉方便复制的明文、为每站换独立凭证、减少日常暴露，并把故障恢复提前演练。涉及已解锁客户端的同权限进程、被劫持的浏览器会话、粘贴与日志外泄、过期归档、错误地关闭最后一个有效恢复入口，实际风险仍取决于运行环境和恢复设计。[FIDO passkeys](https://fidoalliance.org/passkeys/) · [Proton 账户恢复](https://proton.me/support/set-account-recovery-methods) · [1Password Recovery Code](https://support.1password.com/recovery-codes/)

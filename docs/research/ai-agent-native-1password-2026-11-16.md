# Agent 时代的 1Password：运行时风控、凭证轮转与离线恢复

调研日期 2026-11-16（Asia/Shanghai）。依据产品官方文档、发布记录、代码仓库和研究方公开材料。功能结论限定在公开材料描述的路径和版本。本次未部署产品，也未访谈客户或验证市场份额。

## 结论

**把 Agent 的权限和人的保险库拆开。** 如果 Agent 能读取已解锁的保险库、可重用的登录会话或广权限令牌，密钥存放位置的变化不会缩小它的实际权限。即使 Agent 永远看不到密钥，仍可能用一次合法连接连续下载大量数据，或在短时间里重复提交同一笔写操作。建议复用现有保险库，把判断、限额、暂停和审计放在 Agent 控制范围之外的调用路径上，并为人保留独立恢复入口。 [Cloudflare Agent Access Model](https://blog.cloudflare.com/the-agent-access-model/) · [Permit 出站控制](https://docs.permit.io/permit-mcp-gateway/http-egress-proxy/) · [Microsoft 应急访问设计](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access)

**有直接竞品，而且 1Password 本身已经入场。** 1Password for Agents 解决浏览器登录时的凭证隔离与用户授权。Peta 已把凭证库、MCP 网关、执行前审批和工具日志装进同一个产品，Peta Desk 的仓库直接使用“1Password for AI agents”这个定位。Alter 按调用参数授权并托管凭证，Clawvisor 执行任务级授权，Permit.io 同时覆盖 MCP 和直连 HTTP，withHuman 则把跨 Agent 审批、MCP 网关与凭证托管结合。 [Alter](https://docs.alterauth.com/how-it-works/) · [Clawvisor](https://clawvisor.com/faq) · [1Password for Agents](https://support.1password.com/1password-for-agents/) · [Peta Desk](https://github.com/dunialabs/peta-desk) · [Permit MCP Gateway](https://docs.permit.io/permit-mcp-gateway/human-in-the-loop/) · [Permit HTTP 代理](https://docs.permit.io/permit-mcp-gateway/http-egress-proxy/) · [withHuman](https://withhuman.ai/docs) · [Infisical Agent Vault](https://github.com/Infisical/agent-vault)

**值得验证的产品是特定团队的生产操作授权与取证。** 例如，同一个团队用 Codex、Claude Code 和后台 Agent，三者都可以提议发布，但只有授权服务能用限定凭证触发发布。审批人看到具体仓库、环境、待发布版本和 CI 状态，事后能把任务、审批记录与实际部署结果连起来。跨 Agent 审批、按参数检查、签名回执都有先例，Gated 已公布同一方向的 GitHub 私测说明。差异化需要靠一条具体生产流程的保护覆盖、接入成本和下游证据质量来验证。 [withHuman](https://withhuman.ai/docs) · [AWS 参数策略](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-conditions.html) · [AgentAction](https://github.com/dinpd/AgentAction) · [Gated GitHub 私测说明](https://gated.sh/docs)

**用户洞察有调查支持，但无法据此估计未审计的调用比例。** CSA 2026 年对 228 名 IT 和安全专业人员的调查由 Aembit 委托，68% 的受访组织难以清楚区分人工与 Agent 活动，74% 表示 Agent 常获超出任务所需的权限。这测的是受访者对组织能力和行为的判断，分母为调查组织而非工具调用。微软的 Cyber Pulse 也讨论能见度与治理缺口，覆盖的是其第一方遥测和研究范围。 [CSA 研究说明](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-agent-identity-sprawl-authorization-202/) · [微软 Cyber Pulse](https://www.microsoft.com/en-us/security/security-insider/emerging-trends/cyber-pulse-ai-security-report/)

## 1. 产品究竟控制哪一件事

| 控制对象 | 需要回答的问题 | 可验收的证据 |
| --- | --- | --- |
| 身份 | 哪个 Agent 或工作负载在替谁行动？这是第几次运行？ | 可信身份提供方或运行时签发身份，能关联人、Agent、任务与运行 |
| 凭证 | 谁可以使用哪项凭证？凭证是否进过模型、沙盒环境变量或工作目录？ | 代理代发请求或工作负载联邦，记录凭证的签发、注入或兑换，区分上游原始密钥和 Agent 持有的短期令牌 |
| 操作 | 这次具体调用能不能执行？读哪个对象、准备写入什么、发给谁？ | 在执行前检查工具、参数、对象、环境、累计额度及必要审批 |
| 结果 | 这次调用是被拒、已转发、已受理，还是确实改变了目标系统的状态？ | 决策与执行关联到同一请求，再用下游事件、对象 ID 或回读确认结果 |

例如，获得 GitHub 授权只说明某个实体可以访问仓库。某次合并是否获得许可，还涉及目标分支、PR 内容与当前提交 SHA。网关记录请求已转发，或者上游以 HTTP 202 受理异步请求时，还需回查最终状态。在日志里分别保留申请、允许或拒绝、下游受理和最终状态，调查人员才能知道漏查发生在哪个环节。 [GitHub 合并接口](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request) · [Cloudflare Agent Access Model](https://blog.cloudflare.com/the-agent-access-model/) · [Microsoft Agent Governance Toolkit 设计记录](https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/adr/0030-action-bound-approval-protocol.md)

## 2. 最接近的产品

| 产品及可确认的状态 | 能控制什么 | 选型时要追问的边界 |
| --- | --- | --- |
| **1Password for Agents**，2026-10-22 发布，支持文档已列出 Claude Duet、Grok Bot、Instinct、Muse、Town | 识别合作 Agent，在用户设备上批准具体登录请求，由扩展向目标网站提交用户名、密码与一次性验证码 | 这版限 1Password.com 个人或家庭账户的个人登录条目，当前排除 passkey、通过登录提供方登录的条目和共享库。批准可用于重新登录最多 30 天。登录后会话由网站管理。OpenAI ChatGPT Work 和 dots 出现在发布稿的合作名单，当前帮助页未列为接入选项。 [发布稿](https://1password.com/press/2026/october/1password-for-agents-trust-layer-personal-ai-agents) · [接入和权限范围](https://support.1password.com/1password-for-agents/) |
| **1Password Credential Broker**，2026-07-28 进入公开预览，产品页仍标为公开预览 | 动态验证工作负载 OIDC 身份，为 GitHub Actions 和自定义 OIDC 配置交付获准凭证，记录每次交付和命中策略 | 发行事件可追溯，所交付凭证的有效期与发行策略取决于实际凭证类型。公开说明的日志粒度是凭证交付。 [公开预览](https://1password.com/blog/1password-credential-broker-public-preview) · [产品 FAQ](https://1password.com/product/credential-broker) |
| **1Password Privileged Access**，2026-07-28 推出，建立在收购的 Apono 上 | 针对云、数据库和开发基础设施发放限时、最小的访问权限，支持审批、到期回收和访问审计 | 应分别核对权限授予与实际动作的审计记录。此产品的主要控制对象是基础设施访问授权。 [发布稿](https://1password.com/press/2026/july/privileged-access) · [Apono 收购](https://1password.com/press/2026/june/1password-acquires-apono) |
| **Alter Vault**，YC S25，有公开 SDK 和代理文档 | 原始凭证存于 Vault，代理代用。Agent 可持自己的身份，接受用户委托再向子 Agent 缩小范围转授。默认拒绝，可按参数审批，记录经 Alter 的调用 | 代理或审批后由 Alter 后端执行的结果，证据强于由 SDK 客户端回报的直连结果。还应核对接入方式、策略条件及下游适配。 [工作原理](https://docs.alterauth.com/how-it-works/) · [委托](https://docs.alterauth.com/concepts/credentials/) · [审计](https://docs.alterauth.com/concepts/audit-logs/) · [YC 公司页](https://www.ycombinator.com/companies/alter) |
| **Clawvisor**，提供托管与 ELv2 自托管版本 | 人批准目的与任务范围，将凭证使用权、工具、调用预算和有效期绑到任务。代理注入凭证，调用时按目的与风险检查、超出范围请求同意，日志关联参数、任务和用户 | 需要区分规则限制与模型判断。验证模型判定出错时，高风险动作是否仍受目标资源与参数的硬约束。 [FAQ](https://clawvisor.com/faq) · [仓库](https://github.com/clawvisor/clawvisor) · [定价](https://clawvisor.com/pricing) |
| **Peta Core + Desk**，可自托管，源代码可见，社区版免费，最多 30 个访问令牌与 30 个 MCP 服务，Business 一个月许可证 8.99 美元 | Vault 管理和注入 MCP 凭证，为 Agent 或用户发访问令牌，经网关限制 MCP 能力并记录调用。Desk 可展示工具参数，允许用户批准、拒绝、修改后转发 | 范围是经 Peta 的 MCP 路径。Peta 已公开说明审批参数的规范化与哈希绑定，应纳入对照测试。代码使用 ELv2，商业使用以其许可条款为准。 [Core](https://github.com/dunialabs/peta-core) · [Desk](https://github.com/dunialabs/peta-desk) · [审批绑定](https://github.com/dunialabs/peta-core/security) · [定价及许可](https://peta.io/pricing/) |
| **Permit.io MCP Gateway + HTTP Egress Proxy**，有部署文档，MCP 人审为 Enterprise 功能，HTTP 代理需开通 | MCP 工具审批和审计。HTTP 代理扩展到直连 REST、webhook 和第三方 API，支持按身份、域名、路径、方法与信任级别检查、代注入凭证及条件审批 | 要验证沙盒是否强制经代理出站，以及业务参数、重试与下游效果的具体记录。 [MCP 审批](https://docs.permit.io/permit-mcp-gateway/human-in-the-loop/) · [HTTP 代理](https://docs.permit.io/permit-mcp-gateway/http-egress-proxy/) · [HTTP 授权规则](https://docs.permit.io/permit-mcp-gateway/http-egress-proxy/authorization/) |
| **withHuman**，可注册，有免费及付费云套餐，Scale 标价 20 美元/用户/月 | 通过 Agent hooks、MCP 网关和 SDK 接入。网关托管组织或个人的 OAuth/静态凭证并执行逐调用规则，审批绑定具体请求，可限时消费一次。官方列出 Codex、Claude Code、OpenClaw、Hermes 等接入方式 | 对不同接入路径分别验证阻断能力、凭证所在的信任边界和供应商结果的独立确认。可被 Agent 自行改写的本地 hook 只能提供有限保证。 [产品](https://withhuman.ai/) · [网关与凭证](https://withhuman.ai/docs/web-app/mcp-gateway) · [审批协议](https://withhuman.ai/docs/reference/agent-approval-protocol) · [定价](https://withhuman.ai/pricing) |
| **Infisical Agent Vault**，有自托管代码和产品页 | 运行时拿限时会话令牌，代理代填真实凭证。支持 HTTP 方法和路径策略、MCP 工具过滤、代理用户访问及会话日志。产品页还列出 SQL 审计，需按部署核对 | 逐协议核对访问策略、请求记录、部署版本与人工审批能力。关键验证是能否把凭证放在执行环境之外并强制流量经过代理。 [产品](https://infisical.com/platform/agent-vault) · [代码](https://github.com/Infisical/agent-vault) · [代理协议文档](https://github.com/Infisical/agent-vault/blob/main/docs/agents/protocol.mdx) · [套餐能力和计量](https://infisical.com/pricing) |
| **Runlayer 与 Natoma**，企业网关产品，两家都出现在 1Password 的集成名单 | Runlayer 按人员、Agent、客户端、工具和资源等做运行前策略，审计含策略结果与执行结果，受托调用取用户、Agent 和服务端策略交集。Natoma 描述逐工具记录用户、客户端、输入输出与结果并导出 SIEM | Runlayer 网关页面的审批示例为员工申请连接器、管理员批准访问。应单独验证目标场景是否支持按某次调用的参数审批和实际生效验证。 [Runlayer 网关](https://www.runlayer.com/mcp-gateway) · [Runlayer 委托策略](https://www.runlayer.com/identity-policy) · [Natoma 平台](https://natoma.ai/platform) · [1Password 集成公告](https://1password.com/press/2026/mar/1password-unified-access) |

1Password 的个人 Agent 产品与此前的 **1Password for Claude** 走不同入口。7 月发布的 Claude 桌面／Chrome 集成支持符合配置要求的 Mac 用户，包含符合条件的 Business 账户和另外支持的登录方式。Multifactor 则走共享浏览器访问的路线，让用户发限权链接给人或 Agent，并记录通过链接允许或阻止的行为。它的产品页展示了只读示例，具体站点和操作的限制效果需要测试。 [Claude 桌面／Chrome 集成](https://support.1password.com/1password-claude/) · [Multifactor](https://multifactor.com/)

### 身份平台、工具平台与国内云服务

- **Keycard 与 Aembit。** Keycard 在发令牌及供应上游凭证前评估 Cedar 策略，通过其 MCP Gateway 时还检查工具调用。区分 SDK 出具授权与强制经过网关的执行路径。Aembit 面向已有工作负载 IAM 的团队，组合用户与 Agent 身份，向下游注入凭证，网关支持工具可见性和调用控制，并在工作负载事件中保留决策。官方组件页把 MCP Identity Gateway 标为 Available，2026 年 9 月的版本说明了按工具名称匹配的执行控制。 [Keycard 权限模型](https://docs.keycard.ai/guides/why-keycard/) · [Aembit MCP 组件](https://docs.aembit.io/user-guide/deploy-install/about-mcp/) · [Aembit 网关发布记录](https://docs.aembit.io/changelog/area/mcp/2)
- **Auth0 for AI Agents、Okta for AI Agents 与 Entra Agent ID。** Auth0 已正式可用，面向产品开发者提供 Token Vault、用户身份、异步审批与数据授权，应用要接入审批和执行逻辑。Okta 产品面向企业身份治理，Agent SSO 已进核心 SSO 套餐，支持 XAA 连接。9 月正式发布的 Agent Gateway 在远程 MCP 路径逐工具强制身份和策略，并生成统一审计。2026-11-13 公告把第三方 XAA IdP 支持标为 GA，表明“跨身份平台”已有强对手。停用能力须按资源和已发行令牌的撤销范围核实。Entra Agent ID 已 GA，提供 Agent 身份和蓝图、OAuth 与治理构件，管理界面向导中的部分功能仍有 Preview 标签。 [Auth0 GA](https://auth0.com/blog/auth0-for-ai-agents-generally-available/) · [Okta Agent SSO](https://www.okta.com/newsroom/press-releases/okta-brings-first-class-identity-to-ai-agents-with-agent-sso/) · [Okta Agent Gateway GA](https://support.okta.com/help/s/article/what-s-new-in-okta-for-ai-agents?language=en_US) · [Okta 第三方 IdP](https://www.okta.com/newsroom/press-releases/okta-for-ai-agents-now-works-out-of-the-box-with-multiple-third-party-identity-providers/) · [Microsoft 最新状态](https://learn.microsoft.com/entra/agent-id/whats-new-agent-id)
- **Arcade、Composio、Nango 与 Pipedream Connect。** Arcade 按工具声明所需 OAuth scope，托管 provider token，网关提供执行历史及审计。Composio 用 Session 决定用户账户和可见工具，已文档化每工具或规则需要审批的配置与执行日志。Nango 可发临时 Agent Session 绑定已连接账户和工具，Pipedream 代管 OAuth 与代理 API 请求。对已有工具生态的客户，这些产品加上自家审批逻辑便可能覆盖需求，其连接器、OAuth 维护和令牌刷新也是创业团队应计入的替代成本。 [Arcade 开发者文档](https://www.arcade.dev/developers/) · [Arcade 架构](https://docs.arcade.dev/en/operate/deploy/architecture) · [Composio Session 策略](https://docs.composio.dev/docs/configuring-sessions) · [Composio 日志](https://docs.composio.dev/reference/changelog) · [Nango Agent Sessions](https://nango.dev/blog/how-to-give-ai-agents-access-to-user-accounts-without-exposing-oauth-tokens) · [Pipedream Connect](https://pipedream.com/connect)
- **云平台与原生 Agent。** Amazon Bedrock AgentCore 已正式可用，Identity 保管 refresh token，Gateway Policy 可把工具参数纳入 Cedar 规则，Observability 使用 CloudWatch / OpenTelemetry。OpenAI Responses API 默认请求对连接器或 remote MCP 调用的审批，可按工具关闭，调用事件提供参数与结果。Agents SDK 支持可恢复的人审暂停，OpenAI 托管 Agents API 另有自动审查与 trace。Claude Managed Agents 文档仍使用 beta header，Vault 可在沙盒外按目的地主机注入凭证，内置及 MCP 工具有逐工具权限策略和评估事件，自定义工具的执行由应用负责。平台内能力会直接缩小独立产品在单一 Agent 技术栈的付费空间。 [AWS GA](https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/) · [AWS 参数策略](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-conditions.html) · [OpenAI remote MCP](https://developers.openai.com/api/docs/guides/tools-connectors-mcp) · [OpenAI SDK 人审](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals) · [OpenAI 托管审查](https://developers.openai.com/api/docs/guides/agents-api/sessions/approvals) · [Claude Managed Agents](https://platform.claude.com/docs/en/managed-agents/overview) · [Claude 凭证和权限](https://platform.claude.com/docs/en/managed-agents/secure-deployment)
- **中国市场已有同层能力。** 阿里云 Agent Identity 文档展示工具参数金额、来源和网关条件的组合。阿里云 AgentCore 出站 MCP 鉴权在同时有用户和 Agent 身份时要求两者获准，并对拒绝记审计。百炼支持主 Agent 的逐工具审批，官方 API 文档明确子 Agent 不支持该审批。腾讯云 AI Agent 安全网关能对接 MCP、API 和云资源，做凭据托管、访问授权与审计。 [阿里云 Agent Identity](https://help.aliyun.com/zh/agentidentity/agent-permissions-overview) · [阿里云 AgentCore](https://help.aliyun.com/zh/agentcore/access-authentication-to-outbound-mcp-server-based-on-agent-inbound) · [百炼审批边界](https://help.aliyun.com/zh/model-studio/agent-create) · [腾讯云资源接入](https://cloud.tencent.com/document/product/1627/131323)

### 原生审批与结果取证

**客户现有审批。** 工程团队已有 GitHub rulesets 和部署环境保护，业务客户可能已有 Workato 的 Business Approvals。客户只用一套目标系统时，原生审批通常更贴近业务对象。独立方案可以在两种 Agent、一个既有审批入口和跨两个目标系统的一条工作流上验证价值。自托管 OpenClaw 已可将命令审批绑定到具体执行计划和相关本地文件内容，客户也可能采用宿主的审批加下游原生保护。 [GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets) · [GitHub 部署环境规则](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments) · [Workato Business Approvals](https://docs.workato.com/en/agentic/agent-studio/business-approvals.html) · [OpenClaw 执行策略](https://docs.openclaw.ai/start/why-openclaw/policy-as-code)

**新项目也在把授权和结果连起来。** AgentAction 公布了退款控制样例，绑定审批参数及范围、幂等键和服务方结果，提供签名回执。公开的 Workato 示例使用合成退款，目前只能用于验证实现思路和竞争方向。Alter 明确区分上游结果不明与可重试错误。Gated 的 GitHub 私测用 passkey 检查审批、由服务端执行，并通过 GitHub 回读确认结果，已验证的动作是从一个确定提交创建指定分支，合并与上线尚未纳入它已验证的范围。withHuman 区分网关转发事件与下游业务是否执行，微软 Agent Governance Toolkit 的设计记录也提出把审批绑定到动作、策略版本及有效期。 [AgentAction 仓库与示例](https://github.com/dinpd/AgentAction) · [Alter 错误处理](https://docs.alterauth.com/reference/errors/) · [Gated 私测范围](https://gated.sh/docs) · [withHuman 网关日志](https://withhuman.ai/docs/web-app/mcp-gateway) · [withHuman 审计字段](https://withhuman.ai/docs/web-app/audit-event-types) · [Microsoft 动作绑定设计](https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/adr/0030-action-bound-approval-protocol.md)

## 3. 标准为什么会压低基础功能的差异化

- **MCP 企业托管授权扩展 EMA 已稳定。** 基于 Cross App Access 的扩展由企业 IdP 集中配置客户端到 MCP 服务的连接，减少逐个 SaaS 登录与授权。接入后仍要定义某个调用能改哪些对象、哪些写入须审批、哪些结果要回读。 [MCP EMA 发布说明](https://blog.modelcontextprotocol.io/posts/enterprise-managed-auth/) · [Cloudflare 对 MCP 与工具策略边界的说明](https://blog.cloudflare.com/the-agent-access-model/)
- **OAuth Token Exchange 可表达受托执行。** RFC 8693 的 subject 与 actor 可以把“谁的权限”和“谁在执行”放在一起。用嵌套 actor 可保留委托历史，RFC 中的历史 actor 仅用于信息记录。撤销传播和目标服务是否能使用这些身份字段依赖具体实现。RFC 9396 提供结构化授权字段，RFC 9449 支持将令牌绑定到客户端密钥。在业务层仍需把批准绑定到规范化请求及具体资源。 [RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693) · [RFC 9396](https://datatracker.ietf.org/doc/html/rfc9396) · [RFC 9449](https://datatracker.ietf.org/doc/html/rfc9449)
- **任务级授权已有公开参考架构。** Cloudflare 的 Agent Access Model 把短期任务凭证、任务权限、harness、网络强制执行以及日志关联放在一起。这是参考架构。2026 年 10 月 IETF 上的 AI Agent Credential Delegation Protocol 仍是 Internet-Draft，不能当作已获互操作保障的正式标准。 [Cloudflare AAM](https://blog.cloudflare.com/the-agent-access-model/) · [IETF 草案](https://datatracker.ietf.org/doc/draft-sweeney-wimse-credential-delegation/01/)

## 4. Bitwarden 已经可以复用的能力

| 能力 | Bitwarden 已支持 | 与 Agent 运行时治理的关系 |
| --- | --- | --- |
| 密码、Passkey、TOTP、组织共享与自托管 | 官方服务器支持标准部署、Lite 和离线／隔离环境部署。已解锁客户端在服务器不可达时可离线只读。支持密码保护的加密 JSON 导出及服务器备份。购买的功能可能需要许可证。 [部署选择](https://bitwarden.com/help/self-host-bitwarden/) · [隔离网络部署](https://bitwarden.com/help/install-and-deploy-offline/) · [离线使用](https://bitwarden.com/help/using-bitwarden-offline/) · [数据导出](https://bitwarden.com/help/export-your-data/) · [服务器备份](https://bitwarden.com/help/backup-on-premise/) | 人的保险库、同步、基础恢复能力可直接采购或部署。条目导出覆盖范围和附件应单独核对，服务器备份也要做恢复演练。 |
| 机器凭证和审计 | Secrets Manager 支持按项目或秘密对机器账户授权、有到期选项的访问令牌、CLI/SDK，以及组织事件中的密钥访问记录。Enterprise 有官方自托管路径，官方文档排除 Unified/Lite 路径。 [Secrets Manager 组织与部署](https://bitwarden.com/help/manage-your-secrets-org/) · [访问令牌](https://bitwarden.com/help/access-tokens/) · [事件记录](https://bitwarden.com/help/event-logs/) | 一次取出 API key 后，可用同一 key 调用目标系统多次。Bitwarden 的密钥访问事件无法替代目标 API 调用及结果记录。不要给拥有 shell 的 Agent 装载个人保险库会话或广权限机器令牌。 |
| MCP 与 Agent 授权 | 官方 Bitwarden MCP 是本地保险库及组织管理工具，README 明确说明能读取并在 AI 响应中暴露密码等内容。另一项目 Agent Access 是早期预览协议和 SDK，支持人批准选定凭证，经加密通道发送并注入指定进程，避免把整库授予远端。 [MCP README](https://github.com/bitwarden/mcp-server) · [Agent Access 代码及预览边界](https://github.com/bitwarden/agent-access) · [发布说明](https://bitwarden.com/blog/introducing-agent-access-sdk/) | 注入子进程时凭证无需经过聊天或标准输出。拥有读取该子进程或其环境权限的 Agent 仍可能接触明文。SDK 另有直接返回凭证的接口。隔离的执行器和逐次调用策略应独立验证。 |
| 凭证健康检查、审批和轮转 | Access Intelligence 报告弱、复用或已暴露密码，并发整改通知。Privileged Controls 在 2026-11-04 官方更新中仍为私有预览，支持凭证租借、审批、访问日志和按租借结束或计划轮转，预览原生支持 Microsoft Entra ID，并提供服务器凭证的自定义脚本路径。 [Access Intelligence](https://bitwarden.com/help/access-intelligence/) · [Privileged Controls](https://bitwarden.com/blog/bitwarden-privileged-controls-secure-your-most-sensitive-accounts-in-minutes/) · [11 月更新](https://bitwarden.com/blog/bitwarden-2026-product-roundup/) | 把弱密码和共享账号管理留给已有产品。自动轮转要按目标系统、部署方式和功能开放状态验证。凭证租借审批与某次具体生产写入的审批是两个事件。 |

**加密与运营成熟度应分别比较。** Bitwarden 本身是持续维护的商业产品，公开源代码和安全测试报告。官方白皮书描述 AES-256-CBC 加 HMAC 及 PBKDF2 或可选 Argon2id，特定加密模块取得 FIPS 140-3 验证。1Password 默认密码账户额外使用 Secret Key 与账户密码派生保护密钥。当攻击者只取得服务端保存的加密数据且拿不到设备侧 Secret Key 时，这项设计为 1Password 提供了具体优势。需要进一步考虑终端接管、已经解锁的进程和主动恶意服务端。2026 年 ETH Zurich／USI 研究和厂商回复都显示，协议、客户端实现及持续更新同样重要。模块验证和算法名称都无法为任意自托管栈背书。 [Bitwarden 白皮书](https://bitwarden.com/help/bitwarden-security-white-paper/) · [公开审计](https://bitwarden.com/help/is-bitwarden-audited/) · [NIST 模块证书](https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/5507) · [1Password Secret Key](https://support.1password.com/understanding-account-key/) · [研究原文](https://www.usenix.org/conference/usenixsecurity26/presentation/scarlata) · [Bitwarden 修复说明](https://bitwarden.com/blog/security-through-transparency-eth-zurich-audits-bitwarden-cryptography/) · [1Password 对同一研究的回应](https://1password.com/blog/eth-zurich-zero-knowledge-malicious-server-review/)

**自托管转移故障和运维责任。** Bitwarden 可去掉保险库读写对公共服务的日常依赖，实际可用性仍取决于本地机器、磁盘、电源、内网 DNS、TLS、认证、更新和能恢复的备份。若密码库、Agent、备份解锁密钥和审计都在同一台主机，单次主机接管或故障会影响全部。Vaultwarden 是采用 Bitwarden 兼容协议的独立社区服务器，版本、补丁、企业功能与审计范围按各自项目核对。 [Bitwarden 自托管常见问题](https://bitwarden.com/help/hosting-faqs/) · [Bitwarden 更新指南](https://bitwarden.com/help/updating-on-premise/) · [Vaultwarden 项目](https://github.com/dani-garcia/vaultwarden)

## 5. 从调用日志到能止损的运行时风控

有两种不同的覆盖。**可强制的调用**必须经过受控执行器或网关，由网关持有上游凭证并在放行前检查。**仅可观测的调用**可以由 Agent 框架、出站遥测或 SaaS 下游事件补齐线索。SSH、浏览器既有登录会话、本机 CLI 和直接 API 出站各有不同拦截点。只设代理环境变量或安装本地 hook，无法约束拥有同设备高权限、能改配置或还能使用其他身份的 Agent。第一版应在界面列出已强制、仅观测、未知的路径，并以目标系统可核对事件作为覆盖率分母。 [Cloudflare 执行模型](https://blog.cloudflare.com/the-agent-access-model/) · [withHuman 对直连路径的说明](https://withhuman.ai/docs/web-app/mcp-gateway) · [Permit 出站代理](https://docs.permit.io/permit-mcp-gateway/http-egress-proxy/)

| 风险信号 | 对应控制 | 已有实现可对标 |
| --- | --- | --- |
| 短时间重复调用、大量重试或超出任务额度 | 按租户、Agent、任务和目标聚合速率与并发，另计写入次数、不同对象数或导出数据量。预算超限自动拒绝或冷却，高影响写入用幂等标识防止重复执行。单 IP 限速只能应对部分场景。 | Alter 支持每 Agent 的配额、时间窗和按参数规则。Permit HTTP 代理按 Agent 的目的主机及域限制速率。 [Alter 策略](https://docs.alterauth.com/reference/cli/commands/policy/) · [Permit 速率控制](https://docs.permit.io/permit-mcp-gateway/http-egress-proxy/) |
| 每个请求单独合法，组合起来异常 | 以同类 Agent 的任务、时间和资源范围做基线。在短期没有足够历史时先用确定性规则，例如越出任务范围、扫描过多不同对象、重复失败、罕见目的地或读后紧跟批量外发。模型或统计异常先告警或升级审批，硬边界直接阻断。 | Runlayer Tool Call/Intent Guard 对接入路径的工具请求做运行时检查。Permit Session Monitoring 记录调用模式，须联系厂商确认开放范围。Zenity 宣传对受支持的 Agent 活动序列检测和阻断。Google Agent Anomaly Detection 仍是 Preview，分析接入的 trace 和工具历史，并非每条调用都经过它做同步授权。 [Runlayer](https://www.runlayer.com/guard) · [Permit](https://docs.permit.io/permit-mcp-gateway/advanced-features/) · [Zenity](https://zenity.io/platform/ai-detection-and-response) · [Google 文档](https://docs.cloud.google.com/gemini-enterprise-agent-platform/agent-anomalies-overview) |
| 高置信异常或疑似泄露 | 暂停单个 Agent 或连接，撤销当前会话／任务授权。若原始凭证疑似外泄，在目标系统撤销或轮转并确认生效。记录暂停、撤销及未完成在途操作，供人工恢复。 | Alter 支持暂停和撤销，Entra Agent ID Protection 支持基于身份风险阻止相关访问。覆盖程度由仍存活的令牌、入口和目标系统是否重新鉴权决定。 [Alter 暂停管理](https://docs.alterauth.com/reference/cli/commands/agents/) · [Entra 风险响应](https://learn.microsoft.com/entra/agent-id/manage-agent-identities-organization) |

例子是“排查一个客户的账单问题”。账单查询本来允许，Agent 在一分钟查询数百个不同客户则先压住该任务，保留其访问记录，并让其他任务继续。日志只保存定位所需的调用与策略元数据、脱敏后的对象标识和结果状态，调用内容按需留存。对于高风险写入，审计应能关联原始任务、策略、执行前审批、网关实际发出的请求和下游结果；遇到日志后端故障，应保留本地持久化记录或暂停需要完整审计的写动作。 [OWASP Agentic Applications 安全指南](https://genai.owasp.org/download/49059/) · [Alter 审计元数据](https://docs.alterauth.com/concepts/audit-logs/) · [withHuman 网关事件范围](https://withhuman.ai/docs/web-app/audit-event-types)

## 6. 轮转和网络故障如何避免永久锁死

**1Password 的短时离线、设备或账户丢失、上游凭证已经换代是三件事。** 对已同步且仍能解锁的客户端，官方确认本地可以访问已同步内容。企业 SSO 离线解锁受管理员配置、设备生物认证和期限限制。Emergency Kit 保存登录所需的账户资料，帮助重新登录 1Password；保险库内容要依赖已同步副本、独立备份或独立的目标系统恢复凭证。自动化若依赖在线 Service Account 或 Credential Broker，应单独模拟断网，不能沿用个人客户端的离线承诺。1Password Connect 有本地缓存，首次拉取、没有有效副本的冷启动和同步后新版本应分别测试。 [1Password 同步](https://support.1password.com/sync/) · [SSO 离线边界](https://support.1password.com/sso-security/) · [Emergency Kit](https://support.1password.com/emergency-kit/) · [Connect 缓存](https://www.1password.dev/connect) · [自动化接入比较](https://www.1password.dev/service-accounts)

| 故障 | 允许继续的路径 | 停止或恢复的条件 |
| --- | --- | --- |
| 外部 Vault 或管理服务不可达，客户侧执行器仍在线 | 预先登记的低风险操作可在很短的期限内使用仍有效的现有授权和隔离缓存，继续记本地审计。 | 新授权、提权和敏感写入暂停。无法看到最新撤销状态时，缓存的可用窗口就是额外风险上限，可按资源缩短或设为零。执行器自身无法审计或已失效时暂停受保护操作。 |
| 上游已经换新，保险库或执行器仍持旧版本 | 支持双凭证的目标先创建并保存备用版本，从正常执行路径验证新凭证，再切换；确认必要消费者和恢复路径已就绪后，撤销旧版本。 | 切换结果不明时读取目标状态并告警。只有旧凭证仍有效且无泄漏嫌疑时才可以回退。支持单凭证的目标需要明确停机窗口或独立恢复账号。 |
| 保险库账号、设备、网络或日常身份提供方失效 | 人在目标系统使用预先登记的备用硬件密钥、恢复码或应急管理员。保留独立加密备份和恢复材料，放在不同设备或地点，确保可以在日常系统离线时解锁。 | 应急身份与日常 Agent 分开，验证它不依赖同一个 Vault、IdP 或联网路径。演练要实际登录并确认权限，而不是只检查备份文件存在。使用后留审计并按情况更新凭证。 |

优先使用目标系统原生的限时凭证。长期 API key 或密码仍需要安排轮转。把新版本生成、存储、在线验证、生效和撤销做成可检查的状态，区分正常轮转与泄露处置，轮转失败时保留并标记可用版本。AWS Secrets Manager 和 Infisical 已有分阶段或双用户轮转，HashiCorp Vault 有租约和受限缓存，Delinea 已有 PAM 的恢复、离线缓存及应急访问做法。产品应优先适配原生功能并验证执行结果。1Password 8 桌面端的 1PUX 和 CSV 是明文导出。应急备份应独立加密，并分别检查 Passkey、附件和二次验证恢复材料。 [AWS 分阶段轮转](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotate-secrets_lambda-functions.html) · [Infisical 双阶段轮转](https://infisical.com/platform/secrets-management) · [Vault Proxy 缓存](https://developer.hashicorp.com/vault/docs/agent-and-proxy/proxy/caching) · [Delinea 应急恢复](https://docs.delinea.com/online-help/secret-server/backup-and-disaster-recovery/index.htm) · [1Password 导出边界](https://support.1password.com/export/)

## 7. 产品路线与试点

| 路线 | 谁现在最强 | 创业判断 |
| --- | --- | --- |
| 给个人浏览器 Agent 安全登录 | 1Password、Multifactor | 优先级低。网站掌握登录后会话，网页按钮缺少稳定的交易语义，靠浏览器扩展覆盖全部网站的成本高。 |
| 通用 Agent 密钥库、MCP 网关与工具审计 | Peta、Permit.io、Alter、Runlayer、Natoma、Infisical，加上云厂商 | 单独做基础功能容易被免费自托管或平台套件替代。若手里已有 Agent 分发渠道，可检验“默认带保护”的产品体验。 |
| 一类工作流的跨 Agent 实时风控与恢复 | Alter、Permit、withHuman 和 Clawvisor 做调用控制，Runlayer、Zenity 和 Google 做行为检测，PAM 和 Secrets Manager 覆盖轮转与恢复的部分场景 | **优先验证集成后的价值。** 在一条已有真实流量的生产流程里验证调用覆盖、异常止损、结果取证和故障恢复。 |

上表是基于已核实功能的创业判断。对第一类买家，竞争焦点是密码库信任和浏览器分发。对后两类买家，竞争焦点是产品能否在客户的身份体系和执行边界里真正获得拦截权限。采购、运维和安全团队要承担接入成本，价值来自放开原先禁止的动作、减少人为代操作、缩短事故定位。需求访谈要让客户展示一次现有的生产写操作和相应审批记录。 [1Password 合作分发](https://1password.com/press/2026/october/1password-for-agents-trust-layer-personal-ai-agents) · [Peta 定价](https://peta.io/pricing/) · [withHuman 定价](https://withhuman.ai/pricing) · [AWS Gateway 策略](https://aws.amazon.com/bedrock/agentcore/faqs/)

### 复用现有组件，选一条流程验收

第一版可以让人继续用 1Password 或官方 Bitwarden，机器凭证走既有的 Vault、云原生短期身份或目标端 OAuth。复用 Permit、Alter 等既有执行路径时，先验证是否能按任务归因、及时停用和保留客户侧必要审计。产品工作的优先顺序是将调用与业务对象关联，区分强制覆盖与观测覆盖，再把一个高价值异常模式和一条断网恢复路径做成可演练的流程。已有套件如果能以相近代价覆盖，即可用现成配置验证客户需求。 [Permit HTTP 出站代理](https://docs.permit.io/permit-mcp-gateway/http-egress-proxy/) · [Alter 策略规则](https://docs.alterauth.com/reference/cli/commands/policy/) · [Vault 动态凭证租约](https://developer.hashicorp.com/vault/docs/concepts/lease)

### 试点示例：GitHub 到生产部署

**首批对象**是同时使用两种以上开发 Agent、已让 Agent 写 PR、仍由人手动触发受保护部署的工程团队。买家假设为 Platform Engineering 或 DevSecOps 负责人，使用者是研发和当值运维。若设计伙伴更容易触达客服运营，也可用退款流程检验同一假设。Intercom Fin 已支持检查退款条件并调用外部审批或业务流程，客服切入需要让客户比较现有产品能覆盖的流程。 [Intercom Fin Procedures](https://www.intercom.com/help/en/articles/10257113-how-to-set-up-fin-tasks)

这里选择 GitHub 到部署，因为已有可核验的 PR SHA、CI 结果、部署环境与 webhook，能把审批内容与结果对应起来。GitHub 本身已有这些原语，试点需要计入它作为竞争对照。 [GitHub 合并接口](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request) · [GitHub 部署事件](https://docs.github.com/en/webhooks/webhook-events-and-payloads#deployment_status) · [GitHub App 权限](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app)

1. **接入两个客户端和两个动作。** 例如 Codex 与 Claude Code，共用同一 MCP 入口。Agent 可以读取 PR 或准备变更。受保护的动作只做“合并已验证版本”和“部署已验证构建”，两个动作均通过同一执行服务，试点按已有流程保留独立的生产部署审批。使用 GitHub App 或已有 Vault 提供服务端凭证；客户原有分支和部署保护仍由目标系统执行。 [GitHub 合并接口](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request) · [GitHub 部署环境规则](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
2. **让审批内容来自可信数据。** 展示组织、仓库、PR、精确 SHA、目标环境、检查结果、执行账户和发起人。Agent 的任务说明可供人参考。从可信 API 重新取当前版本，将批准绑定到同一主体、目标租户、动作与参数、有效期及执行次数。提交变化、审批过期或策略命中禁止条件时，交回待核准状态。 [Microsoft 动作绑定设计](https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/adr/0030-action-bound-approval-protocol.md) · [GitHub 合并 SHA 字段](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)
3. **执行时检查凭证与网络边界。** 保护范围内的 Agent 环境不能继续持有等价的长效凭证，也不能从另一路径取得同样的写权限。工具调用前检查，直接 HTTP 通道则在受控执行环境限制。如果客户的某个本地 Agent 仍有其个人 GitHub token，界面只能把那部分表述为观测覆盖或待迁移。 [Cloudflare 执行与出站边界](https://blog.cloudflare.com/the-agent-access-model/) · [Permit 出站代理](https://docs.permit.io/permit-mcp-gateway/http-egress-proxy/)
4. **拿下游证据收尾。** 每次动作关联发起人、Agent/运行、规范化参数摘要、策略版本、审批人、执行身份、请求 ID 与目标对象 ID。部署请求受理后等待来自目标平台的确认，超时标记“结果待核实”，用稳定的动作标识关联重试与回查。审计先保存必要的结构化证据，并限制原始请求、提示词和敏感字段的保留。 [GitHub 部署事件](https://docs.github.com/en/webhooks/webhook-events-and-payloads#deployment_status) · [AgentAction](https://github.com/dinpd/AgentAction) · [Cloudflare 活动记录模型](https://blog.cloudflare.com/the-agent-access-model/)

### 用同一条工作流跑竞品和付费验证

| 验收场景 | 应拿到的结果 |
| --- | --- |
| 正常合并与发布 | 可从目标系统事件回到发起任务、批准的 SHA、审批人及最终发布版本 |
| 批准之后出现新提交、目标环境变化或审批超时 | 旧批准无法使用，目标系统状态未变化，有拒绝原因 |
| 调用发出但响应超时，上游重复提交 | 展示处理中或结果待核实，只有一个实际写入，最终能关联或解释结果 |
| Agent 直接尝试调用目标 REST API | 受控环境下该写入失败，报告指出是由网络边界还是目标服务权限阻断 |
| 跨租户、审批人员离职、服务依赖故障 | 对需要审批的动作维持拒绝或待审批状态，审计区分权限撤销、下游异常与审批超时 |
| Agent 在合理接口上短时重复请求，或在一个任务中触及异常多的资源 | 命中确定性预算后限流或暂停，在审计中保留规则、阈值和受影响范围，其他 Agent 或任务继续 |
| 断开外部 Vault 或审计服务，在目标端模拟轮转 | 低风险动作按有效期限和存储条件降级，高风险写入保持受控，轮转不误撤销唯一可用凭证，人能用独立入口恢复 |

先用 **Permit 或 Alter 配合 GitHub 原生流程**跑这张表，需要跨 Agent 审批时再对照 withHuman 或 Peta。参考 Gated 的分支创建回读，把接入时间、受控调用占比、异常到暂停的时间、误拦截比例、正常作业的人审次数和断网恢复时间记下来。第一个销售验证可访谈 10 家团队，争取 3 家愿意提供真实流程、至少 2 家同意带明确预算的试点。阈值与客户约定。若现有组合可以在同样成本下通过验收，优先采购或集成。

### 定价、需求信号与竞争壁垒假设

Peta 按版本与容量卖许可证，withHuman 按审批用户收费，Clawvisor 按保护调用计量，Infisical 按注入凭证的请求计量。这表明同一个需求会同时遇到免费自托管、席位订阅和基础设施用量三类报价。生产场景可测试按受保护工作流或团队收订阅费。报价时看客户愿意为哪项结果付钱，例如少一次人工代操作、少一份自维护密钥或审计取证从多系统变成可复现的查询。公开定价无法推导付费意愿。 [Peta](https://peta.io/pricing/) · [withHuman](https://withhuman.ai/pricing) · [Clawvisor](https://clawvisor.com/pricing) · [Infisical](https://infisical.com/pricing)

Runlayer 2026 年 6 月宣布完成 3,000 万美元 A 轮，披露已签 AppLovin、Gusto、Decagon、Opendoor 等客户。1Password 同期收购特权访问厂商 Apono。这是供给方投入和已经出现企业采购的信号，公开发布未提供成交规模、单个功能带来的收入或本报告所提切入点的付费意愿。 [Runlayer 融资及客户披露](https://www.runlayer.com/blog/series-A-30m-fundraise-felicis-khosla) · [1Password 收购公告](https://1password.com/press/2026/june/1password-acquires-apono)

长期壁垒的候选是复用性强的业务语义和证据适配，包括跨 GitHub、部署平台、企业审批与客户 SIEM 的可验证事件关联，以及从观察到强制执行的低摩擦迁移。若每家客户都要写一套私有代理和审批逻辑，市场可能更适合交付项目。若一组模板能重复接入第二、第三个客户，再扩展到回滚、生产权限、客服退款等同类型动作。

对首批团队的产品承诺可以写成 **让 Agent 在明确权限内执行生产任务，异常时自动停住，事后能核对结果，依赖故障时人仍能接管。**

## 8. 迁移后如何证明安全收益

迁移的安全收益取决于原来哪条路径会泄露或误用凭证，以及迁移后它是否还有效。以下对照适用于同一批账号和自动化，不能从迁移条目数量推导总体风险降幅。 [GitHub 凭证泄漏处置](https://docs.github.com/en/code-security/tutorials/remediate-leaked-secrets/remediating-a-leaked-secret) · [Cloudflare Agent Access Model](https://blog.cloudflare.com/the-agent-access-model/)

| 迁移做到哪一步 | 实际改善 | 仍有的风险 |
| --- | --- | --- |
| 从聊天、源码和 `.env` 搬到保险库，停用可能暴露的原凭证 | 减少平时明文暴露，原来的副本失去使用价值 | 已被复制的数据无法收回。上游独立发行的浏览器会话、刷新令牌或第三方授权可能仍有效。 |
| 从 1Password 换到自托管 Bitwarden，账号、设备和授权维持原状 | 可以降低对 1Password 公网服务的依赖 | Agent 能使用的权限基本相同。自托管增加需要自行验证的补丁、内网认证、备份和恢复路径。 |
| 为 Agent 使用独立身份，隔离现有个人会话，限定业务操作并收回等价直连权限 | 保护范围内的调用能在执行前拒绝，按任务限制用量，事后关联操作者、决策与结果 | 仍有权限内误操作、业务策略错误、已放行的在途请求、网关或目标系统失陷。Agent 如果能改生产自动化、重设密钥或变更权限，也可能间接扩大实际能力。 |

以 GitHub 为例。如果 Agent 仍能使用人类的已登录浏览器和 CLI，原样迁移密码库不会改变它的仓库权限。如果受控 Agent 只能通过自己的身份读取指定仓库、创建 PR，合并需匹配已批准的提交，再由受保护执行器调用，安全收益可以落到可复核的行为差异上。GitHub 原有的分支和部署保护仍负责目标端的强制执行。 [GitHub 仓库规则](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets) · [目标应用会话撤销](https://learn.microsoft.com/en-us/entra/identity/users/users-revoke-access) · [withHuman 的直连边界](https://withhuman.ai/docs/web-app/mcp-gateway)

核心验收是用测试资源做迁移前后对照。验证曾散落的旧凭证和应退役的会话在目标端已经失效，从 Agent 的正常入口确认越权操作和等价直连被阻止，重复调用能按任务暂停并留下记录。再断开 Vault 验证低风险降级和人工恢复，同时核查正常调用没有中断。为了区分一次成功验证和长期保障，应记录测试资源、被覆盖的入口、凭证撤销生效时间与恢复时间。 [GitHub 凭证撤销](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) · [Permit 代理限制](https://docs.permit.io/permit-mcp-gateway/http-egress-proxy/) · [Microsoft 应急访问](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access)

## 9. 个人方案与投入产出

如果独立异地恢复意味着**原服务完全不可达时，也能在一台新设备用通用工具离线读取备份**，个人主库首选 **Proton Pass Plus + 原生 PGP 加密导出**。如果接受恢复到另一 Bitwarden 账户或自托管实例，**Bitwarden 官方云 Premium + 密码保护的加密 JSON 异地备份**成本更低，Free 已具备基础密码管理能力。两种路线均用独立的机器身份承载 Agent 权限，机器凭证由目标系统签发或轮转，按调用类型接入原生授权或有审计的网关。 [Proton Pass 加密导出](https://proton.me/support/pass-export) · [Bitwarden 加密导出](https://bitwarden.com/help/encrypted-export/) · [Bitwarden 个人方案](https://bitwarden.com/products/personal/)

| 方案 | 当前报价与适用条件 | 独立恢复和自动化边界 |
| --- | --- | --- |
| **Proton Pass Plus** | 官网美元年付首年 $23.88，页面列示续费 $35.88/年。支持浏览器和手机自动填充，付费版 macOS 应用支持离线查看。 | 原生 ZIP 中的 PGP 加密 JSON 可用通用 OpenPGP 工具离线解密，无需登录 Proton。勾选的附件以解密后的数据写入外层 ZIP，包含附件时将整个 ZIP 再加密后才异地保存。关键 passkey 保留独立恢复途径。Agent 访问令牌支持限定范围、期限和访问日志。CLI 能读取凭证值，因此只给专用低权限凭证，敏感调用用单独的代执行网关。 [定价](https://proton.me/pass/pricing) · [离线访问](https://proton.me/support/set-up-proton-pass-macos) · [加密导出](https://proton.me/support/pass-export) · [导出源码](https://github.com/ProtonMail/WebClients/blob/main/packages/pass/lib/export/archive.ts#L30-L103) · [Agent 权限](https://proton.me/support/pass-access-tokens) · [CLI 读取能力](https://protonpass.github.io/pass-cli/commands/item/) |
| **Bitwarden 官方云** | Free 为 $0，Premium 年付 $19.80。日常登录可使用自动填充与原生 passkey。私人账户的密码健康报告可辅助分批改密。 | 密码保护的加密 JSON 可导入不同 Bitwarden 账户或自托管实例。JSON 包含已存 passkey，部分早期 passkey 有计数器限制，附件需另行备份。设置为锁定而非退出后，已同步设备可离线解锁并只读。Agent Access SDK 官方说明仍处早期测试阶段，单次同意后可将凭证交给目标进程，运行环境的隔离要另行验证。 [定价](https://bitwarden.com/products/personal/) · [改密流程](https://bitwarden.com/help/change-at-risk-passwords/) · [加密导出](https://bitwarden.com/help/export-your-data/) · [锁定与离线](https://bitwarden.com/help/vault-timeout/) · [Agent Access](https://bitwarden.com/blog/introducing-agent-access-sdk/) |
| **1Password Individual** | 美国美元页新客官网年付首年 $35.88，常规价 $47.88/年。已有日常使用的官方支持浏览器 Agent，或频繁使用 Codex Environments 时值得试用。 | 同步设备可离线读；桌面 1PUX 是含附件的明文，需要直接导出到本地加密卷，再异地保存封闭的加密副本。桌面导出不包含 passkey，iOS 或 Android 支持的 Credential Exchange 可直接转到另一兼容应用。1Password for Agents 仅适用 .com 个人／家庭账户和支持的 Agent，不能代用 passkey 或联合登录，已批准凭证最长复用 30 天。Codex Environments 是另一条接入路径，本地 MCP 不返回秘密值，实际接收秘密的进程仍需隔离。 [定价](https://1password.com/pricing/personal?currency=usd) · [离线同步](https://support.1password.com/sync/) · [导出](https://support.1password.com/export/) · [1PUX 附件](https://support.1password.com/1pux-format/) · [Agent 登录](https://support.1password.com/1password-for-agents/) · [Codex Environments](https://1password.com/blog/1password-trusted-access-layer-for-openai-codex) |
| **KeePassXC 或自托管** | KeePassXC 免费，本地 KDBX 适用于要求没有网络仍可读取、且能自己管理文件副本和设备的用户。自托管 Bitwarden 适用于能承担实例更新、备份和恢复测试的人。 | KeePassXC KDBX 是可直接异地复制的加密文件，恢复可用离线电脑实测。同步、移动端选型、冲突处理、恢复材料由个人负责。自托管 Bitwarden 仍需保护服务器、维护 TLS 和补丁，个人网站改密仍由网站接收。 [KeePassXC](https://keepassxc.org/) · [Bitwarden 自托管](https://bitwarden.com/help/self-host-bitwarden/) |
| **Keeper** | Keeper Unlimited 厂商公布的参考年费 $39.99，结算以地区页为准。独立格式备份是其个人版的优点。 | 官方支持导出含附件的加密 KeePass KDBX。KeeperFill 可辅助改密；自动轮转属于另购的 KeeperPAM 面向特定受管资源的能力。 [Keeper 参考定价](https://www.keepersecurity.com/blog/2025/07/22/keeper-vs-1password-comparing-password-managers/) · [加密备份](https://docs.keeper.io/user-guides/web-vault) · [KeeperFill](https://docs.keeper.io/user-guides/browser-extensions) · [KeeperPAM](https://docs.keeper.io/keeperpam/) |

这些价格是 2026-11-16 核对的美元标价，结算可能因地区或渠道而异。按个人时间价值 **$20/小时** 举例，Proton Pass Plus 对 Bitwarden Premium 的首年差额 $4.08，约等于一年 **12 分钟**；常规年价差 $16.08，约等于一年 **48 分钟**。1Password 对 Bitwarden Premium 的常规年价差 $28.08，约等于一年 **84 分钟**。三者都能自动填充，所以只计独有功能实际节省的时间，并扣除备份或部署新增成本。自托管若每月额外占用 15 分钟，一年就是 **3 小时，约 $60**，还未计设备和储存。一次性迁移可以用实测每项耗时乘待迁项目数估价，例如 30 项、每项 2–5 分钟为 1–2.5 小时。以上是情景测算，未在具体设备上试用，也没有用未经测量的事故概率估算安全收益。 [Proton 定价](https://proton.me/pass/pricing) · [1Password 定价](https://1password.com/pricing/personal) · [Bitwarden 定价](https://bitwarden.com/products/personal/)

**异地恢复应测试两种故障。** 服务端短时不可达时，从已同步且处于锁定状态的另一台可信设备离线解锁。原账户或原设备无法访问时，先用测试条目演练离线打开异地 PGP 或 KDBX 副本，或演练导入另一账户或测试实例。Bitwarden 导出选 **Password protected**，绑定原账户的 **Account restricted** 导出可能在账户加密密钥轮转后失效。每次重要凭证换新后更新备份，其他条目可按愿意承受的回退窗口定期导出，例如每月一次意味着可能缺失自上次导出后的全部变化。导出解密材料、硬件密钥或关键服务恢复码跟原设备和主账户分开放置，关键 passkey 和附件分别做恢复测试。 [Proton Pass 导出](https://proton.me/support/pass-export) · [Bitwarden 备份选项](https://bitwarden.com/help/export-your-data/) · [Bitwarden 锁定与离线](https://bitwarden.com/help/vault-timeout/) · [KeePassXC 离线加密数据库](https://keepassxc.org/) · [独立应急访问设计](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access)

Proton Pass CLI 另可导出可离线阅读的加密 HTML 归档，嵌入成功下载的附件，适合自建定时备份。此归档只包含展示用的 passkey 元数据。原生 PGP ZIP 含保存在库中的 passkey 密钥材料，适合验证回导能力。两种导出及与 1Password 的比较见[对比报告](./proton-pass-vs-1password-2026-11-16.md)。 [Proton CLI 归档文档](https://protonpass.github.io/pass-cli/commands/export/) · [归档模型](https://github.com/protonpass/pass-cli/blob/2.7.0/pass/src/domain/archive/model.rs#L117-L161)

**个人密码按风险更换，机器凭证短期签发或按计划轮转。** 日常使用可在支持的网站用 passkey，其他网站由密码管理器生成和自动填充。可能暴露、弱或复用的个人密码迁移时优先换新，NIST 对人用密码的规范反对按照日历强制周期更换。Google Password Manager 有一项范围更窄的可用功能，已知泄露的保存密码在兼容网站上可由用户点击后自动修改。常规 API key 或数据库密码轮转要求目标服务支持签发、替换或撤销接口，自动任务应使用独立的机器身份并在切换后确认旧凭证已撤销。 [NIST 人用密码指引](https://pages.nist.gov/800-63-4/sp800-63b.html) · [FIDO Passkeys](https://fidoalliance.org/passkeys/) · [Chrome 自动修复适用范围](https://support.google.com/accounts/answer/95606?hl=en) · [AWS 轮转流程](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)

**选一种 Agent 执行路径试点即可。** MCP 工具要人审和调用记录，先试 withHuman 托管免费版，使用独立、限权的 OAuth 连接。自带 HTTP/CLI 的 Agent 需要原始密钥隔离时，试 Infisical Agent Vault，公开 Pro 页面列出每月前 5,000 次带凭证请求免费、短会话与 30 天会话日志，代理由用户部署，限制生效取决于运行环境是否强制走代理。业务应用能改代码，且必须按参数或配额阻断时，Alter 有免费 API 档可试，达到上限会停。个人浏览器 Agent 日常登录优先时可试 1Password 已支持的合作客户端，其登录授权与登录后的站内操作是两个边界。 [withHuman 方案](https://withhuman.ai/pricing) · [withHuman 网关](https://withhuman.ai/docs/web-app/mcp-gateway) · [Infisical 方案](https://infisical.com/pricing) · [Alter 方案](https://alterauth.com/pricing/) · [Alter 配额](https://docs.alterauth.com/reference/cli/commands/policy/) · [1Password for Agents](https://support.1password.com/1password-for-agents/)

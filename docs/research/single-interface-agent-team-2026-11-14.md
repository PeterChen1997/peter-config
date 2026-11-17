# 单一项目负责人与多 Agent 协作调研

调研日期 2026-11-14（Asia/Shanghai）。依据官方文档、产品页面和公开源码仓库。产品排序按单负责人入口、项目状态与回报路径判断；本次为文档调研，未实测可靠性、实际费用或任务成功率。

每支团队有一位固定负责人和一个固定对话。你在这里说目标、调整方向、回复需要你判断的事项；负责人拆任务、跟进、验收并主动汇报，成员和看板留在后台。按这个标准，手头已有 **Grok Bot** 就先试一位项目负责人 Bot。要独立搭建，并把完成和阻塞汇总回飞书，优先验证 **Hermes Agent + Kanban**。**Paperclip Agent Chat** 有现成的原聊天完成回报，但异常通知留有缺口。**Multica** 更适合接受在 Issue 里验收的工程团队。

## 每支团队怎样运行

- **一个负责人对应一个固定私聊或项目会话。** 负责人维护一份团队名单和一份项目状态。两支团队可分别有自己的负责人、项目记录和工作范围。
- **成员只向负责人或任务卡交付。** 负责人明确验收要求，跟进依赖，复核证据并处理力所能及的阻塞。需要用户拍板时，在同一个对话里给出选项、建议和继续所需的决定。
- **短报来自项目状态。** 交付、里程碑变化或需要人处理的阻塞触发主动汇报。需要固定节奏时，加一条例程读取任务状态，只汇报变化、下一步和待决事项。Hermes 的定时任务可把输出送到发起会话；普通 Kanban 状态变化默认不唤醒负责人。Grok Bot 则可让每位负责人持有自己的 Routine。内置主动关怀属于账户的 Primary Bot。 [Hermes Kanban](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban#delivery-modes) · [Hermes 定时任务](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) · [Grok Bot Routine](https://docs.x.ai/grok-bot/skills-routines-and-automations) · [Grok Bot 主动联系](https://docs.x.ai/grok-bot/initiative)

可给试点负责人这样交代：

> 你是这支团队的项目负责人，所有对我的汇报都发在这个对话。收到目标后，先读项目状态，再拆分、分派、追踪和验收。成员将结果、证据和阻塞回给你。进度有实质变化、通过验收或需要我拍板时，主动发一条简报，写清当前状态、下一步、需要我的决定及产物链接。每次做出决定或调整任务后，更新项目记录，我会在这里继续给反馈。

## 快速对照

| 工具 | 你对谁说 | 谁负责任务状态 | 结果在哪里看 | 关键限制 |
| --- | --- | --- | --- | --- |
| Grok Bot | 项目负责人 Bot，或账户的 Primary Bot | Bot 记忆、会话、共享电脑上的项目文件 | Bot 可以异步交接，汇报位置取决于入口和 Bot 类型 | 项目级任务账本需要另指定，同账户的 Bot 共享电脑及浏览器登录 |
| Multica | 项目自己的 Squad Lead，可在 Chat 里讨论并建单 | Project、Issue、Squad、执行记录 | Leader 在 Issue 中交付并提请验收 | 原始私聊自动收齐交付结果未获官方文档确认 |
| Hermes Agent + Kanban | 一个负责协调的 Profile，可接飞书等消息渠道 | 持久任务卡、依赖、重试记录与项目目录 | 网关订阅支持回原聊天，完成、阻塞等事件可唤醒负责人 | 自托管网关；需验收飞书路由、订阅和分项目隔离 |
| Paperclip | 每人和每个 Agent 有一条持久对话，可为项目指定固定负责人 | 项目、任务、层级、审批、预算与运行日志 | 实验 Agent Chat 会把已完成任务回报到原聊天 | 默认关闭，仅自动回报完成，进度和异常要看任务板或另配通知 |
| OpenClaw | 飞书等消息渠道绑定项目主 Agent | 项目工作区、会话数据库、可选 Workboard 卡片 | 普通子 Agent 向发起者交回结果；Workboard 有独立事件与订阅 | 需要配置入口绑定、卡片调度和通知；异常重启后子 Agent 不会独立继续执行 |
| Codex / Claude Code subagents | 现有开发环境的一条主对话 | 会话及仓库内的项目交接文档 | 子 Agent 把结果交给主 Agent | 适合有边界的子任务，跨天项目状态需要显式落盘或记录在外部 Issue |
| Claude Code Agent Teams | Lead，成员之间也能直接沟通 | 该会话的共享任务清单 | Lead 汇总，同一会话可查同事 | 实验功能默认关闭；恢复主会话不会恢复 in-process teammates |

## Grok Bot 自己已经支持负责人和异步交接

官方把 Primary Bot 定义为个人的对接入口，可以创建或协调其他 Bot。每个账户选一个 Primary Bot，内置主动联系由它发起。Bot 向另一个 Bot 发消息后，对方会被唤醒并异步回传。分团队时，可以给每支团队指定普通项目 Bot 负责协调和汇总，并给它各自的 Routine。Group Chat 可以看到更多现场交接，个人 Bot 从共享 Slack 频道发起交接则有身份限制。官方表格显示，个人 Bot 在 Slack 私聊中的交接回复回到应用内；Team Bot 可在 Slack 对话中委派给发起者拥有的 Bot，并在对应 Slack 线程回复。共享 Team Bot 的成员各自有会话。 [管理 Bots](https://docs.x.ai/grok-bot/bots) · [运行机制](https://docs.x.ai/grok-bot/how-grok-bot-works) · [消息及交接](https://docs.x.ai/grok-bot/chat-and-collaboration) · [Team Bots](https://docs.x.ai/grok-bot/team-bots)

每个 Bot 可以保留工作记忆。官方文档给出的对话重置示例中，历史重新开始，Bot 的记忆、文件、例程和设置仍在。同一用户的 Bot 共用持久云电脑、文件系统和浏览器登录状态。文档描述的记录入口是会话、搜索、文件与 Bot 记忆。如果要明确跟踪负责人、依赖、验收和阻塞，建议指向已有的项目文件、Issue 或任务系统。交接消息也占使用额度，试用时可将每个阶段限定给一个明确负责人。 [管理 Bots](https://docs.x.ai/grok-bot/bots) · [持久云电脑](https://docs.x.ai/grok-bot/computer-and-apps) · [使用额度与账号](https://docs.x.ai/grok-bot/faq)

## Multica 适合人和 Agent 共用一个交付空间

官方教程展示了完整链路。向 Lead 描述需求，通过 Create with agent 生成结构化 Issue 并分给 Squad。平台先唤醒 Leader；它看 Issue、成员名单和分派规则，在 Issue 中点名执行者。执行者回报会重新唤醒 Leader，Leader 决定下一步、升级问题或汇总到待审，最后由人或既有集成关闭。工作和交付留在同一个 Issue 中，用户可只跟负责人对接；官方示例在 Issue 中贴 PR 和 @ 用户验收，未确认自动把交付写回最初的 Lead 私聊。 [完整教程](https://multica.ai/docs/tutorial) · [Squads](https://multica.ai/docs/squads) · [Issue wakeups](https://multica.ai/docs/issue-wakeups)

项目描述可以存目标、长期约束，项目资源可绑定代码仓库或指定机器上的本地目录。项目描述进入范围内的 Issue 执行上下文；私聊可主动添加 Project context。Project Lead 字段本身只指定负责人，派给 Squad 或在工作流中设置 Project lead 为某一步的处理者才会触发执行。私聊会尽量续上原来的 CLI 会话；底层会话不可用时会新开执行会话，但 UI 聊天历史仍保留。私聊只有创建者可看，共享决策宜写进项目或 Issue。 [Projects](https://multica.ai/docs/projects) · [Chat](https://multica.ai/docs/chat)

可用本地 Daemon 调用已登录的 Claude Code、Codex 等，官网也提供托管执行环境。平台可自托管，官网说明组织内部使用免费，模型和运行环境的成本需另算；公开许可证还对向第三方托管及嵌入商用作出限制。飞书支持私聊和群内 @，普通聊天回复留在当前聊天；新绑定当前只开放给中国大陆飞书，既有国际 Lark 连接可继续使用。飞书 `/issue` 创建的任务分给绑定的 Agent，Squad 分派及其交付是否能始终自动回飞书原对话，需要实测。 [产品页](https://multica.ai/) · [许可证原文](https://github.com/multica-ai/multica/blob/main/LICENSE) · [自托管](https://multica.ai/docs/self-host-quickstart) · [聊天入口](https://multica.ai/docs/channels)

## Hermes Agent + Kanban 适合把飞书留作日常入口

一个 Hermes Profile 可以作为长期负责人，其他 Profile 做调研、实施或复核。负责人通过 Kanban 创建和分配依赖任务，或者把需求放进 Triage，由内置分解器生成任务关系，全部子任务完成后唤醒根任务负责人复查。项目可使用独立的 SQLite 看板。任务卡保留状态、评论、尝试记录和交接；新卡依赖已完成卡片时，可读到上游的汇报及结构化元数据。各 Profile 的记忆本身分开，共同事实可以放在项目文档或任务卡。 [Kanban](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban) · [Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)

从网关聊天用 `/kanban create` 建卡会订阅原会话，完成、阻塞、超时等事件可以触发通知并唤醒原会话 Agent；持久会话里由 Agent 创建的卡也有默认订阅机制。可以实际测试只让负责人对根任务汇报，避免子卡逐条发消息。飞书集成支持中国飞书和国际 Lark、私聊和群内 @；共享群默认按用户分开历史，需要时可配置为全群同一会话。飞书端的完整组合路径和通知去重仍需实测。运行通常需要常驻网关；普通 `delegate_task` 子执行在网关中断后不续跑，跨重启的工作应记录为持久子卡。软件是 MIT，需自行承担模型、工具及运行费用。 [Kanban 网关通知](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban#gateway-notifications) · [飞书和 Lark](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/feishu) · [费用](https://hermes-agent.nousresearch.com/docs/reference/faq/)

## Paperclip 把负责人聊天与跨天任务台接起来

启用默认关闭的实验功能 Agent Chat 后，你和每个 Agent 有一条持续对话。负责人和你澄清目标，生成带背景、计划和验收标准的常规任务，分到合适项目和 Agent。相关任务被标为完成时，负责人会被唤醒，将完成内容及结果链接贴回原对话。你可以在聊天侧边查看它参与过的任务和产物。队友按公司内的任务可见性读取对话，只有发起者能在其中发送。多个项目使用同一负责人时，私聊按 Agent 归属；需要固定且独立的项目入口时，可以为不同项目配置各自的负责人。 [Agent Chat](https://docs.paperclip.ing/experimental/agent-chat/)

自动回报范围目前限于完成，进行中、阻塞、失败和取消状态还需看任务、日志或其他通知机制。`/new` 会留住可见历史和任务，启动新的模型会话；此前分派的任务即使之后完成也不会向新会话发完成更新。任务的运行还取决于适配器，官方接口支持保存会话状态供后续 heartbeat 复用。产品提供组织层级、委派、审批和预算，适合管理跨职能 Agent 团队。本地版 MIT，可自托管，官网云版入口目前展示等候名单。 [Agent Chat](https://docs.paperclip.ing/experimental/agent-chat/) · [Adapters](https://docs.paperclip.ing/reference/adapters/overview/) · [Delegation](https://docs.paperclip.ing/guides/org/delegation/) · [产品页](https://paperclip.ing/)

也可以让已有 Grok Bot 作为 Paperclip 的外部执行 Agent。实验接入保留其应用和持久上下文，通过 MCP 连接任务、用 Grok Routine webhook 唤醒；要求 Paperclip 的身份验证、公开 HTTPS、Assistant connections 和 Runner。外部模型消耗在 Paperclip 中不可见，Paperclip 停止任务也不能保证远端 Bot 停止。官方流程是 Paperclip 指派任务给 Grok Bot；如果想继续以 Grok 的原对话为唯一项目入口，需要另验证从 Grok 发起任务与收回汇报的体验。 [外部 Agent](https://docs.paperclip.ing/experimental/external-agents/)

## OpenClaw 适合可控的消息入口与本地数据

Gateway 可将渠道账号或具体聊天绑定到项目负责 Agent，每个配置 Agent 有各自的 workspace、工具及会话库。主 Agent 可启动有隔离上下文的内部子 Agent 收回结果，也能配置其他 Agent 或通过 ACP 启动 Codex、Claude Code 等执行环境。把项目入口保留给主 Agent，依需要让子 Agent 拿到简明任务或可控的上下文副本。 [Multi-agent routing](https://docs.openclaw.ai/multi-agent) · [Sub-agents](https://docs.openclaw.ai/tools/subagents) · [ACP](https://docs.openclaw.ai/tools/acp-agents)

当前官方文档给出的会话默认值是无自动重置，按天和空闲重置是选项。会话与记录存在本地数据库，活跃上下文随长度压缩，长期决定可写入 `MEMORY.md` 或项目文件。Gateway 崩溃后的恢复有明确边界：符合条件的主会话执行可能续上，一般子 Agent 执行不会独立恢复，主 Agent 应先查已经写出的文件和动作，再继续或换执行者。 [会话管理](https://docs.openclaw.ai/concepts/session) · [记忆](https://docs.openclaw.ai/concepts/memory) · [子 Agent 恢复](https://docs.openclaw.ai/tools/subagents/operations)

Workboard 是内置但默认关闭的 SQLite 看板，可管理持久卡片、父子依赖、分派、运行记录、交付物和事件订阅。它是单 Gateway 的运营任务板，工作者通过 Gateway 分派，卡片身份和日志可以跨执行保留；将任意事件统一汇总到固定飞书私聊还要设计通知路由。旧的共享 Tasks ledger/TaskFlow API 已从当前自动化架构移除，旧文章中的方案应按版本核查。 [Workboard](https://docs.openclaw.ai/plugins/workboard) · [Automation](https://docs.openclaw.ai/automation) · [飞书](https://docs.openclaw.ai/channels/feishu)

## 已在 Codex 或 Claude Code 工作时的低成本入口

**Codex。** 置顶一条项目负责聊天，让主 Agent 调研、分派、追问并收齐结论。子 Agent 专注各自工作，主对话避免塞满原始日志；当前本地版本按直接请求或适用的项目/技能指令委派。主线程可恢复或压缩；固定交接文档保留当前目标、决定、未完成项、负责人及产物链接，`AGENTS.md` 放稳定规则和交接文档入口。这样现在就能试出日常使用体验。若要支持多个负责人、可靠通知、独立任务流转及团队查看，再接 Issue 系统或用上述平台。 [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) · [最佳实践](https://learn.chatgpt.com/docs/learn/best-practices) · [Memories](https://learn.chatgpt.com/docs/customization/memories)

**Claude Code。** 让一条主会话运行专门的 subagents，可匹配任务自动委派或由人显式触发；独立上下文、可选工具范围、工作树及 `memory: project` 能减少主会话负担。一般自定义 subagent 可按 ID 或名字继续，内置 Explore/Plan 是一次性的。需要成员横向协作和共享任务时，Agent Teams 提供 Lead、成员间通信与共享任务，但仍属默认关闭的实验功能。一条会话只能有一支团队，`/resume` 或 `/rewind` 无法恢复进程内队友，重启后需要重新委派。长期规则与会话知识还可写在 `CLAUDE.md` 或 auto memory。 [Subagents](https://code.claude.com/docs/en/sub-agents) · [Agent Teams](https://code.claude.com/docs/en/agent-teams) · [项目记忆](https://code.claude.com/docs/en/memory)

**GitHub Squad。** 如果只做开发、又希望新会话接回已有团队上下文，可用 Squad 把角色说明、共享决定和各角色工作历史放进仓库的 `.squad/`，由协调者对接用户，状态可随仓库一起版本化。官方列出 Copilot、Claude Code、Codex 等宿主，各自支持的能力不同。当前矩阵将 Codex 的后台执行标为不支持，其参考环境未安装 Codex，对这个宿主仅做了静态检查。 [Squad](https://github.github.com/squad/) · [记忆机制](https://github.github.com/squad/docs/concepts/memory-and-knowledge/) · [宿主支持矩阵](https://github.github.com/squad/docs/reference/host-feature-matrix/)

**omp Vibe Mode。** 一条终端会话里的 director 分配任务、核查结果，worker 分别保有会话和追问上下文。worker 启动时收不到 director 对话，需明确交接，默认共享工作树，退出 Vibe 模式后会停掉未完成的 worker。Tern 能为终端会话提供持久工作区，当前在封闭测试。这个组合值得用于代码密集的交付，项目任务状态仍可交给仓库或 Issue。 [Vibe mode](https://omp.sh/docs/vibe) · [Tern](https://stencil.so/tern) · [已有本地研究](tern-omp-agent-development-2026-10-31.md)

## 另外几款接近的产品

- **LobeHub。** Agent Group 有 Orchestrator 做分派和综合，支持顺序、并行、迭代等协作模式，可给组配置共享背景。产品还提供可分派、可追踪的任务界面。适合先看调研、写作、代码混合协作；组聊委派、独立任务和项目上下文串接后，跨日阻塞、重启和结果回原入口的完整路径仍需实测。 [Agent Groups 文档源码](https://github.com/lobehub/lobehub/blob/canary/docs/usage/agent/agent-team.mdx) · [任务面板](https://lobehub.com/task)
- **dewee。** 有固定 Lead、成员、共享任务板与依赖关系，成员遇到阻塞可以升级给 Lead。官方明确承诺最长十分钟的异步 Agent 委派会回到原对话。团队任务板是另一条执行路径，文档尚未确认看板任务都由 Lead 主动汇报到同一个用户会话。 [Agent Teams](https://dewee.sh/docs/concepts/agent-teams)
- **OpenAI Dots。** 每个成员一个个人 dot，能创建 ChatGPT Work 或 Codex 任务，持续跟进并使用记忆。每项任务有自己的会话，不会自动带上你和 dot 的所有对话。适合已经有访问资格、想让一个个人助理协调 Work/Codex 的用户。文档给出了逐步开放和工作区限制。 [使用和资格](https://help.openai.com/en/articles/20001530-getting-started-with-your-dot)
- **Claude Duet。** 用一个持续对话派发工作，继承 Claude 的记忆、技能和连接应用，也可以按话题开频道，频道共用记忆。截至调研日是美国区个人订阅的候补研究预览。官方主打个人工作的统一入口，未在相关产品文档中核实可按项目指定一组长期 worker 并追踪依赖任务。 [Claude Duet 帮助中心](https://support.claude.com/en/articles/17631495-get-started-with-claude-duet)

## 项目上下文放在哪里

负责人聊天适合讨论目标、答疑、做决定。把需要接手的人和 Agent 都能查的事实写进项目 Brief、Issue 或版本化 Markdown，至少包括当前目标和约束、已定事项、工作进度以及证据链接。每个子任务只拿所需背景、边界和验收要求，回写任务状态和产物位置。负责人在派单前读项目记录，在汇报前核对任务状态。这样切换模型、恢复会话或更换执行者时都有可追溯的接手材料。

协作本身会增加消息与模型调用。研究预印本对 1,902 次编程任务运行进行分析，在其测试条件下，指定协调者并未稳定提高任务成功率，共享文件对不同任务的收益也不同。这个结果适合用来提醒选型时测完成时间、用量和人为干预次数，无法直接用于给本文产品排名。 [When Agents Coordinate](https://arxiv.org/abs/2608.16801)

## 用同一条真实工作验证

拿一个包含调研、实施、复核的两天任务，比如为小功能比较两个方案、实施并独立评审。只和 Lead 聊，开两个执行角色就够。用下面几个条件验收。

1. 下达一个目标后，Lead 生成有验收标准和来源链接的任务，执行者各自收到分派，无需你手动转述。
2. 人为留一个需要决定的输入，观察有无在原聊天收到说明，是否能在原处回复并解除阻塞。正常完成时也检查汇报和证据是否回到那个入口。
3. 第二天从原入口问当前进度、谁在等什么、最新产物在哪里。再开一个干净的模型会话或重启测试运行环境，让负责人凭任务 ID 和项目 Brief 重建状态，核对有无重复做已完成的动作。
4. 记录你必须打开的页面或会话数、主动追问次数、重复贴背景次数和模型用量。同一个小任务在现有工具和候选工具各跑一次，比较节省了什么。

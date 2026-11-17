# 能迁移到 Multica 的 Agent 工作流

调研日期 2026-11-14（Asia/Shanghai）。范围是已有基础 Squad、希望每个项目仍由一位 Lead 对接的场景。行业热度参考近期公开发布、开源实现和研究，未做市场份额排名。厂商案例与预印本分别注明，本文没有在用户的 Multica 工作区执行实验。

**试验顺序建议：先给现有 Squad 加独立验收，再试有依赖约束的并行，最后把等待与复核改为事件触发。** 这三种变化可以保留 Lead、Engineer 和 Reviewer 的配置。只有真实任务遇到持续的解释成本或能清楚隔离的工作支线时，再把 Planner、专职 QA 或更多 worker 固化进 Squad。

## 近两个月有哪些实质变化

| 信号 | 说明 | 能迁移的部分 |
| --- | --- | --- |
| Google Antigravity `/swarm`，11 月 10 日预览 | 固定对话里的协调者分配独立 worktree，执行者、验证者用共享消息板交接。还安排 Agent 监看停滞。Google 11 月 12 日称前几天已发起数万次 swarm，属于产品方公布的使用量。 | 用父 Issue 保留固定 Lead，子卡分区，Reviewer 核对实际 diff 和测试，一次 Wakeup 处理等待。 [发布说明](https://antigravity.google/blog/gemini-4-carbon-in-google-antigravity) · [Swarm 文档](https://antigravity.google/docs/swarm/) · [Google 使用量说明](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/) |
| Google Antigravity Orchestrator，11 月 12 日发布 | 同一执行过程可在不同模型间交接。官方案例让强模型处理规划和疑难返修，让较快模型处理明确步骤。 | 先按失败类型升级，不把所有角色默认换成大模型。Multica 可按 Agent 配模型，文档未承诺在同一次运行中复制 Google 的动态路由。 [发布说明](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/) · [Multica Agents](https://multica.ai/docs/agents) |
| GitHub Copilot Dynamic Workflows，10 月 1 日公开预览 | 顺序、并行、交叉复核及暂停点可由代码编排，Agent 做需判断的部分。产品发布证明平台在支持这类路径，未给出普适生产率结论。 | 用固定状态和依赖表达常规流程，Lead 判断具体分工与例外。 [发布说明](https://github.blog/changelog/2026-10-01-dynamic-workflows-in-copilot-cli-and-the-copilot-app/) |
| GitHub Agentic Workflows，10 月 28 日 GA | GitHub Actions 调用 Agent 做 Issue 分类、CI 分析、文档等工作。默认只读，结果经 Safe Outputs 校验后才能产生有限写操作。 | 先用 CI 或 Issue 事件唤醒 Lead，限制可执行操作与重试范围。 [GA 公告](https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available/) · [Safe Outputs](https://github.github.com/gh-aw/reference/safe-outputs/) |
| WorkflowArena，11 月 9 日预印本 | 145 个长任务、八个领域，隐藏验证器检查最终产物。不同模型及其执行环境的分派策略不同；固定执行模型，在部分难题上换编排可以改变表现。 | 评估 Lead 时保持执行者和验收稳定，测协调本身的贡献。 [论文](https://arxiv.org/abs/2611.12856) |
| Multi-step SWE，11 月 4 日预印本 | 69 个任务，每项含 5–15 个依赖步骤，把前一步实际产出交给下一步。九个受测模型中最高完整解决率为 18.5%。适用范围是该 benchmark。 | 每阶段验证能否给下一阶段稳定接手；不要只统计子任务标记完成。 [论文](https://arxiv.org/abs/2611.07166) |
| NP-Bench，10 月 5 日预印本 | 根据任务所有权分区，并按生产者与消费者关系控制合并顺序，小样本的干净集成从 1/9 改善到 9/9。结果不代表任意项目的收益。 | 并行前写清可改文件和接口，最后在集成分支验收。 [论文](https://arxiv.org/abs/2610.07261) |

## 六种工作流及迁移判断

### 1. 规格驱动与独立验收

GitHub Spec Kit 将用户行为和场景规格、技术计划、任务拆分分开，并提供澄清与一致性检查。对已有项目可以只迁移一份短规格，包含目标场景、范围、验收证据和需要确认的开放问题。Lead 负责把需求澄清到可派单的程度；实现者拿到可执行标准；Reviewer 直接阅读规格和实际产物。测试能表达的要求交给测试，文案与交互之类的要求给具体示例和判据。只有重复出现同类复杂项目时才尝试完整 Spec Kit 工作流。 [Spec Kit](https://github.com/github/spec-kit)

Anthropic 的长任务实验把规划、生成、评价拆开。评价者按事先定义的准则检查实际应用，失败反馈推动生成者做下一版。改用能力更强的模型后，作者把每阶段评价改成最后集中评价，并观察到简单部分的额外评价会带来开销。建议在 Multica 把 Reviewer 的预期结果固定为 `PASS / CHANGES_REQUESTED / BLOCKED`、复现步骤、证据链接和验收条目。实现与评价的角色分开即可，开始时可以用同一模型，减少变量。 [Anthropic Harness](https://www.anthropic.com/research/harness-design-long-running-apps) · [演示源码](https://github.com/anthropics/cwc-long-running-agents)

### 2. 有边界的并行，最后集中集成

适合几条可并行的调查，以及接口既定、修改区域可分开的代码任务。Lead 先确定对外契约和文件所有权，后端、文档或独立验证各自使用子 Issue 和隔离 worktree；有依赖的步骤等前置产物确认后再启动。选一位集成者，完整测试在合并后的共同版本上跑。简单顺序任务可以保留同一个执行者；多路执行会增加沟通、集成及模型调用。NP-Bench 的合并实验和协调研究提供了机制依据，不能换算成 Multica 的准确提速幅度。 [NP-Bench](https://arxiv.org/abs/2610.07261) · [When Agents Coordinate](https://arxiv.org/abs/2608.16801)

### 3. 事件唤醒，跨天从项目记录继续

Anthropic 的早期长任务 harness 用进度文件和 Git 记录让新会话接着做，OpenAI 的 Codex 团队把仓库知识作为可版本化的事实来源。两者都提示，把重要决定和检查证据写在任务或仓库里，当前会话可按需重建。迁移到 Multica 时，用 Lead、主 Issue、唯一的下一步组成交接，等待 CI、依赖关闭、回复或约定时间时设 Issue Wakeup。横跨项目的例行扫描再用 Autopilot。中断测试可让另一个合适的会话或 Agent 仅凭 Issue、PR 和 CI 继续，检查是否重新做了已完成的副作用。 [Anthropic 跨会话](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) · [OpenAI Harness Engineering](https://openai.com/index/harness-engineering/) · [Multica Issue Wakeups](https://multica.ai/docs/issue-wakeups)

### 4. 同一题的多路候选，按证据择优

区别于任务拆分：几个运行从同一版本解决同一个问题，独立候选交给同一验收来判。适合难复现问题的独立分析、复杂实现方案比较、可以离线比较的选择。先锁定验收标准，给两条候选同等上限和隔离环境。Reviewer 用相同测试或评分表评价，Lead 选择一条，尽量避免合并所有候选。11 月的《Test-Time Compute Scales Better with Parallel Agent Teams》讨论有 verifier 时可怎样花测试时计算，特定推理任务的增益不直接适用于日常项目。建议先对照「一个实现者多迭代一次」和「两个候选各一次」，再决定是否值得付出额外协调成本。 [论文](https://arxiv.org/abs/2611.09798)

### 5. 受约束的仓库维护自动化

GitHub Agentic Workflows 把自动化放进可重放的 Actions 流程，并限制输出。适合将高频低风险的 Issue 分类、CI 诊断、过期文档检查做成模板。Multica 最小实验是「Autopilot 或 CI 事件启动 → Agent 只读分析 → 输出一条带证据的 Issue 评论或建议」，重复运行使用同一对象，记录误报、重复报告和需要人工接手的比例。需要用 GitHub 的 Safe Outputs 等写权限限制时，把确定性验证和授权留在原有 CI/Actions，Multica 负责派单、跟进和汇报。这是两层工具配合，不能把 Runbook 提示词当成 Safe Outputs 的能力。 [GitHub GA](https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available/) · [Multica Autopilots](https://multica.ai/docs/autopilots)

### 6. Software Factory 的独立场景测试

StrongDM 公布的 Software Factory 使用场景及 Digital Twin Universe 检查真正的端到端任务，部分场景独立于实现者可以修改的代码。迁移到小队时可以只取一项：一个小型外部服务 mock 或测试夹具，加两三条不由实现者改写的契约测试，并留下实际运行结果。完整的双生环境、无人审查或长时间自治都有建设和验证成本，小队初期没有必要一起引入。厂商公开案例证明了这种架构可实现，不能视为替换当前流程的普遍证据。 [StrongDM Software Factory](https://factory.strongdm.ai/) · [技术说明](https://factory.strongdm.ai/techniques)

## 如何读这些证据

GitHub 发布说明提供可用功能和时间，Anthropic、OpenAI 与 StrongDM 的文章提供可复用设计和案例。预印本提供特定模型与任务设计下的评估。更可信的本地比较是固定模型、预算、起点和验收，先保留基础 Squad 作为对照，再每次只动一处。工时计入你介入的时间，模型调用计入失败重试和等待后唤醒。测试最终可交付结果，不以 Agent 数量、评论数或已关闭 Issue 数量当成收益。

## 在 Multica 里把现有 Squad 用作试验台

以 **2026-11-14** 的公开文档为准。官方 Changelog 已列出 11 月 13 日的 v0.9.0。先在自己的 workspace 确认有对应入口，尤其是 Settings → Workflows 和主 Issue 的系统 Wakeup。这里给出可复制的试验方案，本次没有操作你的 Multica workspace。 [Multica Changelog](https://multica.ai/changelog) · [Workflows](https://multica.ai/docs/workflows) · [Issue wakeups](https://multica.ai/docs/issue-wakeups)

| Multica 能力 | 在试验里负责什么 | 容易踩的地方 |
| --- | --- | --- |
| Squad | 父 Issue 分给 Squad，由 Lead 分派、协调、汇总和升级 | 指派给 Squad 才触发这套协议。Project Lead 字段本身不开始工作 |
| Sub-issue Stage | 同一父 Issue 下，按批次组织不同子任务 | 在默认打开的系统规则下，当前批次都关闭会唤醒 Lead。Stage 编号本身不拦住提前开工。后续批次先留在 Backlog，由 Lead 决定放行 |
| Project Workflow | 在同一张 Issue 内，按状态顺序交接给不同处理人 | 移动状态才触发交接。同时设置 Squad 和 Workflow 交接时，先核对谁会成为当前 assignee |
| Issue Wakeup | 在已有 Issue 上等 CI、子任务、指定回复或时间到点 | 系统已提供子任务批次唤醒。单次等待可设超时并回到 Lead，避免重复触发 |
| Autopilot | 从定时或外部 webhook 启动新的工作 | Run only 的结果在运行历史里。需要协作记录时选 Create issue，或让任务把简报写到指定主 Issue |
| Worktree 与 PR | 让并行实现隔离，让验收指向明确的代码版本 | 共享文件仍可能冲突。评审要注明 PR 和 commit，集成后再跑一遍整体检查 |

表格依据 [Squads](https://multica.ai/docs/squads) · [Issues](https://multica.ai/docs/issues) · [Workflows](https://multica.ai/docs/workflows) · [Issue Wakeups](https://multica.ai/docs/issue-wakeups) · [Autopilots](https://multica.ai/docs/autopilots) · [Project resources](https://multica.ai/docs/project-resources)。

### 实验 A｜原 Squad 对照独立验收

**先做这一组。** 保留 Lead、Engineer、Reviewer 三个角色。选一个能从现有测试入口验证的小改动，例如给 CSV 导出加日期筛选。约定三个独立检查：日期边界、无结果时的约定行为、已有无筛选调用仍正常。

1. **对照组**按你现在的 Squad 跑一遍，给它相同的原始需求和公开验收场景，记录它怎么拆、怎么验收、哪里需要你催。
2. **试验组**从相同起点开独立工作树。Lead 先把交付物、范围边界、用户场景和验收证据写进同一张 Issue。两组使用同一份最终评分清单。可留一个代表性的边界用例仅供最终评审，工程师仍能看到对应行为要求。如果试验组改善明显，再分开测短规格和独立验收各自的收益。
3. Engineer 贴出 PR、commit 和测试日志。Reviewer 用独立的运行会话检查实际交付。先读规格和当前代码，再自己运行一个关键场景。结果用 `PASS / CHANGES_REQUESTED / BLOCKED` 加证据链接，说明哪些场景尚未执行。第一轮发现问题由 Lead 分派回同一 Engineer，原 Issue 保留记录。可先限两轮返工，仍有分歧再向你说明。
4. 验收通过后，Lead 把父 Issue 放到 In Review，附修改、结果和需要你决策的事项。若 PR 合并后还要验收回归或发布，在该 Issue 上启用 Keep status when PRs merge。可让你自己用一份清单给两组结果盲评。

第一轮用 Squad 在同一 Issue 里组织。若后来几十张卡都经过同一个交接顺序，可在试验项目复制一个 Workflow，单独配 Engineer → Reviewer → 人工验收，并设定 If rejected, send back。用 Issue 归属、评审结果和验收证据判断，运行日志的 Completed 只说明那次运行正常结束。 [Squads](https://multica.ai/docs/squads) · [Workflows](https://multica.ai/docs/workflows) · [Runs](https://multica.ai/docs/tasks) · [GitHub 集成](https://multica.ai/docs/github-integration)。

### 实验 B｜阶段式并行、汇合与换会话接手

选一项自然可拆的功能，例如「导入 CSV，并在预览页逐行显示错误」。沿用 A 的评分规则，每批放 1–2 张子 Issue。与同样验收标准的串行实现比较。你继续只和 Lead 对接。

| 批次 | 子任务及起始状态 | Lead 放行条件 |
| --- | --- | --- |
| Stage 1 | 启动接口与验收场景卡 | 请求、响应和错误类型明确。必要的产品选择由 Lead 汇总问你一次 |
| Stage 2 | 分两张卡做解析层与预览 UI，均先放 Backlog | Stage 1 已通过后移到 Todo。每个成员写自己的文件范围，UI 可用约定接口的 mock 开发 |
| Stage 3 | 集成和独立端到端验收，先放 Backlog | 两边给出可定位的分支、PR 或 commit，Lead 检查后指定集成人。集成后用最终 commit 做整体验收 |

系统 Stage Wakeup 按 `done` **或** `cancelled` 计算关闭，且父子状态各自独立。要求 Lead 读验收证据再放行。取消了必要工作要补替代方案或重新约定范围。子卡默认通常到 In Review，单纯提交 PR 不会关闭批次。约定试验内的子卡由 Lead 在验收后标 Done，父 Issue 留给你确认。创建子卡时子卡可能继承父卡 assignee，要明确改成成员，避免又派给 Squad 造成重复协调。 [Issues](https://multica.ai/docs/issues#projects-and-sub-issues) · [系统 Wakeup](https://multica.ai/docs/issue-wakeups#wake-the-parent-when-sub-issues-finish) · [Squads](https://multica.ai/docs/squads)。

**再做一次接手测试。** 在 Stage 2 完成前后，让 Lead 写下目标、已定接口、子 Issue ID、验收状态、PR/commit 和下一步。第二天开一个空白聊天或用干净会话接手，只给父 Issue ID 和项目入口，检查能否复原状态并指出唯一的下一步。另可模拟一个成员停止运行后重试，先核对已有 PR/commit，再继续；由于重试会尽量复用原文件与会话，干净会话和故障重试要分别测。 [项目上下文](https://multica.ai/docs/chat) · [Runs](https://multica.ai/docs/tasks)。

如果先拿知识工作试，可以把同样的三阶段用在供应商评估。Lead 先定比较维度，两位执行者分别查官方能力与条款、搭小样验证关键场景，最后由 Reviewer 抽查来源与实测证据。每人提交结构化发现和原始材料链接，Lead 统一写成可选型的对照结论。Anthropic 的研究系统把子 Agent 的输出放在可引用的文件里，以免每一轮都在聊天里复制整份材料。 [Anthropic 多 Agent 研究系统](https://www.anthropic.com/research/multi-agent-research-system)

### 实验 C｜让 Lead 在事件发生时回来

在测试项目加一个现有 Issue，模拟一个普通 CI 失败或需要用户决策的依赖。让 Lead 挂一次性 Issue Wakeup，绑定该 Issue 或其直接关联的 PR，在对应 CI 检查完成、收到回复、或到截止时间后回来核对。它只需要评论一次，给出观测到的状态、下一步和证据链接。可以先用 Wake now 校验权限与输出，再用一次真实的测试事件验证触发。CI 条件只认规则建立之后完成的检查。涉及外部写入或合并，继续按你在实验里指定的审批进行。 [Issue Wakeups](https://multica.ai/docs/issue-wakeups) · [GitHub 集成](https://multica.ai/docs/github-integration)。

通过后再试 Autopilot，比如用 Run now 手动测试「扫描本项目超过一天未推进的卡，按风险列前三个，回写指定跟踪 Issue」。确实要从 GitHub Actions 等外部事件开新任务时，再加 webhook，复用来源事件 ID 作为幂等键。用同一事件发两次，验收只入队一次。Lead 在 Issue 里 @你会进入你的 Inbox。原始 Lead 私聊自动回写仍需在你的工作区单独验证。 [Autopilot 触发与去重](https://multica.ai/docs/autopilots) · [Inbox](https://multica.ai/docs/inbox) · [Chat](https://multica.ai/docs/chat)。

### 实验 D｜昂贵任务先并行规划，再单线实现

方案本身存在明显不确定性时，用同一个明确任务和代码基线，分两个只读调查，一人查现有复用点和迁移成本，一人查失败模式和验证方法。各自独立写候选方案、三条证据、风险和落地工期，再由 Lead 选择、合并或请你拍板。一位 Engineer 落地，Reviewer 沿用 A 的验收。与当前单人规划比较。10 月的 ProgramBench 预印本中，多 Agent 方案成本为单 Agent 的三到七倍；在其一组同模型实验里，只并行规划取得与全阶段委派相同的分数，成本约一半。它提供了一个值得测试的假设，不能直接预测现有项目的费用。先保持实现模型不变，再看按角色换模型是否值得。 [ProgramBench 预印本](https://arxiv.org/abs/2610.17471) · [Multica Agents](https://multica.ai/docs/agents)。

## 可直接给 Multica Lead 的试验指令

以下是可贴进 **Squad Instructions** 的起步版本。用于 A 时，把分阶段内容留到 B 再加。

> 你负责把用户目标交付到可验收。先读 Project description 和当前 Issue。把交付物、范围边界、验收场景和证据位置写成简短的执行说明。明确每个成员负责的改动、依赖和交付位置。成员交付后，让 Reviewer 依据 Issue 的验收场景核对最终 commit 和测试证据。需要返工时，给 Engineer 一个可核对的失败场景。
>
> 多阶段任务由父 Issue 协调。后续批次在 Backlog 等待。系统唤醒后，核对上一批实际结果和依赖，再放行下一批。遇到外部依赖就给自己建一次 Issue Wakeup。记录每次决定、子 Issue ID、PR/commit、验收状态和下一个动作，让新会话可以从父 Issue 继续。
>
> 有实质进展、验收就绪，或需要用户决定时，在父 Issue 汇总。写清「完成的事 / 下一步 / 需要你决定什么 / 证据链接」。只有影响范围、验收或关键依赖的选择才 @用户。实验中的父 Issue 在证据齐备后移到 In Review。

## 怎么比较

先用一个任务理解工具，再用至少三组相近的小任务决定是否保留某种流程。同任务 A/B 尽量从相同 commit 起步，独立 worktree、独立会话，固定模型、预算、权限及验收清单，不向第二组提供第一组的产物。若做不到严格匹配，把结果当经验记录。

| 指标 | 怎么记 |
| --- | --- |
| 验收质量 | 通过几个独立场景，先记首轮结果，再记返工后结果。对非代码任务用同一份 rubric 和来源抽查 |
| 人的协调成本 | 追问、手工转述、手动派活各多少次。把主动做产品决策记在单独一列 |
| 交付耗时 | 从下达任务到可验收的实际用时，以及 Agent time，两者在并行时通常不同 |
| 模型成本 | 总运行数、Tokens、Spent 及失败/重复运行。模型未上报的用量记为未知。新版有 Include sub-issues 时把子卡计入 |
| 交接与可靠性 | 新会话能否准确说出已定事项和下一步。是否有提前放行、重复执行或需要人去子卡捞进展 |

如果 A 提高验收质量或减少人工协调，先留下 A。B 只应用在可并行且交接成本可控的任务。C 以事件能够可靠回到 Lead 为验收条件，D 以减少选错方案或返工的程度来决定是否值得额外花费。运行耗时和成本可在 Issue Execution log 或 Analytics 里核对。 [Runs](https://multica.ai/docs/tasks) · [Analytics](https://multica.ai/docs/analytics) · [Changelog](https://multica.ai/changelog)。

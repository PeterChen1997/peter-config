# Tern + omp：Agent 开发工作流调研

调研日期：2026-10-31（Asia/Shanghai）。范围是 Stencil 的 Tern 与 can1357/oh-my-pi，不是同名的 tern.build。依据官方文档、公开源码和作者实验；没有安装软件或复现实验。本文区分当前功能、作者测量和下一代设计。omp 源码核对快照为 `91afeb4385ad0bb07efef33b877057f8d1fb930b`；官网和 main 链接可能后续更新。

## 核心判断

这一组合把编程 Agent 的执行环境和人与 Agent 的工作界面一起设计。模型提供推理与生成，omp 提供上下文、工具、执行循环、会话和任务委派，Tern 提供持久工作区、原生界面与跨客户端连接。它的吸引力在于减少实际开发循环中的摩擦；不能据此推导出同一模型在所有任务上都会更聪明或更便宜。

来源：[omp 概览](https://omp.sh/docs)、[Tern 产品页](https://stencil.so/tern)、[TSP 协议](https://docs.stencil.so/tern/protocol/index.html)。

## 各层负责什么

| 层 | 职责 | 边界 |
| --- | --- | --- |
| 模型与服务商 | 推理、生成、工具调用决策 | 可按角色选择；模型质量、延迟与费用仍取决于具体模型和接口 |
| omp | 组装上下文、调用模型、执行工具、组织子 Agent、保存会话 | 是 Pi 的 fork，当前包含 TypeScript/Bun 运行层与 Rust 原生模块 |
| Tern | 终端、窗格、会话守护进程、原生 UI、文件与 Git 等工作区视图 | 是交互和工作区层；不等同于 omp 的任务决策循环 |
| 项目环境 | 文件、测试、语言服务器、调试适配器、浏览器等 | 最终正确性需要在项目中验证 |

omp 不依赖 Tern 才能使用，既有普通终端交互，也有 SDK、RPC、ACP 等入口。Tern 提供的原生展示是可选增强。

来源：[omp README](https://github.com/can1357/oh-my-pi/blob/main/README.md)、[SDK](https://omp.sh/docs/sdk)、[Tern SDK README](https://github.com/stencil-hq/tern-sdk/blob/main/README.md)。

## 为什么这两个组合起来有价值

### 1. 把工具界面交给终端原生绘制

传统 TUI 在字符格里画边框、处理换行、滚动与刷新。TSP 让 omp 发送语义组件树及更新，例如工具卡片、代码、diff、进度和输入框；Tern 负责布局、绘制、动画与滚动。交互事件回传给程序，业务状态仍由程序管理。

omp 会检测 TSP 支持并选择原生后端；缺少语义描述的组件可回退为文本行，普通终端继续走字符渲染。协议数据随 PTY 输出传输，可经过会话守护进程和 SSH。这不只是把 CLI 放进一个漂亮窗口，而是更换 UI 的表达与绘制方式。

来源：[TSP 分工](https://docs.stencil.so/tern/protocol/index.html)、[omp renderer 文档](https://github.com/can1357/oh-my-pi/blob/main/docs/tui-core-renderer.md)、[TypeScript TSP SDK](https://github.com/stencil-hq/tern-sdk/blob/main/typescript/README.md)。

### 2. 让长任务与窗口生命周期分开

Tern 的窗格和屏幕权威副本由 session daemon 持有；窗口连接并展示它们，所以关窗口后进程可以继续运行。插件也拆成 host/window 两部分，分别处理持久窗格和单窗口行为。

产品页展示桌面、iPhone、浏览器连接同一会话，以及重启后恢复工作区的体验。应区分“关闭窗口后仍在运行”和“机器重启后恢复持久状态”：后者不意味着操作系统进程在断电期间继续执行。具体恢复范围未在本次调研中实测。

来源：[Tern Architecture](https://docs.stencil.so/tern/concepts/architecture.html)、[Tern 产品页](https://stencil.so/tern)。

### 3. 优化模型实际使用的开发工具

Hashline 的基本思路是读取时附带内容校验标识，编辑时引用已读内容的位置与标识，避免反复完整复述旧文本；内容变更后拒绝失效的定位并要求恢复上下文。具体语法和校验粒度随版本演进，早期文章中的短行哈希示例不能直接当作当前 API。

omp 的 LSP 工具让 Agent 获得定义、引用、类型、诊断和语义重命名等能力；DAP 工具让它操作断点、步进、调用栈和变量。这些能力依赖相应语言服务器、调试适配器和项目配置。将反馈接入执行循环，有助于减少仅靠文本猜测的错误，但不替代编译与测试。

来源：[Hashline 作者文章](https://stencil.so/blog/the-harness-problem)、[Code intelligence](https://omp.sh/docs/code-intelligence)、[Debugging](https://omp.sh/docs/debugging)。

## 实际开发流程

一个合理的使用流程是：给出目标与验收标准 → 主 Agent 调查并计划 → 对独立工作分派子 Agent → 使用文件、LSP、终端、浏览器或调试工具完成工作 → 主 Agent 整合并验证 → 人查看 diff 与证据。

普通 subagent 适合独立调查、按文件划分的修改、审查等。子 Agent 有独立会话，不能假设知道主对话全部内容；需要明确交代目标、文件归属、接口和验证方式。隔离工作区是可选能力，不能把 README 中的推广措辞理解为每个任务默认拥有独立工作树。即使隔离，集成时仍可能冲突。

当前官方 Subagents 页面列出的默认隔离模式为 none，并说明可启用平台相关的文件系统 clone/overlay，最终按 patch 或 branch 策略集成。公开源码和不同文档中的设置名称存在差异，落地时须按安装版本核对，不宜盲抄参数。

来源：[Subagents & Agent Hub](https://omp.sh/docs/subagents)、[task 文档](https://github.com/can1357/oh-my-pi/blob/main/docs/tools/task.md)。

Vibe mode 进一步把主会话变成 director：主要读取、检查和协调，把修改与命令执行交给持续存在的 worker。fast/good 是工作和模型路由分层，适合分别处理明确的机械工作与需要判断的设计、调试、审查。worker 保有自己的对话，适合沿同一工作线持续反馈。

这套分工的节省是有条件的：协调、重复上下文和验收本身也消耗模型调用；小改动或依赖紧密的任务可能直接单 Agent 更省。没有找到 Vibe 模式在真实项目中普遍降低总成本的受控实验。

来源：[Vibe mode](https://omp.sh/docs/vibe)、[Model roles](https://omp.sh/docs/roles)。

不要把 Vibe 和 Prewalk 混为一谈：前者持续协调多个 worker，后者是在同一会话中由前一个模型调查、规划，到合适的首次编辑边界再一次性交给另一个模型接手。Prewalk 不等于一直有强模型监督廉价模型。

来源：[固定版本 Prewalk 文档](https://github.com/can1357/oh-my-pi/blob/91afeb4385ad0bb07efef33b877057f8d1fb930b/docs/prewalk.md)。

上下文优化也属于 harness 的工作：把稳定系统提示放在动态项目内容之前以增加缓存复用机会；将较旧历史摘要压缩，或把大型工具结果替换成可恢复的 artifact 引用。缓存收益依赖服务商与前缀稳定性，摘要则有信息损失风险。这些机制不能保证所有模型都能无损地无限续写。

来源：[固定版本 Prompt 组装](https://github.com/can1357/oh-my-pi/blob/91afeb4385ad0bb07efef33b877057f8d1fb930b/docs/system-prompt-customization.md)、[固定版本 Compaction 文档](https://github.com/can1357/oh-my-pi/blob/91afeb4385ad0bb07efef33b877057f8d1fb930b/docs/compaction.md)。

## 为什么会被推荐，以及证据有多强

1. **终端工作流里的原生交互。** 对重度终端用户，工具卡片、diff、文件预览和持久会话能减少切换与滚屏摩擦。机制有协议和实现支撑；“更舒服”仍是个人体验判断。
2. **完整的 coding harness。** 代码导航、调试、任务委派、模型路由、扩展等聚合到同一循环，减少自行拼装的工作。这是功能集成价值，不能直接换算成任务成功率。
3. **能按工作选择模型并改造环境。** omp 支持多服务商和角色路由，可通过 TypeScript 扩展、MCP、SDK/RPC 定制。适合希望拥有工具控制权的开发者。
4. **Hashline 的实验有很强传播力。** 作者展示了仅改变编辑工具就显著改变部分模型成功率和输出 token 的例子，说明 harness 是值得优化的变量。

来源：[omp 概览](https://omp.sh/docs)、[扩展开发](https://omp.sh/docs/extension-authoring)、[SDK](https://omp.sh/docs/sdk)、[编辑实验](https://stencil.so/blog/the-harness-problem)。

Hashline 实验的边界：作者在 React 源码文件上制造机械变异，再要求模型修复；每轮 180 项、3 轮、新会话。当前文章表格显示 16 模型中 14 个相对 patch 提升，Grok 4 Fast 的最佳输出 token 降幅为 61%。这不是 61% 的普遍账单节省，也不是完整软件工程任务中胜过其他产品的证明。表中也有退步：DeepSeek V3.2 相对 patch/replace 均下降，GPT-5.2 Codex 相对 replace 略降且输出 token 增加。

来源：[作者实验的表格与方法](https://stencil.so/blog/the-harness-problem)。

本次还读到真实用户的相反反馈：有人强调 Tern 大幅改善 omp 的体验，也有人认为界面不直观。该讨论只支持“已有用户喜欢或不喜欢”，不能证明多数开发者采用、总体生产率更高或市场占有率领先。

来源：[Hacker News 用户讨论](https://news.ycombinator.com/item?id=50298436)。

## 当前版本与 omp² 必须分开

截至调研时，Tern 官网标记为 closed beta，omp 官网仍预告 omp² soon。作者的 Harness Playbook 明确把当前系统的问题复盘和下一代方案混合讲述，并说明部分方案仍在推进。

Playbook 值得借鉴的架构方向是：以一个可持久化、可回放的会话状态作为权威；界面只是状态投影；策略与执行权限留在 host；长任务、工具、子 Agent 有统一取消和观察机制；provider 差异集中建模。文中的 session DOM、Director stack、Python 扩展与隔离执行边界等，不能一概当成当前 npm 版本已经提供的保证。

来源：[omp 官网](https://omp.sh/)、[Tern 官网](https://stencil.so/tern)、[The Harness Playbook](https://stencil.so/blog/harness-playbook)。

因此需分开看三种持久性：Tern 在窗口退出后维持进程；omp 保存和恢复会话；omp² 希望将更多运行状态统一为可回放的权威状态。这三件事不能相互替代。

## 对采用或自建 Agent 的含义

如果目标是用 Agent 写软件，先在熟悉项目中评价 omp 的单 Agent 表现，再增加一两个边界明确的 worker；Tern 的价值主要由实际交互体验决定。比较时固定模型、任务和验收方式，观察成功率、人工介入、完成时间、总调用费用与恢复体验。

如果目标是开发自己的 Agent 产品，可把 omp SDK/RPC 当执行引擎候选，Tern 当可选客户端。领域工具、权限边界、测试和产品流程仍需自己设计。Tern 的 TSP SDK（Rust/Python/Go/TypeScript）适合为已有 CLI 或 Agent 添加原生交互；Tern 插件则用 Luau，和 omp 的 TypeScript 扩展属于不同层。

来源：[omp SDK](https://omp.sh/docs/sdk)、[Tern SDK](https://github.com/stencil-hq/tern-sdk)、[Tern 插件概览](https://docs.stencil.so/tern/)。

另外，Tern 文档明确将插件视为用户主动信任的代码，能以当前用户权限读写文件、运行程序和访问网络；插件 Luau VM 的稳定性隔离不能当作权限沙箱。这是构建扩展方案时需要明确的边界。

来源：[Trust and Security](https://docs.stencil.so/tern/concepts/security.html)。

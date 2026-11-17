# Kindle 改造与微信读书 APK 可行性调研

调研日期：2026-11-01（Asia/Shanghai）。范围为 Kindle 电子墨水屏阅读器，不含 Fire 平板。依据项目源码、README、发布文档与 GitHub API；未刷机、未安装插件、未登录微信读书。文中的支持状态是这次查阅到的公开证据，不是实机保证。

## 判断

Kindle 确实有 Android 移植，不能概括为“Kindle 不能刷安卓”。但“存在 Android 项目”“有适用于这台设备的刷机包”“能够稳定运行某版微信读书”是三项不同的条件。

本次没有找到适用于第 10 代 Kindle、已验证可日用的 Android 开源 ROM。最接近该目标的是 PlainOS 的 PW4 适配计划；实际可用性仍须核实包、机型和固件。若目的是阅读微信读书，KOReader 加社区插件已有直接路线，可作为当前优先评估对象。这是基于项目文档的建议，尚未进行设备验收。

## 真正涉及 Android 的项目

| 项目 | 查到的证据 | 第 10 代能否据此安装 APK |
| --- | --- | --- |
| [PlainOS](https://fuquan.moe/posts/005-PlainOS-Release-Note.html) | 发布页支持表列 PW3、Voyage 已发布，PW4 为“近期发布”；有 Android 包与双系统制作流程 | PW4 仍缺已发布包证据，Basic KT4 未列支持；ROM 源码和许可证未证实 |
| [CracKDroid 的 PW3 指南](https://github.com/liguobao/kanshan-kindle-crackdroid) | 使用 PW3 专用镜像，提供双启动及 adb 安装阅读器 APK 的步骤 | 只能证明旧机型路线存在，不能用于 PW4/KT4；教程仓库不等于 ROM 源码 |
| [KOSP / Kindle-AOSP](https://github.com/Kindle-AOSP) | 有 Android 设备树、内核、显示相关代码和 U-Boot；早期对象为 KT3/heisenberg | KT3 与第 10 代 KT4 不同，未找到后者适配证据 |

PlainOS 发布文档最近更新标为 2026-08-31，文首仍写仅支持 PW3，表格则已增加 Voyage，存在不同阶段信息并存的情况。没有找到更新的 PW4 发布包可用于消除不确定性。网络上关于 Android 5.1、微信读书 1.9 的报道，本次未由作者版本声明或安装包独立核实，不能据此承诺应用兼容性。[发布文档](https://fuquan.moe/posts/005-PlainOS-Release-Note.html)

KOSP 自己的 Build 0.1 记录提到刷新模式问题、切换 Activity 卡顿 5–15 秒、APK 安装慢或失败，末尾写基本半弃坑。它证明底层开源移植工作确实存在，也说明不能将源码存在解读成成熟产品。[项目状态](https://github.com/Kindle-AOSP/kosp-misc)、[设备树](https://github.com/Kindle-AOSP/android_device_amazon_kindle)

## 重写系统部件和界面的项目

| 项目 | 实际替换或扩展的部分 | 与 APK 的关系 |
| --- | --- | --- |
| [ReKindle](https://github.com/ReKindleOS/ReKindle) | 在浏览器运行的墨水屏网页桌面，提供工具和小游戏；可选实验性全屏启动 | PWA，不是 Android 运行时 |
| [ZenOS](https://github.com/xZenLabs/zen-os) | KOReader 的首页、书库、控制面板、启动器及设置界面 | 界面层，底下仍是 KOReader |
| [SimpleUI](https://github.com/doctorhetfield-cmd/simpleui.koplugin) | KOReader 首页、导航、状态栏和组件 | UI 插件，不提供通用 APK 支持 |
| [Aristotle](https://github.com/piotrkowski/aristotle) | 基于 Plato 的 PW4 阅读器和书库，运行时替代原生 Java 界面 | 原生阅读应用，无 Android 兼容层 |
| [Slate](https://github.com/rituparna-ui/slate) | LuaJIT 直接处理 framebuffer、触摸、控件、墨水屏刷新和小应用 | 自建 UI 栈，目标为 MediaTek 墨水屏平台，不是 APK 框架 |
| [Quill OS，原 InkBox](https://github.com/Quill-OS/quill/wiki) | Alpine Linux + Qt 独立系统，官方支持表中 Kindle 仅列 Touch | 替代 Linux 系统不等于 Android |
| [Alpine Kindle 新实现](https://github.com/adiglase/alpine-kindle) | 通过 chroot 运行 Linux 桌面；项目报告 PW5 真机验证 | 共享宿主内核，不自动具备 Android 能力 |
| [KPM](https://github.com/KindleModding/KPM) / [KindleForge](https://github.com/KindleTweaks/KindleForge) | 安装 Kindle 原生应用和扩展的包管理器/应用商店 | 管理适配 Kindle 的软件包，不是安卓应用商店 |
| [Kindle Browser Patch](https://github.com/PiperKev/KindleBrowserPatch) | 放开浏览器下载类型及协议限制 | 能下载文件与能执行 APK 是两回事 |

Aristotle 的安装文档只支持越狱 PW4、2018 型号 PQ94WIF、固件 5.13.x，并明确标为实验性，其他型号与固件不受支持。休眠接管和电池消耗仍有待验证，不建议为了微信读书选择这个项目。[安装限制](https://github.com/piotrkowski/aristotle/blob/main/docs/install.md)

ReKindle 的普通网页使用无需越狱；可选全屏扩展仍启动 Kindle 自带 Chromium。README 将其标为高度实验性，不能把没有原生窗口边框的外观当作刷入了全新操作系统。[README](https://github.com/ReKindleOS/ReKindle/blob/main/README.md)

Alpine 里也有名叫 `apk` 的包管理器；这是 Alpine Linux 的软件包工具，不是 Android APK 安装器。Waydroid 才是运行 Android 应用的另一类方案，但其宿主内核需要 binder 与 ashmem 或 memfd，桌面安装还涉及 Wayland。本次未找到第 10 代 Kindle 的可复现 Waydroid 适配包。[Waydroid 内核条件](https://docs.waydro.id/debugging/getting-essential-information)、[安装文档](https://docs.waydro.id/usage/install-on-desktops)

## 不刷 Android 的微信读书路线

### KOReader + finlater/weread.koplugin

项目提供书架、公众号、章节或整书下载、阅读进度、阅读时长、书评、划线和想法功能；建议 KOReader 2026.03 及以后。文档的扫码登录流程要求账号先开通微信读书 Skill。它还能把微信读书入口整合进 SimpleUI / ZenUI。因此能组合出更接近专用阅读器的界面，但不等于运行腾讯 APK，也不能默认官方 App 所有功能均可用。[项目说明](https://github.com/finlater/weread.koplugin)

### KOReader + MiuRead（觅阅）

同样是社区 KOReader 插件，提供书架、下载、划线和想法、进度与时长同步，维护正式与测试通道。最新发布仍在修复时间和进度同步；当前 README 也明确区分离线测试与真实微信读书服务验收。应选择正式发布包，实际检查手机与 Kindle 的进度往返、休眠、断网恢复，而非只看菜单能否打开。[项目说明](https://github.com/miumiupy98-art/miuread-koreader)、[发布记录](https://github.com/miumiupy98-art/miuread-koreader/releases)

另查到 [WeRead Desktop](https://github.com/zhangweiii/wereaddesktop.koplugin)，可将微信书架作为 KOReader 桌面，并提供 Kindle 首页直启入口；本次未验证这个较小项目的稳定性，优先比较前两个已有持续维护的插件。

以上是第三方客户端方案，书籍权限取决于账号权益和服务端接口。支持阅读时长或进度同步是项目能力声明，不能理解成已对用户账号验证过、所有书籍均可下载、或能完整替代官方 App。

腾讯确有单独的 Android 墨水屏版，包名 `com.tencent.weread.eink`；这能确认用户想安装的应用类别存在，但不能据此确认老 Android ROM 的登录和新版兼容性。[腾讯的 Google Play 应用页](https://play.google.com/store/apps/details?id=com.tencent.weread.eink&hl=zh)

## 活跃状态快照

以下来自调研时 GitHub API 的 latest release；日期已转换为北京时间。提交频繁不等于功能已通过设备验收。

| 项目 | 最新非预发布版本 / 状态 | 北京时间发布日期 |
| --- | --- | --- |
| [ZenOS](https://api.github.com/repos/xZenLabs/zen-os/releases/latest) | v4.2.0 | 2026-10-16 |
| [SimpleUI](https://api.github.com/repos/doctorhetfield-cmd/simpleui.koplugin/releases/latest) | 3.0.2 | 2026-10-30 |
| [finlater WeRead](https://api.github.com/repos/finlater/weread.koplugin/releases/latest) | v1.6.0 | 2026-10-05 |
| [MiuRead](https://api.github.com/repos/miumiupy98-art/miuread-koreader/releases/latest) | v6.3.8 | 2026-11-01 |
| [Aristotle](https://api.github.com/repos/piotrkowski/aristotle/releases/latest) | v0.1.0 | 2026-10-18 |
| [KindleForge](https://api.github.com/repos/KindleTweaks/KindleForge/releases/latest) | v4.1.0-eol；仓库已归档 | 2026-08-23 |

KindleForge 当前仓库已标注归档，README 说明需要以 KPM 为后端重写、暂无时间表，故不按旧宣传中的活跃应用商店推荐。[仓库状态](https://github.com/KindleTweaks/KindleForge)

## 用户设备核实与后续路径

2026-11-01 用户更换数据线并重新连接后，已通过 USB 设备标识对应表确认：设备为 Kindle 基础款第 10 代（2019），社区简称 KT4 / Kindle Basic 3。它不是 Paperwhite 4，前文的 PlainOS PW4 适配计划不能套用到这台设备。[型号对应表](https://wiki.mobileread.com/wiki/Kindle_Serial_Numbers)

只读获取 `/Volumes/Kindle/system/version.txt`，实际内容为 `Kindle 5.18.1.1.1 (476967 023)`：固件版本 **5.18.1.1.1**，构建标识 **476967 023**。早先连接未枚举、首次挂载读取阻塞均为历史情况；最新重连后固件文件已成功读取。没有更改 Kindle 文件或固件；不在本报告保存完整序列号。

后续建议：

1. 先确认 USB 数据连接，或从设备信息取得完整型号和固件；不为探测兼容性升级固件。
2. 若是 PW4 且坚持腾讯 APK，继续核对 PlainOS 的 PW4 实际发布包、适配说明与恢复方法，现有“近期发布”不足以开始刷机。
3. 若主要目标是读微信书，按实际固件判断越狱可行性，再选择 KOReader 加一个微信读书插件；有需要再加一个 UI 插件。
4. 验收应覆盖扫码登录、目标书籍、翻页残影、手机进度同步、断网及休眠恢复。没有这些实机结果，不宣称已经改造成功。

越狱只开放原系统执行外部代码的能力，不会自动加入 Android 运行时；反过来，社区关于原系统不能直接运行 Android App 的 FAQ，也不能用于否定另行刷入 Android ROM 的路线。[越狱定义](https://kindlemodding.org/jailbreaking/)、[FAQ](https://kindlemodding.org/jailbreaking/Legacy/jailbreak-faq.html)

## 后续实机验证（2026-11-01）

已对 KT4、固件5.18.1.1.1完成 SpiderCat 越狱，读取到 jb.sh 2.5.0 成功标记与管理员权限记录。经 KPM 安装 KOReader 包2026.7.2、MiuRead v6.3.8，安装完成日志与插件文件哈希已核验，自动升级程序的屏蔽状态已核验，临时填充空间已释放。用户已确认扫码登录成功、能够打开微信书籍。该路线保留 Kindle 原系统，并未刷成 Android 或取得通用 APK 支持。用户进一步确认 Kindle 与手机双向进度同步均可接续。离线及休眠恢复未专项测试。私人备份和设备日志保留在本地，不随本报告提交或上传。

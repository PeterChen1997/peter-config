# Immich 放群晖还是飞牛：原件保留群晖

调研日期：2026-10-25。用户确认“feishu NAS”指飞牛 fnOS；两机实际配置与网络尚未知。仓库 README 记载群晖 DS220+，须确认是否仍为当前设备。未发现适用的 AGENTS.md；仓库无既有调研目录，本文保存于 docs/research。

## 判断

**工程建议：飞牛若有明显更强的 CPU、足够内存及本地 SSD，倾向飞牛运行 Immich 与数据库，群晖保存照片、视频原件。若两机性能相近，或优先少维护、少故障点，倾向直接放群晖。** 操作系统品牌本身不能决定性能。

“数据都存群晖”需区分：若仅指原件，上述分工成立；若连数据库等全部持久数据都必须留群晖，建议主服务也放群晖，避免把飞牛的数据库目录映射至共享盘。

| 对比 | 主服务在群晖 | 主服务在飞牛，原件在群晖 |
| --- | --- | --- |
| 工程推断：维护与故障 | 一机、无需跨机挂载，较简单 | 依赖两机、交换机、挂载和权限 |
| 工程推断：处理性能 | 取决于群晖 CPU、内存、磁盘 | 可用飞牛更强的 CPU/GPU、SSD；须看实际硬件 |
| 工程推断：原件访问 | 本地访问 | 扫描、读取原图、转码读取受网络影响 |
| 工程推断：日常浏览 | 取决于本地预览与数据库速度 | 预览、数据库在本地 SSD 可减少跨机读取 |

## 官方事实与部署边界

1. **数据库目录不能放网络共享。** 官方要求 Postgres 数据目录使用支持 Unix 权限的文件系统，理想介质为本地 SSD，明确排除所有网络共享。当前最低内存 6GB、推荐 8GB；4GB 可关闭 ML 运行；CPU 最低 2 核、推荐 4 核。这是整机资源规划依据，不能把原厂内存等同于用户现有内存。[Immich requirements](https://docs.immich.app/install/requirements/)

2. **原件可以远程挂载。** 群晖提供 NFS 与 SMB；Immich FAQ 给出 CIFS/Samba Docker volume 示例，外部库文档给出宿主机 NAS 路径映射。飞牛官方确认“文件管理 > 远程挂载”，但未承诺其用户挂载自动对 Docker 可见，必须从容器内验证路径与读写权限。[群晖 NFS](https://kb.synology.com/index.php/en-us/DSM/help/DSM/AdminCenter/file_winmacnfs_nfs?version=7)、[群晖 SMB](https://kb.synology.com/en-global/DSM/help/DSM/AdminCenter/file_winmacnfs_win)、[Immich FAQ](https://docs.immich.app/FAQ/)、[飞牛权限说明](https://help.fnnas.com/articles/v1/contact/user-role)

3. **缩略图、转码视频可独立放盘。** 当前官方示例将 NAS/HDD 基础目录挂至容器 `/data`，再用本地目录覆盖 `/data/thumbs`、`/data/encoded-video` 等。小缩略图与大预览均在 thumbs，不能拆开；须另行监控各盘容量。[自定义存储位置](https://docs.immich.app/guides/custom-locations/)

4. **已有照片与手机新备份分开考虑。** 已有群晖目录可作为 External Library，不必复制进内部库；`:ro` 防止 Immich 修改、删除原件，也不能向目录写入 XMP。手机通过 Immich 上传的新照片进入内部库，须把 UPLOAD_LOCATION 指向群晖挂载才能让原件落在群晖。网络盘不要依赖实验性 watcher，采用定时扫描。[外部库](https://docs.immich.app/features/libraries/)、[扫描设置](https://docs.immich.app/administration/system-settings/)、[快速开始](https://docs.immich.app/overview/quick-start/)

5. **挂载检查有边界。** 启动时 `.immich` 标记检查覆盖内部 upload、library、thumbs、encoded-video、profile、backups；失败会阻止启动。官方没有在此承诺所有外部库或运行中断连均受同等保护。工程建议在启动及扫描前验证真正的共享挂载、目录与权限，演练断连和重启，不靠创建空目录或关闭检查绕过。[系统完整性](https://docs.immich.app/administration/system-integrity/)

6. **远程 ML 是可选折中。** 群晖保留主服务，飞牛只跑 ML，可卸载智能搜索与人脸检测；人脸识别仍在主服务与数据库侧，视频转码也不会因此搬走。远程 ML 接收预览图，无内置认证，应限内网，版本与主服务同步。[远程机器学习](https://docs.immich.app/guides/remote-machine-learning/)

7. **沿用官方 Compose。** Immich 要求 `docker compose` 插件；群晖 Container Manager Project 可导入与维护 Compose YAML。飞牛官方确认 Docker 能力，但本次未找到足够具体的官方 Compose 专文，不据社区一键模板推断长期兼容性。[群晖项目管理](https://kb.synology.com/en-global/DSM/help/ContainerManager/docker_project)、[飞牛 Docker 能力](https://help.fnnas.com/articles/v1/settings/authorize)

核查时官方最新版本为 **v3.3.5**；部署时重新检查 release 与对应 Compose，不照搬旧教程容器路径或数据库镜像。[官方 release](https://github.com/immich-app/immich/releases/tag/v3.3.5)

## 下一步需要的信息

确认群晖是否 DS220+、实际内存；飞牛 CPU、内存、SSD；两机有线网络；照片数量与视频占比。若属 DS220+ 原厂配置，官方规格为 J4025 双核、2GB 内存，其原厂内存低于当前 Immich 最低要求；实际扩容须另查。[群晖官方规格](https://global.download.synology.com/download/Document/Hardware/ProductSpec/DiskStation/20-year/DS220%2B/enu/Product_Spec_DS220%2B_enu.pdf)

数据库与原件应一起纳入备份：Immich 自动数据库备份不等于照片文件备份；原件留群晖也不等于已有独立副本。[备份与恢复](https://docs.immich.app/administration/backup-and-restore/)

# 家庭网络分流方案

> 现网交接（2026-10-25）：本文保留历史方案及生成工作流，不能作为路由器当前运行配置的依据。本机最新链路、浏览器修复和验证边界见 `inno/network-inventory/CURRENT.md`，访问入口见同目录 `ACCESS.md`；agent 先读仓库根目录 [AGENTS.md](../../AGENTS.md)。私有档案不随公开仓库分发。
>
> 更新于 2026-10-11。家庭端的新工作流和导入步骤见 [双订阅自动更新](openclash/AUTO_UPDATE.md)。
> iPhone Stash 部分仍是旧方案；本次未改动手机配置。

## 一、设计目标

出口资源的成本模型决定分流原则：

| 出口 | 资源 | 特点 | 定位 |
|------|------|------|------|
| **美国静态住宅** | EqualVPN「专属纯净静态住宅节点」 | IP 纯净稳定、风控友好，但额度贵 | 风控敏感服务（AI 厂商）+ 国外流量默认兜底 |
| **便宜大流量** | 华云 IEPL 专线（100+ 节点）+ EqualVPN 赠送娱乐节点（独立 80GB 娱乐流量） | 便宜、量大、速度好，IP 质量一般 | 流量大户：视频 / 社交媒体 / 大文件下载 |
| **自建 VLESS** | 23.95.196.34（美国 ColoCrossing） | 完全可控 | 住宅节点故障时的手动兜底（Stash 端已内置） |
| **直连** | 家宽 | — | 国内全部 + Apple + 代理节点端点 |

**核心原则（反向筛选）**：不维护「哪些走美国口」的白名单，而是维护「哪些是流量大户」的黑名单。
命中大流量规则 → 便宜出口；国内 → 直连；**其余国外流量默认全走住宅**。这样新出现的 AI/小众服务
天然落在高质量出口上，不会因为规则滞后被 AI 厂商识别到低质量 IP 导致账号风险。

## 二、架构

```
                     ┌──────────────────────────────────────────────┐
                     │  规则源（单一事实来源，GitHub 本仓库 + bm7）  │
                     │  rule-providers/*.yaml   blackmatrix7 规则集  │
                     └───────────────┬──────────────────────────────┘
                          每 24h 自动拉取（两端一致）
              ┌──────────────────────┴──────────────────────┐
              ▼                                             ▼
  家庭：UniFi 主路由 → Ser8 旁路由                 外出：iPhone Stash
  OpenClash(peter-home.yaml) + 双 HTTP provider          stash/stash.yaml 完整配置
  + AdGuard Home（广告）                           （规则内含广告 REJECT）
              │                                             │
              └────────────┬────────────────┬───────────────┘
                           ▼                ▼
                    AI 专线（住宅）    大流量（华云+娱乐）    其余国内 → 直连
```

手机在家庭 Wi-Fi 下开着 Stash 也不会双重代理：节点服务器端点已加入 `direct-rules.yaml`，
旁路由对 Stash 的隧道流量直接放行。

## 三、策略组（两端同名）

| 策略组 | 类型 | 节点来源 | 用途 |
|--------|------|----------|------|
| `AI 专线` | select | `住宅节点`（EqualVPN 订阅按 `住宅\|静态` 筛选） | AI 厂商 + 强制代理杂项；供大流量手动选择 |
| `大流量自动`（新家庭配置） | url-test | 花云实际节点 + EqualVPN 娱乐节点，300s 健康检查 | 只自动选优便宜节点，全失效也不选住宅 |
| `大流量` | select | 默认跟随`大流量自动`，可手动选择 `AI 专线`、花云地区或单节点 | 流量大户出口 |
| `国外兜底`（Stash）/ `国外兜底`（新 OpenClash 配置，默认=AI 专线） | select | — | MATCH 兜底 |

> 组名刻意不带 emoji：OpenClash 的 ruby 覆写注入会把 emoji 转义成 `\Uxxxxxx`，导致规则匹配不到策略组。

## 四、规则链（顺序即优先级）

1. 局域网 / 私有地址 → `DIRECT`
2. 广告 → `REJECT`（家里 AdGuard Home 负责，Stash 规则覆盖蜂窝场景）
3. `peter-direct` → `DIRECT`（国内 CDN、Apple、代理节点端点）
4. `peter-ai` + `bm7-openai/claude/gemini` → `AI 专线`
5. `peter-proxy` → `AI 专线`（强制代理杂项：开发/设计/支付工具）
   （4、5 **必须在媒体规则之前**：实测 cursor.sh、claudeusercontent.com 会被宽泛的媒体规则集误伤）
6. `bm7-youtube/netflix/tiktok/spotify/twitter/instagram/telegram/speedtest` → `大流量`
   （**刻意不用 bm7-globalmedia**：它会把开发工具、S3 桶等非媒体域名误分类去大流量）
7. `peter-heavy` → `大流量`（自维护流量大户：容器镜像、HuggingFace 等）
8. `GEOSITE,CN` / `GEOIP,CN` → `DIRECT`
9. `MATCH` → 住宅（质量优先兜底）

## 五、部署

### OpenWrt / OpenClash

采用 [openclash/AUTO_UPDATE.md](openclash/AUTO_UPDATE.md) 的长期方案：

1. `openclash/home-template.yaml` 定义分流与 provider，`openclash/build_config.py` 从本地私有 sources 生成 `peter-home.yaml`。
2. EqualVPN 和花云都作为 HTTP provider，每小时更新。花云使用原始订阅，绕开实测返回 403 的转换器；网页开关仍需浏览器，尚未自动化。
3. 导入前备份当前配置并停用旧注入脚本/额外规则覆写；保留现有 OpenClash 旁路由 DNS、防火墙、TUN 管理。
4. 使用 `openclash/check_providers.py` 查看实际更新时间，以及自动池排除住宅、手动 AI 入口是否存在。
5. 此次配置和隔离内核测试已完成；尚未应用到路由器，最终需在路由器自己的网络出口验证更新和分流。

`custom_overwrite.sh` 保留旧部署兼容，并加入了“便宜节点自动选优、AI 专线仅手动选择”的组结构。
它对 `peter-home.yaml` 跳过注入；新的长期配置不再依赖此脚本组装。

### iPhone / Stash

1. 把 `stash/stash.yaml` 中 `EQUALVPN_SUB_URL` / `HUAYUN_SUB_URL` 换成真实订阅链接。
2. 导入 Stash（文件导入或 iCloud 同步）。若 equalvpn 订阅被 Cloudflare 挡住，
   把 `config/equalvpn.yaml` 的 proxies 段内联进配置并注释掉该 provider。
3. 旧的 `config/home.yaml` 已被本配置取代。

## 六、验证清单

- [ ] `chat.openai.com` / `claude.ai` → YACD/Stash 里显示走 `AI 专线`，[browserleaks.com/ip](https://browserleaks.com/ip) 显示住宅 IP
- [ ] `x.com` / YouTube 视频 → 走 `大流量`
- [ ] 淘宝 / 微信 → `DIRECT`
- [ ] 手机在家庭 Wi-Fi 开 Stash，路由器连接页里 Stash 节点端点显示 `DIRECT`（无双重代理）
- [ ] 住宅节点流量消耗明显下降（各家后台流量统计对比）

## 七、维护 SOP

**发现新的流量大户**（保护住宅额度，建议每 1–2 周看一次）：

1. Mac 上有 launchd 定时采集（`~/Library/LaunchAgents/cn.peterchen97.clash-traffic.plist`，
   每 10 分钟采样 4 分钟，JSONL 落在 `inno/traffic-logs/`）。直接看历史汇总：
   ```bash
   export CLASH_API_SECRET=<OpenClash 管理页面密码>
   python3 config/clash/clash_traffic.py report 7    # 最近 7 天，按出口分组
   ```
   报告把「走住宅但流量大」的域名单独列出，就是优化候选。
   临时看实时情况用 `poll 300` / 无参数快照；或 OpenClash「连接」页人工看。
2. 非 AI/风控敏感的候选加进 `rule-providers/heavy-rules.yaml`，push 后两端最迟 24h 生效
   （用 API `PUT /providers/rules/peter-heavy` 或重启可立即生效）。

**新 AI 服务上线**：什么都不用做（兜底就是住宅）。只有当它被媒体/大流量规则误伤时，才加进 `ai-rules.yaml`。

**订阅换节点后**：新生成器会把本次节点端点直连规则放在主配置最前，但这是构建时快照。provider 自动换节点不会更新这份快照；手机在家使用新的服务器端点时，重新生成配置或更新 `direct-rules.yaml`，避免双重代理。

**规则冲突排查**：记住优先级=顺序，YACD 的 Rules 页可搜域名看命中哪条。

# clash 规则管理

> **分流策略总方案见 [ROUTING.md](./ROUTING.md)**（双出口：美国静态住宅 = AI/兜底，华云+娱乐节点 = 大流量）。

## 当前架构

家庭长期方案见 [双订阅自动更新工作流](openclash/AUTO_UPDATE.md)。一份 `peter-home.yaml` 管理分流，
EqualVPN 与花云分别作为 HTTP provider 每小时刷新；花云直接使用原始订阅，绕开实测 403 的转换器。
「大流量自动」只测速便宜节点；「大流量」允许手动选择「AI 专线」。
花云的网页开关操作尚未自动化，路由器定时下载不能代替浏览器步骤。

```text
EqualVPN 原始订阅 → 住宅节点 → AI 专线
                → 娱乐节点 ┐
花云原始订阅 → 全部实际节点 ┴→ 大流量自动（仅便宜节点）→ 大流量（可手动选 AI 专线）
仓库 + bm7 规则 → 每 24h 更新分流
```

本次已生成私有导入配置并在隔离 mihomo 内核测试；路由器仍是旧部署，尚未切换。
`openclash/custom_overwrite.sh` 保留兼容旧方式；iPhone Stash 仍使用原有方案，本次未迁移。

## 订阅服务商

| 服务商 | 用途 | 购买链接（带推荐码） |
|--------|------|----------------------|
| EqualVPN（eplayai） | 美国静态住宅节点：AI 专线 / 国外兜底 | https://www.eplayai.com/?ref=8cab4dbc55 |
| 花云 FlowerCloud（huayun） | IEPL 专线：大流量出口 | https://api-flowercloud.com/aff.php?aff=11280 |

> 这里只放公开的购买/推荐链接；真实订阅 URL 含 token，**不要**提交进仓库（仓库是公开的）。

## 文件结构

| 文件 | 用途 |
|------|------|
| `ROUTING.md` | **分流方案文档**：策略组、规则链、部署与维护 SOP |
| `rule-providers/ai-rules.yaml` | **当前生效**：AI 补充规则 → AI 专线（住宅） |
| `rule-providers/heavy-rules.yaml` | **当前生效**：大流量补充规则 → 便宜出口 |
| `rule-providers/proxy-rules.yaml` | **当前生效**：强制代理杂项 → AI 专线（住宅） |
| `rule-providers/direct-rules.yaml` | **当前生效**：直连规则（国内 CDN / Apple / 节点端点） |
| `openclash/home-template.yaml` | 新长期主配置模板：双订阅、分类、便宜节点优先和住宅兜底 |
| `openclash/build_config.py` | 从私有订阅 URL 生成可导入的配置和首启缓存 |
| `openclash/check_providers.py` | 检查实际更新时间；可请求立即刷新 |
| `openclash/AUTO_UPDATE.md` | 生成、导入、回滚、更新限制与验证步骤 |
| `openclash/custom_overwrite.sh` | 兼容旧注入方式；对新主配置跳过注入 |
| `openclash/peter_github_rules.rb` | 现网注入脚本：把本仓库四个规则集接入路由器当前配置（不建策略组）|
| `openclash/daily_review.py` | 网关审阅：按实际出口列出规则候选和走代理的流量大户 |
| `stash/stash.yaml` | Stash 完整配置（`config/home.yaml` 已被它取代） |
| `stash/README.md` | 手机端怎么同步规则、节点和配置骨架 |
| `stash/build_stash.py` | 从模板 + 本机私有订阅 / 节点生成手机可导入的配置 |
| `clash_traffic.py` | 流量画像工具：轮询 Clash API 按域名聚合流量，找流量大户（用法见 ROUTING.md） |
| `proxy.list` | 需要走代理的自定义规则（subconverter 模板引用，备用） |
| `direct.list` | 需要直连的自定义规则（subconverter 模板引用，备用） |
| `clash-template.ini` | subconverter 模板（备用） |

## 添加新规则

### 方式一：直接编辑 rule-providers（推荐，当前生效）

编辑 `rule-providers/proxy-rules.yaml` 或 `rule-providers/direct-rules.yaml`，push 到 GitHub 后最迟 24h 生效，重启 OpenClash 可立即生效。

### 方式二：用脚本追加到 proxy.list / direct.list

```bash
# 预览，不写入
python config/clash/update_proxy_list.py --dry-run https://example.com/path

# 添加 URL / 域名 / IP
python config/clash/update_proxy_list.py https://example.com/path openai.com 1.2.3.4

# 强制规则类型
python config/clash/update_proxy_list.py --type DOMAIN-KEYWORD cursor
python config/clash/update_proxy_list.py --type DOMAIN-SUFFIX example.com
python config/clash/update_proxy_list.py --type IP-CIDR 1.2.3.4/32

# 加注释
python config/clash/update_proxy_list.py --comment "AI tools" anthropic.com openai.com
```

默认规则推断：URL/域名 → `DOMAIN-SUFFIX`，IP → `IP-CIDR/32`，普通关键词 → `DOMAIN-KEYWORD`

## OpenClash Overwrite Script

在 OpenClash → Overwrite Settings → Rules Setting → Custom Config Overwrite Scripts 中配置，脚本内容见仓库 wiki 或博客文章。

旧部署方式：注入家庭策略组和规则集。新 `peter-home.yaml` 已包含这些内容，必须避免旧脚本重复覆写。

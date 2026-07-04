# clash 规则管理

> **分流策略总方案见 [ROUTING.md](./ROUTING.md)**（双出口：美国静态住宅 = AI/兜底，华云+娱乐节点 = 大流量）。

## 当前架构

```
VPN 订阅（equalvpn）
  → OpenClash 原生拉取（绕过 Cloudflare 限制）
    → 覆写脚本 openclash/custom_overwrite.sh 注入策略组 + rule-providers
      → clash.meta 从 GitHub 拉取自定义规则（每 24h 自动刷新）

iPhone Stash → stash/stash.yaml（同一套规则源，独立完整配置）
```

> subconverter 服务（sub.hweb.peterchen97.cn）仍在运行，但当前订阅有 Cloudflare 验证，subconverter 无法直接拉取节点，暂时绕过。若以后切换到无验证的订阅，可重新接入。

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
| `openclash/custom_overwrite.sh` | OpenClash 覆写脚本（注入策略组 + 全部 rule-providers） |
| `stash/stash.yaml` | Stash 完整配置（`config/home.yaml` 已被它取代） |
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

作用：每次配置加载后自动注入 `peter-proxy` 和 `peter-direct` 两个 rule-provider，并插到所有订阅规则之前。

# clash 规则管理

## 当前架构

```
VPN 订阅（equaldcdn）
  → OpenClash 原生拉取（绕过 Cloudflare 限制）
    → Overwrite Script 注入 rule-providers
      → clash.meta 从 GitHub 拉取自定义规则（每 24h 自动刷新）
```

> subconverter 服务（sub.hweb.peterchen97.cn）仍在运行，但当前订阅有 Cloudflare 验证，subconverter 无法直接拉取节点，暂时绕过。若以后切换到无验证的订阅，可重新接入。

## 文件结构

| 文件 | 用途 |
|------|------|
| `proxy.list` | 需要走代理的自定义规则（subconverter 模板引用） |
| `direct.list` | 需要直连的自定义规则（subconverter 模板引用） |
| `rule-providers/proxy-rules.yaml` | **当前生效**：clash.meta rule-provider 格式，代理规则 |
| `rule-providers/direct-rules.yaml` | **当前生效**：clash.meta rule-provider 格式，直连规则 |
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

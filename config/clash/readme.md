# clash

部署阶段转换服务，需要保证对应 server 的网络情况正常，可以考虑部署在 openwrt 中。

## 结构

1. openwrt
2. openclash
3. subconvert
4. adguardhome

## 家庭代理列表维护

`proxy.list` 是家庭网络需要走代理的自定义规则列表，已被 `clash-template.ini` 远程引用。

用脚本追加规则：

```bash
# 预览，不写入
python config/clash/update_proxy_list.py --dry-run https://example.com/path

# 添加 URL / 域名 / IP，默认追加到 config/clash/proxy.list
python config/clash/update_proxy_list.py https://example.com/path openai.com 1.2.3.4

# 强制规则类型
python config/clash/update_proxy_list.py --type DOMAIN-KEYWORD cursor
python config/clash/update_proxy_list.py --type DOMAIN-SUFFIX example.com
python config/clash/update_proxy_list.py --type DOMAIN api.example.com
python config/clash/update_proxy_list.py --type IP-CIDR 1.2.3.4/32

# 给一组新增规则加注释
python config/clash/update_proxy_list.py --comment "dev tools" replit.com cursor.com
```

默认规则：

- URL / 域名 → `DOMAIN-SUFFIX,<hostname>`，例如 `https://foo.example.com/a` → `DOMAIN-SUFFIX,foo.example.com`
- IP → `IP-CIDR,<ip>/32`
- CIDR → `IP-CIDR,<cidr>`
- 普通关键词 → `DOMAIN-KEYWORD,<keyword>`

脚本会保留现有顺序，自动跳过重复规则。

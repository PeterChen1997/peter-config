#!/bin/sh
# OpenClash 自定义覆写脚本 —— peter 家庭分流（详见 config/clash/ROUTING.md）
#
# 用途：在 OpenClash 每次加载订阅配置（equalvpn）后，自动注入：
#   1. 华云订阅（可选，作为 proxy-provider）
#   2. 三个策略组：AI 专线 / 大流量 / 大流量自动
#   3. 16 个 rule-provider（本仓库自维护 4 个 + blackmatrix7 12 个）
#   4. 分流规则，插在订阅自带规则之前
#
# 部署位置（二选一）：
#   - LuCI: OpenClash → 覆写设置 → 开发者选项 → 自定义覆写脚本，粘贴本文件内容
#   - SSH:  写入 /etc/openclash/custom/openclash_custom_overwrite.sh
#
# 注意：
#   - 策略组名刻意不带 emoji（OpenClash ruby 注入会把 emoji 转义成 \Uxxxxxx，导致规则匹配不到策略组）
#   - 首次启动时 OpenClash 可能弹出"未找到策略组"的假警告（覆写发生在校验之后），可忽略

. /usr/share/openclash/ruby.sh
. /usr/share/openclash/log.sh
. /lib/functions.sh

CONFIG_FILE="$1"

# 花云订阅链接（填 api-huacloud.net 转换器的完整 URL，在 LuCI 里填真实值，不要提交进仓库）。
# 留空则「大流量」组只使用 EqualVPN 赠送的娱乐节点（独立 80GB 娱乐流量）。
# 注意：花云订阅的 Cloudflare 只放行浏览器 UA，下面 provider 注入了浏览器 UA header（mihomo 支持）
HUAYUN_SUB_URL=""
BROWSER_UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

PETER_RAW="https://raw.githubusercontent.com/PeterChen1997/peter-config/master/config/clash/rule-providers"
BM7_RAW="https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash"

LOG_OUT "Overwrite: 注入 peter 家庭分流（AI 专线 / 大流量）..."

# ---------- 0. 确保顶级键存在（equalvpn 原始配置没有 rule-providers / proxy-providers） ----------
[ -z "$(ruby_read "$CONFIG_FILE" "['rule-providers']")" ] && ruby_edit "$CONFIG_FILE" "['rule-providers']" "{}"

# ---------- 1. 华云订阅（可选 proxy-provider） ----------
if [ -n "$HUAYUN_SUB_URL" ]; then
   [ -z "$(ruby_read "$CONFIG_FILE" "['proxy-providers']")" ] && ruby_edit "$CONFIG_FILE" "['proxy-providers']" "{}"
   ruby_merge_hash "$CONFIG_FILE" "['proxy-providers']" "'huayun'=>{'type'=>'http','url'=>'$HUAYUN_SUB_URL','path'=>'./proxy_provider/huayun.yaml','interval'=>43200,'header'=>{'User-Agent'=>['$BROWSER_UA']},'health-check'=>{'enable'=>true,'url'=>'http://www.gstatic.com/generate_204','interval'=>600}}"
fi

# ---------- 2. 策略组（插到最前，include-all 同时覆盖订阅节点和 provider 节点） ----------
# AI 专线：只允许静态住宅节点，风控敏感流量 + 国外兜底走这里
ruby_arr_insert_hash "$CONFIG_FILE" "['proxy-groups']" "0" "{'name'=>'AI 专线','type'=>'select','include-all'=>true,'filter'=>'住宅|静态'}"
# 大流量自动：华云 IEPL + EqualVPN 娱乐节点里自动测速选优
ruby_arr_insert_hash "$CONFIG_FILE" "['proxy-groups']" "1" "{'name'=>'大流量自动','type'=>'url-test','include-all'=>true,'filter'=>'IEPL|娱乐','url'=>'http://www.gstatic.com/generate_204','interval'=>300,'tolerance'=>50}"
# 大流量：手动开关，默认跟随自动选优
ruby_arr_insert_hash "$CONFIG_FILE" "['proxy-groups']" "2" "{'name'=>'大流量','type'=>'select','proxies'=>['大流量自动'],'include-all'=>true,'filter'=>'IEPL|娱乐'}"

# ---------- 3. rule-providers ----------
add_rp() {
   ruby_merge_hash "$CONFIG_FILE" "['rule-providers']" "'$1'=>{'type'=>'http','behavior'=>'classical','format'=>'yaml','url'=>'$2','path'=>'./rule_provider/$1.yaml','interval'=>86400}"
}

# 本仓库自维护
add_rp "peter-direct"    "$PETER_RAW/direct-rules.yaml"
add_rp "peter-ai"        "$PETER_RAW/ai-rules.yaml"
add_rp "peter-heavy"     "$PETER_RAW/heavy-rules.yaml"
add_rp "peter-proxy"     "$PETER_RAW/proxy-rules.yaml"
# blackmatrix7（No_Resolve 版本：IP 规则不触发提前 DNS 解析）
add_rp "bm7-openai"      "$BM7_RAW/OpenAI/OpenAI_No_Resolve.yaml"
add_rp "bm7-claude"      "$BM7_RAW/Claude/Claude_No_Resolve.yaml"
add_rp "bm7-gemini"      "$BM7_RAW/Gemini/Gemini_No_Resolve.yaml"
add_rp "bm7-youtube"     "$BM7_RAW/YouTube/YouTube_No_Resolve.yaml"
add_rp "bm7-netflix"     "$BM7_RAW/Netflix/Netflix_No_Resolve.yaml"
add_rp "bm7-tiktok"      "$BM7_RAW/TikTok/TikTok_No_Resolve.yaml"
add_rp "bm7-spotify"     "$BM7_RAW/Spotify/Spotify_No_Resolve.yaml"
add_rp "bm7-twitter"     "$BM7_RAW/Twitter/Twitter_No_Resolve.yaml"
add_rp "bm7-instagram"   "$BM7_RAW/Instagram/Instagram_No_Resolve.yaml"
add_rp "bm7-telegram"    "$BM7_RAW/Telegram/Telegram_No_Resolve.yaml"
add_rp "bm7-globalmedia" "$BM7_RAW/GlobalMedia/GlobalMedia_Classical_No_Resolve.yaml"
add_rp "bm7-speedtest"   "$BM7_RAW/Speedtest/Speedtest_No_Resolve.yaml"

# ---------- 4. 分流规则（插到订阅规则之前；顺序即优先级） ----------
# 直连 → AI（先于媒体，防止 Google 系 AI 域名被媒体规则误伤）→ 大流量 → 强制代理杂项
# 订阅自带规则随后生效：广告 REJECT / GEOSITE,CN 直连 / GEOIP,CN 直连 / MATCH,EqualVPN（组内默认=住宅）
ruby_arr_insert_arr "$CONFIG_FILE" "['rules']" "0" "['RULE-SET,peter-direct,DIRECT','RULE-SET,peter-ai,AI 专线','RULE-SET,bm7-openai,AI 专线','RULE-SET,bm7-claude,AI 专线','RULE-SET,bm7-gemini,AI 专线','RULE-SET,bm7-youtube,大流量','RULE-SET,bm7-netflix,大流量','RULE-SET,bm7-tiktok,大流量','RULE-SET,bm7-spotify,大流量','RULE-SET,bm7-twitter,大流量','RULE-SET,bm7-instagram,大流量','RULE-SET,bm7-telegram,大流量','RULE-SET,bm7-globalmedia,大流量','RULE-SET,bm7-speedtest,大流量','RULE-SET,peter-heavy,大流量','RULE-SET,peter-proxy,AI 专线']"

LOG_OUT "Overwrite: peter 家庭分流注入完成"

exit 0

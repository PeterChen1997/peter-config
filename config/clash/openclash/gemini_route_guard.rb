# OpenClash 覆写后执行（排在其他注入脚本之后）：Gemini 域名规则放到最前，交给 Google 组。
#
# 原因（2026-10-26）：Google 把 Lisa 出口判定为中国大陆，Gemini 报 "User location is not supported"。
# Google 组默认走 Gemini-US（花云美国节点）；这些域名若落到 peter-ai → OpenAI 组会回到 Lisa。
#
# 部署：/etc/openclash/custom/gemini_route_guard.rb，由 openclash_custom_overwrite.sh 最后调用：
#   ruby /etc/openclash/custom/gemini_route_guard.rb "$1"
# 配置里没有 Google 组时不做任何事；可重复执行。
require 'yaml'

path = ARGV[0]
exit 0 unless path && File.file?(path)
d = YAML.load_file(path)
exit 0 unless d.is_a?(Hash)
exit 0 unless (d['proxy-groups'] || []).any? { |g| g['name'] == 'Google' }

domains = %w[generativelanguage.googleapis.com aistudio.google.com gemini.google.com makersuite.google.com
             alkalimakersuite-pa.clients6.google.com notebooklm.google.com bard.google.com]
gemini = domains.map { |dom| "DOMAIN-SUFFIX,#{dom},Google" }

rules = (d['rules'] ||= [])
rules.reject! { |r| gemini.include?(r) }
rules.unshift(*gemini)

mode = File.stat(path).mode & 0o777
File.write(path, d.to_yaml)
File.chmod(mode & 0o770, path)

# OpenClash 覆写后执行：把本仓库 rule-providers 注入当前配置，GitHub 作为规则的唯一来源。
#
# 部署：/etc/openclash/custom/peter_github_rules.rb，由 openclash_custom_overwrite.sh 调用：
#   ruby /etc/openclash/custom/peter_github_rules.rb "$1"
# 只依赖配置里已有的 Proxies 组（OpenAI 组存在时 AI 规则走它），不创建策略组；可重复执行。
require 'yaml'

path = ARGV[0]
exit 0 unless path && File.file?(path)
d = YAML.load_file(path)
exit 0 unless d.is_a?(Hash)
groups = (d['proxy-groups'] || []).map { |g| g['name'] }
exit 0 unless groups.include?('Proxies')

raw = 'https://raw.githubusercontent.com/PeterChen1997/peter-config/master/config/clash/rule-providers'
sets = [
  ['peter-direct', 'direct-rules.yaml', 'DIRECT'],
  ['peter-ai', 'ai-rules.yaml', groups.include?('OpenAI') ? 'OpenAI' : 'Proxies'],
  ['peter-proxy', 'proxy-rules.yaml', 'Proxies'],
  ['peter-heavy', 'heavy-rules.yaml', 'Proxies']
]

providers = (d['rule-providers'] ||= {})
sets.each do |name, file, _|
  # 经 Proxies 下载：raw.githubusercontent.com 在国内直连不稳定
  providers[name] = { 'type' => 'http', 'behavior' => 'classical', 'format' => 'yaml',
                      'url' => "#{raw}/#{file}", 'path' => "./rule_provider/#{name}.yaml",
                      'interval' => 86400, 'proxy' => 'Proxies' }
end

# 规则集里的 IP 规则都带 no-resolve；RULE-SET 行也加上，避免在规则链最前面触发 DNS 解析
rules = (d['rules'] ||= [])
rules.reject! { |r| r.start_with?('RULE-SET,peter-') }
anchor = rules.index('DOMAIN-SUFFIX,metamask.io,Proxies')
rules.insert(anchor ? anchor + 1 : 0, *sets.map { |name, _, target| "RULE-SET,#{name},#{target},no-resolve" })

mode = File.stat(path).mode & 0o777
File.write(path, d.to_yaml)
File.chmod(mode & 0o770, path)

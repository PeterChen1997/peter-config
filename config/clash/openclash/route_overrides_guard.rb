# OpenClash 覆写后执行（排在其他注入脚本之后）：少量必须压过 peter-* 规则集的分流，放到规则最前。
#
# 1) Gemini → Google 组（2026-10-26）：Google 把 Lisa 出口判定为中国大陆，Gemini 报
#    "User location is not supported"。Google 组默认走 Gemini-US（花云美国节点）；
#    这些域名若落到 peter-ai → OpenAI 组会回到 Lisa。
# 2) Apple 上传 → Upload 组（2026-10-26）：peter-direct 把 apple.com 整体直连，altool/Xcode 往
#    北美对象存储上传只有约 100KB/s；花云 IEPL 实测约 2–3 倍。只接管上传域名，其余 Apple 仍直连。
#    Fly 镜像推送（registry.fly.io）和 depot 远程构建器原本落到 Final → Lisa，上行约 75KB/s，
#    大层推不完；同样交给 Upload 组。
#
# 部署：/etc/openclash/custom/route_overrides_guard.rb，由 openclash_custom_overwrite.sh 最后调用：
#   ruby /etc/openclash/custom/route_overrides_guard.rb "$1"
# 对应策略组不存在时跳过那一组规则；可重复执行。
require 'yaml'

path = ARGV[0]
exit 0 unless path && File.file?(path)
d = YAML.load_file(path)
exit 0 unless d.is_a?(Hash)
groups = (d['proxy-groups'] || []).map { |g| g['name'] }

overrides = {
  'Google' => %w[generativelanguage.googleapis.com aistudio.google.com gemini.google.com makersuite.google.com
                 alkalimakersuite-pa.clients6.google.com notebooklm.google.com bard.google.com],
  'Upload' => %w[object-storage.apple.com contentdelivery.itunes.apple.com registry.fly.io depot.dev]
}
all = overrides.flat_map { |group, domains| domains.map { |dom| "DOMAIN-SUFFIX,#{dom},#{group}" } }
wanted = overrides.select { |group, _| groups.include?(group) }
                  .flat_map { |group, domains| domains.map { |dom| "DOMAIN-SUFFIX,#{dom},#{group}" } }

rules = (d['rules'] ||= [])
rules.reject! { |r| all.include?(r) }
rules.unshift(*wanted)

mode = File.stat(path).mode & 0o777
File.write(path, d.to_yaml)
File.chmod(mode & 0o770, path)

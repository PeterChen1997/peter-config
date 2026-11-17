# Apply the opt-in two-group home topology after OpenClash's own overwrites.
# Credentials/topology remain in a local-only router configuration, never this repo.
require 'yaml'
path = ARGV[0]
exit 0 unless path && File.file?(path)
data = YAML.load_file(path)
exit 0 unless data.is_a?(Hash)
exit 0 unless File.basename(path) == 'Home-Auto.yaml' || data['x-home-simple-routing'] == true
settings = '/etc/openclash/custom/simple-routing.PRIVATE.yaml'
raise 'Missing local simple-routing settings' unless File.file?(settings)
overlay = YAML.load_file(settings)
%w[proxies proxy-providers proxy-groups rule-providers rules].each do |key|
  raise "Missing routing section: #{key}" unless overlay.key?(key)
  data[key] = overlay[key]
end
data['ipv6'] = false
(data['dns'] ||= {})['ipv6'] = false
data['dns']['proxy-server-nameserver'] = ['127.0.0.1:5335']
(data['profile'] ||= {})['store-fake-ip'] = true
data['profile']['store-selected'] = false
data['x-home-simple-routing'] = true
# Exclude node IPs from SNI destination recovery; retain browser recovery elsewhere.
sniffer = (data['sniffer'] ||= {})
skip = (sniffer['skip-dst-address'] ||= [])
(data['proxies'] || []).each do |node|
  server = node['server'].to_s
  skip << "#{server}/32" if server.match?(/\A(?:\d{1,3}\.){3}\d{1,3}\z/)
end
sniffer['skip-dst-address'] = skip.uniq
mode = File.stat(path).mode & 0o777
File.write(path, data.to_yaml)
File.chmod(mode & 0o770, path)

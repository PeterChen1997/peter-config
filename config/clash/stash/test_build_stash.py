"""Security regression checks with synthetic nodes; never read local credentials."""
from pathlib import Path
import contextlib,copy,importlib.util,io,json,os,tempfile,unittest
from unittest import mock
import yaml
spec=importlib.util.spec_from_file_location('stash_builder',Path(__file__).with_name('build_stash.py'))
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class PrivateNodeSafety(unittest.TestCase):
 def setUp(self):
  self.config={'proxy-groups':[{'name':'住宅节点','proxies':['DIRECT']},{'name':'大流量','proxies':['DIRECT']}],'rules':['MATCH,住宅节点'],'proxy-providers':{'equalvpn':{'url':'EQUALVPN_SUB_URL'}},'rule-providers':{}}
  self.private={'proxies':[{'name':'residential-example','server':'192.0.2.1','type':'vless','port':443},{'name':'datacenter-example','server':'192.0.2.2','type':'vless','port':443}],'node-groups':{'住宅节点':['residential-example'],'大流量':['datacenter-example']}}
 def test_data_center_does_not_become_residential_or_replace_bulk_default(self):
  builder.inject_private_nodes(self.config,self.private)
  groups={g['name']:g['proxies'] for g in self.config['proxy-groups']}
  self.assertEqual(groups['住宅节点'][0],'residential-example')
  self.assertNotIn('datacenter-example',groups['住宅节点'])
  self.assertEqual(groups['大流量'],['DIRECT','datacenter-example'])
  self.assertIn('IP-CIDR,192.0.2.2/32,DIRECT,no-resolve',self.config['rules'])
 def test_unclassified_private_node_stops_generation(self):
  self.private['node-groups'].pop('大流量')
  with self.assertRaises(ValueError):builder.inject_private_nodes(self.config,self.private)
 def test_rebuild_replaces_world_readable_output_with_private_file(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);private=root/'private';private.mkdir()
   (root/'stash.yaml').write_text(yaml.safe_dump(self.config))
   (private/'sources.json').write_text(json.dumps({'equalvpn':'https://example.invalid/synthetic-subscription'}))
   (private/'stash-private-nodes.yaml').write_text(yaml.safe_dump(self.private))
   output=root/'phone.yaml';output.write_text('old synthetic data');output.chmod(0o644)
   with mock.patch.multiple(builder,HERE=str(root),PRIVATE=str(private)),mock.patch('sys.argv',['build_stash.py','--out',str(output)]),contextlib.redirect_stdout(io.StringIO()):builder.main()
   self.assertEqual(output.stat().st_mode&0o777,0o600)
   self.assertEqual(yaml.safe_load(output.read_text())['proxy-groups'][1]['proxies'][0],'DIRECT')
if __name__=='__main__':unittest.main()

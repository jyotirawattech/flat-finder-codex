import hashlib,json,os
from pathlib import Path
import subprocess,sys,tempfile,unittest,zipfile
ROOT=Path(__file__).resolve().parents[1]
class DistributionTests(unittest.TestCase):
 def test_installer_is_idempotent_and_protects_modifications(self):
  with tempfile.TemporaryDirectory() as t:
   env=dict(os.environ,CODEX_HOME=t);cmd=[sys.executable,str(ROOT/'scripts/install.py')]
   first=subprocess.run(cmd,env=env,capture_output=True,text=True);self.assertEqual(first.returncode,0,first.stderr)
   self.assertEqual(subprocess.run(cmd,env=env,capture_output=True).returncode,0)
   p=Path(t)/'skills/flat-finder/SKILL.md';p.write_text(p.read_text()+'\nLocal customization\n')
   retry=subprocess.run(cmd+['--update'],env=env,capture_output=True,text=True);self.assertNotEqual(retry.returncode,0);self.assertIn('local changes',retry.stderr);self.assertIn('Local customization',p.read_text())
 def test_manifest_matches_skill(self):
  sys.path.insert(0,str(ROOT/'scripts'));from install import hashes
  self.assertEqual(hashes(ROOT/'flat-finder'),json.loads((ROOT/'flat-finder/MANIFEST.json').read_text())['files'])
 def test_built_archives_have_manifests_and_synthetic_site(self):
  for name in ['flat-finder-codex-1.0.0.zip','flat-finder-skill.zip','flat-finder-demo-site.zip']:
   p=ROOT/'dist'/name
   if not p.exists():self.skipTest('Build release.py before archive acceptance tests')
   with zipfile.ZipFile(p) as z:
    self.assertIn('RELEASE-MANIFEST.json',z.namelist());self.assertFalse(any('..' in Path(n).parts for n in z.namelist()))
    manifest=json.loads(z.read('RELEASE-MANIFEST.json'))
    self.assertEqual(set(manifest['files']),set(z.namelist())-{'RELEASE-MANIFEST.json'})
    for name,digest in manifest['files'].items():self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),digest)
    if 'demo-site' in name:
     state=json.loads(z.read('demo-state.json'));self.assertTrue(state['profile']['demo']);self.assertTrue(all(x['demo'] for x in state['listings']));self.assertEqual(state['counts']['ready'],0)
if __name__=='__main__':unittest.main()

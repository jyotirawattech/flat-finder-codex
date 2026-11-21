import http.client
from pathlib import Path
import sys,tempfile,threading,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'flat-finder/scripts'))
from flat_finder import init_workspace
from ff_server import make_server
class LocalServerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();init_workspace(Path(cls.temp.name),demo=True);cls.server=make_server(cls.temp.name,0);cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.worker.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.worker.join();cls.temp.cleanup()
 def request(self,path='/',headers=None,method='GET'):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3);c.request(method,path,headers=headers or {});r=c.getresponse();body=r.read();result=(r.status,dict(r.getheaders()),body);c.close();return result
 def test_viewer_state_and_exports(self):
  status,h,b=self.request();self.assertEqual(status,200);self.assertIn(b'flat finder',b);status,h,b=self.request('/api/state');self.assertEqual(status,200);self.assertIn(b'"demo": true',b);self.assertEqual(h['Cache-Control'],'no-store');self.assertIn("script-src 'self'",h['Content-Security-Policy']);status,h,b=self.request('/api/export.csv');self.assertEqual(status,200);self.assertIn('attachment',h['Content-Disposition'])
 def test_raw_files_traversal_and_mutation_denied(self):
  for path in ['/profile.json','/listings.json','/scripts/ff_core.py','/../profile.json','/%2e%2e/profile.json','/vendor/../../profile.json']:
   self.assertEqual(self.request(path)[0],404,path)
  self.assertEqual(self.request('/api/state',method='POST')[0],405)
 def test_cross_origin_and_rebinding_denied(self):
  for headers in [{'Host':'evil.example:43126'},{'Origin':'https://evil.example'},{'Sec-Fetch-Site':'cross-site'}]:self.assertEqual(self.request('/api/state',headers)[0],403)
  self.assertEqual(self.server.server_address[0],'127.0.0.1')
 def test_correct_asset_mime(self):
  for path,typ in [('/style.css','text/css'),('/app.js','javascript'),('/vendor/leaflet.js','javascript'),('/vendor/leaflet.css','text/css')]:
   status,h,b=self.request(path);self.assertEqual(status,200);self.assertIn(typ,h['Content-Type'])
if __name__=='__main__':unittest.main()

import datetime as dt
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'flat-finder/scripts'))
from ff_core import ValidationError,assess,canonical_url,csv_report,distance_m,merge_listings,read_json,safe_url,validate_listing,validate_profile,workspace_state,write_json
from flat_finder import import_data,init_workspace
NOW=dt.datetime(2026,11,21,13,tzinfo=dt.timezone.utc)
def profile():
 p=read_json(ROOT/'flat-finder/assets/examples/profile.json');p.update(demo=False,move_in_before='2027-03-01',monthly_limit=30000);return validate_profile(p)
def listing():
 x=read_json(ROOT/'flat-finder/assets/examples/listings.json')['listings'][0];x.update(demo=False,source_checked_at=NOW.isoformat());return validate_listing(x)
class AssessmentTests(unittest.TestCase):
 def test_strict_budget_and_unknown_maintenance(self):
  p=profile();x=listing();x.update(rent=29000,maintenance=1000);self.assertEqual(assess(x,p,NOW)['state'],'excluded')
  x['maintenance']=None;a=assess(x,p,NOW);self.assertIsNone(a['monthly_total']);self.assertEqual(a['state'],'provisional')
  x['maintenance_included']=True;self.assertEqual(assess(x,p,NOW)['monthly_total'],29000)
  p['strict_monthly_limit']=False;x['rent']=30000;self.assertNotEqual(assess(x,p,NOW)['state'],'excluded')
 def test_radius_not_walk_or_availability(self):
  a=assess(listing(),profile(),NOW);self.assertLess(a['radius_m'],1000);self.assertEqual(a['state'],'provisional');self.assertTrue(any('walk' in g for g in a['gaps']));self.assertTrue(any('availability' in g for g in a['gaps']))
 def test_complete_requires_real_fresh_evidence(self):
  x=listing();p=profile();x['coordinates']['precision']='entrance';x['walk'].update(status='verified',exact_entrance=True,legitimate=True,source_url='https://example.org/route',checked_at=NOW.isoformat());x['availability'].update(status='confirmed',before_deadline=True,confirmed_at=NOW.isoformat(),evidence_note='Provider confirmation recorded')
  self.assertEqual(assess(x,p,NOW)['state'],'ready')
  for stamp in ['2026-10-01T10:00:00+05:30','2027-01-01T10:00:00+05:30']:
   x['walk']['checked_at']=stamp;self.assertEqual(assess(x,p,NOW)['state'],'provisional')
  x['demo']=True;self.assertNotEqual(assess(x,p,NOW)['state'],'ready')
 def test_deadline_timezone_no_rolling(self):
  p=profile();p['move_in_before']='2026-11-22';a=assess(listing(),p,dt.datetime(2026,11,21,19,tzinfo=dt.timezone.utc));self.assertFalse(a['can_prepare_contact']);self.assertIn('Do not',a['next_action']);self.assertEqual(p['move_in_before'],'2026-11-22')
 def test_verified_anchors_and_room_scope(self):
  p=profile();x=listing();p['anchors'][0]['verified']=False;self.assertIsNone(assess(x,p,NOW)['radius_m']);p['anchors'][0]['verified']=True;p['anchors'].append(dict(p['anchors'][0],id='far-anchor',lat=18.9));x['kind']='private_room';p['room_anchor_ids']=['far-anchor'];self.assertEqual(assess(x,p,NOW)['state'],'excluded');self.assertAlmostEqual(distance_m({'lat':0,'lng':0},{'lat':0,'lng':1}),111195,delta=2)
 def test_protected_contact_suppression(self):
  for status in ['sent','delivered','read','unknown','held','closed']:
   x=listing();x['contact']['status']=status;self.assertFalse(assess(x,profile(),NOW)['can_prepare_contact'])
 def test_merge_preserves_history(self):
  old=listing();old['contact']['status']='sent';new=listing();new['source_url']+='?utm_source=test';result=merge_listings([old],[new]);self.assertEqual(len(result),1);self.assertEqual(result[0]['contact']['status'],'sent')
  for status in ['closed','held','unknown']:
   old['contact']['status']=status;new['contact']['status']='sent';self.assertEqual(merge_listings([old],[new])[0]['contact']['status'],status)
  old['disposition']='unavailable';self.assertEqual(merge_listings([old],[new])[0]['disposition'],'unavailable');new['source_url']='https://example.org/another'
  with self.assertRaises(ValidationError):merge_listings([old],[new])
 def test_cross_source_phone_duplicate_suppression(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);write_json(w/'profile.json',profile());old=listing();old['contact'].update(phone='+12025550123',status='unknown');new=listing();new.update(id='another',source_url='https://example.org/another');new['contact']['phone']=old['contact']['phone'];write_json(w/'listings.json',{'listings':[old,new]});candidate=next(x for x in workspace_state(w,NOW)['listings'] if x['id']=='another');self.assertFalse(candidate['assessment']['can_prepare_contact']);self.assertIn('another saved source',candidate['assessment']['next_action'])
 def test_invalid_urls_numbers_and_stable_identity(self):
  for url in ['javascript:alert(1)','http://example.org','https://a:b@example.org/','https://example.org:123/','https://example.org/\nheader']:
   with self.assertRaises(ValidationError):safe_url(url)
  for bad in [True,float('nan'),float('inf'),-1]:
   x=listing();x['rent']=bad
   with self.assertRaises(ValidationError):validate_listing(x)
  self.assertNotEqual(canonical_url('https://example.org/?id=1'),canonical_url('https://example.org/?id=2'))
 def test_atomic_import_no_overwrite_and_permissions(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);init_workspace(w,demo=True);before=(w/'listings.json').read_bytes();bad=listing();bad['rent']=-1
   with self.assertRaises(ValidationError):import_data(w,{'listings':[bad]})
   self.assertEqual((w/'listings.json').read_bytes(),before)
   with self.assertRaises(ValidationError):init_workspace(w,demo=True)
   self.assertEqual((w/'listings.json').stat().st_mode&0o777,0o600)
 def test_csv_formula_escaping(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);init_workspace(w,demo=True);data=read_json(w/'listings.json');data['listings'][0]['title']='=1+1';write_json(w/'listings.json',data);self.assertIn("'=1+1",csv_report(workspace_state(w,NOW)))
if __name__=='__main__':unittest.main()

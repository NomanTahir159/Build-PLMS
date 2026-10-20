import json,tempfile,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from server import Backend
from test_backend import fixture

class StorageLayoutTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.api=Backend(self.root/'Database'/'plms.sqlite3')
  self.auth=self.api.handle({'action':'bootstrap','username':'U001','password':'123','state':fixture()})
 def tearDown(self):self.api.db.close();self.temp.cleanup()
 def call(self,action,**kwargs):return self.api.handle({'action':action,'token':self.auth['token'],**kwargs})
 def test_catalog_changes_survive_restart_and_named_files_are_written(self):
  st=self.call('read');st['state']['catalog'][0]['range']='custom preserved';st['state']['profileDates']={'Example':{'updatedAt':'2026-10-20'}}
  self.call('commit',state=st['state'],revision=st['revision'])
  catalog=json.loads((self.root/'Catalog'/'catalog.json').read_text());self.assertEqual(catalog['catalog'][0]['range'],'custom preserved')
  self.assertTrue((self.root/'Presets'/'presets.json').is_file());self.assertTrue((self.root/'Log'/'activity.jsonl').is_file())
  self.api.db.close();self.api=Backend(self.root/'Database'/'plms.sqlite3');self.assertEqual(self.api.load()[1]['catalog'][0]['range'],'custom preserved')
 def test_snapshots_are_real_backup_files_without_removing_unrelated_files(self):
  unrelated=self.root/'Backup'/'PLMS-user-document.json';unrelated.write_text('keep')
  row=self.call('snapshot_create',reason='On demand')['row'];path=self.root/'Backup'/('PLMS-'+row['id']+'.json')
  self.assertTrue(path.is_file());self.assertEqual(json.loads(path.read_text())['format'],'PLMS_BACKUP');self.assertTrue(unrelated.exists())
 def test_repeat_order_can_use_stable_patient_id_and_direct_test_code(self):
  st=self.call('read');data=st['state'];p=data['patients'][0];p['id']='PATIENT-ONE';p['patientGroupId']='GROUP-ONE'
  data['orders'].append({'lab':'REPEAT','patientId':p['id'],'patientGroupId':p['patientGroupId'],'patient':p['name'],'tests':['TEST::HB'],'department':'Hematology','sample':'Collected','status':'Pending'})
  st=self.call('commit',state=data,revision=st['revision']);self.assertIn('REPEAT',[o['lab'] for o in st['state']['orders']]);self.assertEqual(self.api.item_tests(st['state'],'TEST::HB')[0]['code'],'HB')
  self.assertIn('REPEAT',[o['lab'] for o in self.call('read')['state']['orders']])
 def test_admin_order_deletion_can_remove_archived_reports(self):
  st=self.call('read');data=st['state'];data['reportVersions']={'1':[{'number':1,'html':'<p>Approved</p>'}]}
  st=self.call('commit',state=data,revision=st['revision']);data=st['state'];data['orders']=[o for o in data['orders'] if o['lab']!='1'];data['results'].pop('1',None);data['reportVersions'].pop('1',None)
  st=self.call('commit',state=data,revision=st['revision']);self.assertNotIn('1',st['state']['reportVersions'])

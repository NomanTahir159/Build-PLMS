import json, pathlib, unittest
import test_backend as fixtures
m=fixtures.m
class DesktopIntegrationTests(unittest.TestCase):
 setUp=fixtures.BackendTests.setUp
 tearDown=fixtures.BackendTests.tearDown
 call=fixtures.BackendTests.call
 account=fixtures.BackendTests.account
 def test_management_permission_scope_and_reopen(self):
  current=self.call('read');data=current['state'];data['management']={'employees':[{'id':1,'name':'Employee'}],'trainees':[{'id':1,'student':'Trainee','sections':[]}]}
  self.call('commit',state=data,revision=current['revision'])
  viewer=self.account('Viewer');visible=self.call('read',viewer)
  self.assertEqual(visible['state']['management'],{'employees':[],'trainees':[]})
  denied=visible['state'];denied['management']['employees']=[{'id':2,'name':'Unauthorized'}]
  with self.assertRaises(m.ApiError):self.call('commit',viewer,state=denied,revision=visible['revision'])
  current=self.call('read');current['state']['management']['employees'][0]['name']='Updated'
  self.call('commit',state=current['state'],revision=current['revision'])
  self.api.db.close();self.api=m.Backend(self.path)
  self.assertEqual(self.api.load()[1]['management']['employees'][0]['name'],'Updated')
 def test_management_seed_migration_preserves_clinical_data(self):
  previous=self.api.load()[1];self.api.ensure_management();after=self.api.load()[1]
  seed=json.loads((pathlib.Path(__file__).parents[1]/'management.seed.json').read_text(encoding='utf-8'))
  self.assertEqual(after['management'],seed)
  self.assertEqual(after['patients'],previous['patients']);self.assertEqual(after['catalog'],previous['catalog'])
 def test_management_schema_rejects_duplicate_ids(self):
  with self.assertRaises(m.ApiError):m.validate_management({'employees':[{'id':1,'name':'A'},{'id':1,'name':'B'}],'trainees':[]})

import base64, io, json, pathlib, unittest, zipfile
from unittest.mock import patch
import test_backend as fixtures
m=fixtures.m
class DesktopIntegrationTests(unittest.TestCase):
 setUp=fixtures.BackendTests.setUp
 tearDown=fixtures.BackendTests.tearDown
 call=fixtures.BackendTests.call
 account=fixtures.BackendTests.account
 def test_word_operations_require_authenticated_template_permission(self):
  with self.assertRaises(m.ApiError):self.api.handle({'action':'word_updates'})
  viewer=self.account('Viewer')
  with self.assertRaises(m.ApiError):self.call('word_updates',viewer)
  with self.assertRaises(m.ApiError):self.call('word_open',id='unknown',bytes='')
 def test_word_open_only_accepts_existing_template(self):
  state=self.call('read');data=state['state'];data['reportTemplates']=[{'id':'RT_WORD','name':'Word','content':'<p>{{RESULTS_TABLE}}</p>'}]
  self.call('commit',state=data,revision=state['revision'])
  with patch.object(self.api.office,'open',return_value={'opened':True}) as op:
   self.assertTrue(self.call('word_open',id='RT_WORD',bytes='doc')['opened']);op.assert_called_once_with('RT_WORD','doc')
 def test_managed_document_preserves_existing_file_and_rejects_traversal(self):
  office=self.api.office
  for bad in ['../a','x/y','x\\y','',None]:
   with self.assertRaises(m.ApiError):office.path(bad)
  doc=io.BytesIO()
  with zipfile.ZipFile(doc,'w') as archive:archive.writestr('word/document.xml','<document/>')
  encoded=base64.b64encode(doc.getvalue()).decode()
  with patch.object(office,'winword',return_value='word.exe'),patch.object(office,'watch'),patch.object(m.subprocess,'Popen'):
   with self.assertRaises(m.ApiError):office.open('RT_TEST','invalid')
   office.open('RT_TEST',encoded);before=office.path('RT_TEST').read_bytes()
   office.open('RT_TEST','invalid');self.assertEqual(office.path('RT_TEST').read_bytes(),before)
 def test_word_updates_filter_to_existing_templates(self):
  path=self.api.office.path('RT_TEST');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'docx')
  path.with_suffix('.sync.json').write_text(json.dumps({'id':'RT_TEST','revision':'abc','html':'<p>{{RESULTS_TABLE}}</p>','bytes':''}))
  self.assertEqual(self.api.office.updates(set()),[])
  self.assertEqual(self.api.office.updates({'RT_TEST'})[0]['revision'],'abc')
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

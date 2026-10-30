import copy,pathlib,tempfile,unittest
from test_backend import m,fixture,PASSWORD

class TraineeLetterSettingsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)/'db.sqlite3';self.api=m.Backend(str(self.path))
  state=fixture();state['settings']={'identity':{'laboratoryName':'Clinical Lab'}}
  state['rolePermissions']['Viewer'].update({'trainees.view':True,'trainees.edit':True})
  self.admin=self.api.handle({'action':'bootstrap','username':'admin','password':PASSWORD,'state':state})
  snap=self.api.handle({'action':'read','token':self.admin['token']});state=snap['state']
  state['users'].append({'id':'editor','name':'Editor','role':'Viewer','status':'Active','department':'All','__nativePassword':PASSWORD})
  self.api.handle({'action':'commit','token':self.admin['token'],'state':state,'revision':snap['revision']})
  self.editor=self.api.handle({'action':'login','username':'editor','password':PASSWORD})
 def tearDown(self):self.api.db.close();self.tmp.cleanup()
 def call(self,action,auth=None,**kw):return self.api.handle({'action':action,'token':(auth or self.editor)['token'],**kw})
 def config(self):return {'title':'Training Letter','body':'Hello {student}','bodyHtml':'<p style="text-indent:4mm"><strong>Hello {student}</strong></p>','gapMM':12,'signatories':[{'name':'Signer','lines':'Pathologist','affiliation':'{laboratory}'}]}
 def test_trainee_editor_can_save_rich_letter_without_settings_edit(self):
  snap=self.call('read');state=snap['state'];state['settings']['traineeLetter']=self.config();self.call('commit',state=state,revision=snap['revision'])
  self.assertEqual(self.call('read')['state']['settings']['traineeLetter'],self.config())
  self.assertEqual(self.call('read')['state']['settings']['identity']['laboratoryName'],'Clinical Lab')
  other=m.Backend(str(self.path))
  try:self.assertEqual(other.load()[1]['settings']['traineeLetter'],self.config())
  finally:other.db.close()
 def test_letter_permission_does_not_allow_identity_changes(self):
  snap=self.call('read');state=snap['state'];state['settings']['identity']['laboratoryName']='Forbidden';state['settings']['traineeLetter']=self.config()
  with self.assertRaisesRegex(m.ApiError,'settings.edit'):self.call('commit',state=state,revision=snap['revision'])
  self.assertNotIn('traineeLetter',self.call('read')['state']['settings'])
 def test_missing_trainee_edit_denied(self):
  snap=self.call('read',self.admin);state=snap['state'];state['rolePermissions']['Viewer']['trainees.edit']=False;self.call('commit',self.admin,state=state,revision=snap['revision'])
  snap=self.call('read');state=snap['state'];state['settings']['traineeLetter']=self.config()
  with self.assertRaisesRegex(m.ApiError,'trainees.edit'):self.call('commit',state=state,revision=snap['revision'])
 def test_invalid_gap_or_unsafe_rich_html_is_rejected(self):
  for field,value in [('gapMM',101),('bodyHtml','<script>bad()</script>')]:
   snap=self.call('read');state=snap['state'];state['settings']['traineeLetter']=self.config();state['settings']['traineeLetter'][field]=value
   with self.assertRaises(m.ApiError):self.call('commit',state=state,revision=snap['revision'])
   self.assertNotIn('traineeLetter',self.call('read')['state']['settings'])

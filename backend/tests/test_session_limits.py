import copy,tempfile,pathlib,unittest
from test_backend import m,fixture,PASSWORD
class SessionLimitsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.api=m.Backend(str(pathlib.Path(self.tmp.name)/'db.sqlite3'));self.auth=self.api.handle({'action':'bootstrap','username':'admin','password':PASSWORD,'state':fixture()})
 def tearDown(self):self.api.db.close();self.tmp.cleanup()
 def call(self,action,auth=None,**kw):return self.api.handle({'action':action,'token':(auth or self.auth)['token'],**kw})
 def limits(self,idle,maximum):
  st=self.call('read');s=st['state'];s.setdefault('settings',{})['sessionLimits']={'idleMinutes':idle,'maxHours':maximum};return self.call('commit',state=s,revision=st['revision'])
 def test_never_disables_both(self):
  self.limits(0,0);s=self.api.sessions[self.auth['token']];s['last']-=10**7;s['start']-=10**7;self.call('read')
 def test_idle_only(self):
  self.limits(5,0);s=self.api.sessions[self.auth['token']];s['start']-=10**7;self.call('read');s['last']-=301
  with self.assertRaisesRegex(m.ApiError,'expired'):self.call('read')
 def test_maximum_only(self):
  self.limits(0,1);s=self.api.sessions[self.auth['token']];s['last']-=10**7;self.call('read');s['start']-=3601
  with self.assertRaisesRegex(m.ApiError,'expired'):self.call('read')
 def test_options_validation(self):
  for value in [-1,True,'Never',7,None]:
   with self.assertRaisesRegex(m.ApiError,'Invalid session'):self.limits(value,8)
  self.assertEqual(m.session_limits(self.call('read')['state']),(1800,28800))
 def test_persists_across_restart(self):
  self.limits(15,12)
  # Verify persisted database state through a new connection to the same file.
  other=m.Backend(str(pathlib.Path(self.tmp.name)/'db.sqlite3'))
  try:self.assertEqual(m.session_limits(other.load()[1]),(900,43200))
  finally:other.db.close()
 def test_non_admin_settings_editor_cannot_change_limits(self):
  st=self.call('read');s=st['state'];s['rolePermissions']['Viewer']['settings.edit']=True;s['users'].append({'id':'viewer','name':'Viewer','role':'Viewer','status':'Active','department':'All','__nativePassword':PASSWORD});self.call('commit',state=s,revision=st['revision']);viewer=self.api.handle({'action':'login','username':'viewer','password':PASSWORD});st=self.call('read',viewer);s=st['state'];s.setdefault('settings',{})['sessionLimits']={'idleMinutes':0,'maxHours':0}
  with self.assertRaisesRegex(m.ApiError,'Only Administrators'):self.call('commit',viewer,state=s,revision=st['revision'])

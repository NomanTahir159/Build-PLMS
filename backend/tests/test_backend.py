import copy, importlib.util, pathlib, tempfile, unittest
spec=importlib.util.spec_from_file_location('backend',pathlib.Path(__file__).parents[1]/'server.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PASSWORD='Correct horse battery staple'
def fixture():
 return {'users':[{'id':'admin','name':'Administrator','role':'Administrator','status':'Active','department':'All','password':''}],
 'patients':[{'lab':'1','name':'Patient One'},{'lab':'2','name':'Patient Two'}],
 'orders':[{'lab':'1','patient':'Patient One','tests':['Hemoglobin'],'department':'Hematology','testStates':{}},{'lab':'2','patient':'Patient Two','tests':['Colour'],'department':'Microbiology','testStates':{}}],
 'catalog':[{'code':'HB','name':'Hemoglobin','department':'Hematology'},{'code':'UR','name':'Colour','department':'Microbiology'}],
 'results':{'1':{'HB':'12'},'2':{'UR':'Yellow'}},'reportTemplates':[],'reportVersions':{},'resultReferences':{},
 'rolePermissions':{'Technologist':{'patients.view':True,'orders.view':True,'results.view':True,'results.enter':True,'results.edit':True,'samples.receive':True,'account.change_own_password':True},'Viewer':{'patients.view':True,'orders.view':True,'results.view':True}},'userPermissionOverrides':{}}
class BackendTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=str(pathlib.Path(self.tmp.name)/'plms.sqlite3');self.api=m.Backend(self.path);self.admin=self.api.handle({'action':'bootstrap','username':'admin','password':PASSWORD,'state':fixture()})
 def tearDown(self):self.api.db.close();self.tmp.cleanup()
 def call(self,action,auth=None,**kw):return self.api.handle({'action':action,'token':(auth or self.admin)['token'],**kw})
 def account(self,role='Viewer',department='All'):
  st=self.call('read');data=st['state'];data['users'].append({'id':role,'name':role,'role':role,'department':department,'status':'Active','__nativePassword':PASSWORD});self.call('commit',state=data,revision=st['revision']);return self.api.handle({'action':'login','username':role,'password':PASSWORD})
 def test_credentials_and_restart(self):
  self.assertEqual(self.admin['state']['users'][0]['password'],'');row=self.api.db.execute('SELECT hash FROM credentials WHERE id=?',('admin',)).fetchone();self.assertNotIn(PASSWORD,row[0]);self.assertTrue(m.password_verify(PASSWORD,row[0]));self.assertNotIn(PASSWORD,self.api.db.execute('SELECT body FROM app_state').fetchone()[0]);b=m.Backend(self.path);self.assertTrue(b.handle({'action':'login','username':'admin','password':PASSWORD})['token']);b.db.close()
 def test_no_session_and_logout(self):
  with self.assertRaises(m.ApiError):self.api.handle({'action':'read','token':'forged'})
  self.call('logout')
  with self.assertRaises(m.ApiError):self.call('read')
 def test_reject_short_setup_and_repeat_setup(self):
  with self.assertRaises(m.ApiError):self.api.handle({'action':'bootstrap','username':'x','password':PASSWORD,'state':fixture()})
  with self.assertRaises(m.ApiError):m.password_hash('123')
 def test_viewer_cannot_write_or_escalate(self):
  viewer=self.account();st=self.call('read',viewer);data=copy.deepcopy(st['state']);data['patients'][0]['name']='Changed'
  with self.assertRaises(m.ApiError):self.call('commit',viewer,state=data,revision=st['revision'])
  data=copy.deepcopy(st['state']);data['users'][0]['role']='Administrator'
  with self.assertRaises(m.ApiError):self.call('commit',viewer,state=data,revision=st['revision'])
  self.assertEqual(self.call('read')['state']['patients'][0]['name'],'Patient One')
 def test_department_read_write_scope(self):
  tech=self.account('Technologist','Hematology');st=self.call('read',tech);self.assertEqual([x['lab'] for x in st['state']['patients']],['1']);self.assertNotIn('2',st['state']['results'])
  data=copy.deepcopy(st['state']);data['results']['1']['HB']='13';self.call('commit',tech,state=data,revision=st['revision']);st=self.call('read',tech);data=copy.deepcopy(st['state']);data['results']['2']={'UR':'Changed'}
  with self.assertRaises(m.ApiError):self.call('commit',tech,state=data,revision=st['revision'])
  self.assertEqual(self.call('read')['state']['results']['2']['UR'],'Yellow')
 def test_stale_write_rejected(self):
  st=self.call('read');s=copy.deepcopy(st['state']);s['patients'][0]['name']='Updated';self.call('commit',state=s,revision=st['revision'])
  with self.assertRaises(m.ApiError):self.call('commit',state=s,revision=st['revision'])
 def test_throttle_and_sql_injection(self):
  for _ in range(5):
   with self.assertRaises(m.ApiError):self.api.handle({'action':'login','username':"admin' OR 1=1 --",'password':'wrong'})
  with self.assertRaisesRegex(m.ApiError,'Too many'):self.api.handle({'action':'login','username':"admin' OR 1=1 --",'password':'wrong'})
  self.assertTrue(self.api.handle({'action':'login','username':'admin','password':PASSWORD})['token'])
 def test_password_and_session_revocation(self):
  second=self.api.handle({'action':'login','username':'admin','password':PASSWORD});self.call('password',current=PASSWORD,password='Another strong password!')
  with self.assertRaises(m.ApiError):self.call('read',second)
  with self.assertRaises(m.ApiError):self.api.handle({'action':'login','username':'admin','password':PASSWORD})
  self.assertTrue(self.api.handle({'action':'login','username':'admin','password':'Another strong password!'})['token'])
 def test_approved_results_protected(self):
  st=self.call('read');s=st['state'];s['orders'][0]['testStates']={'Hemoglobin':{'resultStatus':'Approved'}};self.call('commit',state=s,revision=st['revision']);tech=self.account('Technologist');st=self.call('read',tech);s=st['state'];s['results']['1']['HB']='999'
  with self.assertRaisesRegex(m.ApiError,'reports.amend'):self.call('commit',tech,state=s,revision=st['revision'])
 def test_backup_restore_validation(self):
  backup=self.call('backup')['state'];self.assertTrue(backup['users'][0]['password'].startswith('pbkdf2-'));restored=self.call('restore',state=backup);self.assertEqual(len(restored['state']['patients']),2)
  bad=copy.deepcopy(backup);bad['orders'][0]['lab']='nonexistent'
  with self.assertRaises(m.ApiError):self.call('restore',state=bad)
  self.assertEqual(len(self.call('read')['state']['orders']),2)
 def test_html_and_prototype_rejected(self):
  st=self.call('read');data=st['state'];data['reportTemplates']=[{'id':'bad','content':'<img src=x onerror="alert(1)">'}]
  with self.assertRaises(m.ApiError):self.call('commit',state=data,revision=st['revision'])
  with self.assertRaises(m.ApiError):m.validate_state({**fixture(),'__proto__':{}})
 def test_audit_has_no_patient_values(self):
  st=self.call('read');s=st['state'];s['patients'][0]['name']='Sensitive Changed Name';self.call('commit',state=s,revision=st['revision']);events=self.call('audit')['events'];self.assertNotIn('Sensitive',str(events));self.assertNotIn(PASSWORD,str(events))
 def test_snapshot_storage_and_access(self):
  row=self.call('snapshot_create',reason='On demand')['row'];self.assertNotIn('payload',row)
  rows=self.call('snapshots')['rows'];self.assertNotIn('payload',rows[0]);payload=self.call('snapshot_read',id=row['id'])['row']['payload'];self.assertTrue(payload['data']['users'][0]['password'].startswith('pbkdf2-'))
  viewer=self.account()
  for action in ('snapshots','snapshot_read','snapshot_create','backup'):
   with self.assertRaises(m.ApiError):self.call(action,viewer,id=row['id'])
  bad=copy.deepcopy(payload);bad['data']['patients'][0]['name']='tampered'
  with self.assertRaisesRegex(m.ApiError,'integrity'):self.call('snapshot_import',rows=[{'id':'tampered','time':row['time'],'reason':'Migrated','payload':bad}])
  b=m.Backend(self.path);self.assertEqual(b.db.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0],1);b.db.close()
 def test_admin_id_change_keeps_credential_and_session(self):
  st=self.call('read');data=st['state'];data['users'][0]['id']='new-admin';response=self.call('commit',state=data,revision=st['revision']);self.assertEqual(response['userId'],'new-admin');self.assertTrue(self.api.handle({'action':'login','username':'new-admin','password':PASSWORD})['token'])
 def test_add_only_cannot_create_administrator(self):
  st=self.call('read');data=st['state'];data['rolePermissions']['Viewer']['users.add']=True;self.call('commit',state=data,revision=st['revision']);viewer=self.account();st=self.call('read',viewer);data=st['state'];data['users'].append({'id':'intruder','name':'Intruder','role':'Administrator','status':'Active','department':'All','__nativePassword':PASSWORD})
  with self.assertRaisesRegex(m.ApiError,'users.change_role'):self.call('commit',viewer,state=data,revision=st['revision'])
 def test_session_expiry(self):
  self.api.sessions[self.admin['token']]['last']-=1801
  with self.assertRaisesRegex(m.ApiError,'expired'):self.call('read')
  login=self.api.handle({'action':'login','username':'admin','password':PASSWORD});self.api.sessions[login['token']]['start']-=28801
  with self.assertRaisesRegex(m.ApiError,'expired'):self.call('read',login)
 def test_password_reset_revokes_other_worker_session(self):
  b=m.Backend(self.path);other=b.handle({'action':'login','username':'admin','password':PASSWORD});self.call('password',current=PASSWORD,password='Changed across worker processes!')
  with self.assertRaisesRegex(m.ApiError,'Password changed'):b.handle({'action':'read','token':other['token']})
  b.db.close()
 def test_restore_cannot_promote_non_admin(self):
  st=self.call('read');data=st['state'];data['rolePermissions']['Viewer']['backups.restore']=True;self.call('commit',state=data,revision=st['revision']);viewer=self.account()
  with self.assertRaisesRegex(m.ApiError,'Administrator'):self.call('restore',viewer,state=fixture())
 def test_restore_preserves_current_admin(self):
  backup=self.call('backup')['state'];backup['users']=[{'id':'legacy','name':'Legacy Admin','role':'Administrator','status':'Active','department':'All','password':m.password_hash('Legacy secure password!')}];self.call('restore',state=backup);self.assertTrue(self.api.handle({'action':'login','username':'admin','password':PASSWORD})['token'])
 def test_reordering_requires_permission_and_persists(self):
  st=self.call('read');data=st['state'];data['catalog'].reverse();self.call('commit',state=data,revision=st['revision']);self.assertEqual(self.call('read')['state']['catalog'][0]['code'],'UR');viewer=self.account();st=self.call('read',viewer);data=st['state'];data['patients'].reverse()
  with self.assertRaisesRegex(m.ApiError,'patients.edit'):self.call('commit',viewer,state=data,revision=st['revision'])
 def test_inactive_profile_cannot_be_booked(self):
  st=self.call('read');data=st['state'];data['catalog'][0]['profiles']=['Profile A'];data['profileActive']={'profile a':False};self.call('commit',state=data,revision=st['revision']);st=self.call('read');data=st['state'];data['patients'].append({'lab':'3','name':'New Patient'});data['orders'].append({'lab':'3','patient':'New Patient','tests':['Profile A']})
  with self.assertRaisesRegex(m.ApiError,'active'):self.call('commit',state=data,revision=st['revision'])
 def test_worker_unicode_under_windows_codepage_and_existing_login(self):
  import json,os,subprocess,sys
  data=fixture();data['patients'][0]['name']='مریض Ελληνικά 中文';data['catalog'][0]['unit']='μmol/L';data['catalog'][1]['name']='β-hCG';data['orders'][1]['tests']=['β-hCG']
  db=str(pathlib.Path(self.tmp.name)/'unicode.sqlite3');command=[sys.executable,str(pathlib.Path(__file__).parents[1]/'server.py'),db];env={**os.environ,'PYTHONIOENCODING':'cp1252','PYTHONUTF8':'0'}
  def run(requests):
   proc=subprocess.run(command,input=('\n'.join(json.dumps(r,ensure_ascii=True) for r in requests)+'\n').encode('ascii'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=20)
   self.assertEqual(proc.returncode,0,proc.stderr.decode('ascii',errors='replace'));return [json.loads(line) for line in proc.stdout.splitlines()]
  initial=run([{'action':'bootstrap','username':'Windows Admin','password':PASSWORD,'state':data}]);self.assertTrue(initial[0]['ok']);self.assertEqual(initial[0]['data']['state']['patients'][0]['name'],data['patients'][0]['name'])
  reopened=run([{'action':'status'},{'action':'login','username':'Windows Admin','password':PASSWORD}]);self.assertTrue(reopened[0]['data']['initialized']);self.assertTrue(reopened[1]['ok']);self.assertEqual(reopened[1]['data']['state']['catalog'][0]['unit'],'μmol/L')
if __name__=='__main__':unittest.main()

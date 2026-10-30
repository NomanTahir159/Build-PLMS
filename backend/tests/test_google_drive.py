import base64, copy, gzip, hashlib, json, os, pathlib, tempfile, threading, time, unittest, urllib.parse, urllib.request
from unittest import mock
from test_backend import m, fixture, PASSWORD
import google_drive as g

CLIENT={'installed':{'client_id':'1234567890-example.apps.googleusercontent.com','client_secret':'desktop-public-client-secret'}}
class MemoryStore:
 def __init__(self):self.value={}
 def read(self):return copy.deepcopy(self.value)
 def write(self,value):self.value=copy.deepcopy(value)

class Google:
 def __init__(self):self.files={};self.calls=[];self.offline=False;self.corrupt=False
 def __call__(self,method,url,headers=None,body=None,limit=g.MAX_BACKUP):
  self.calls.append((method,url,headers,body))
  if self.offline:raise g.DriveError('Offline; try again later.')
  if url==g.TOKEN_URL:return json.dumps({'access_token':'ACCESS-PRIVATE','refresh_token':'REFRESH-PRIVATE','expires_in':3600,'scope':g.SCOPE}).encode()
  if 'openidconnect.googleapis.com' in url:return b'{"email":"lab@example.test","email_verified":true}'
  if '/upload/drive/' in url:
   from email.parser import BytesParser
   from email.policy import default
   message=BytesParser(policy=default).parsebytes(('MIME-Version: 1.0\r\nContent-Type: '+headers['Content-Type']+'\r\n\r\n').encode()+body)
   parts=list(message.iter_parts());metadata=json.loads(parts[0].get_payload(decode=True));data=parts[1].get_payload(decode=True);ident='cloud_'+str(len(self.files)+1)
   row={**metadata,'id':ident,'createdTime':g.stamp(),'size':str(len(data)),'spaces':['appDataFolder']};self.files[ident]=(row,data);return json.dumps(row).encode()
  parsed=urllib.parse.urlsplit(url);ident=parsed.path.split('/')[-1]
  if parsed.path.endswith('/files'):
   query=urllib.parse.parse_qs(parsed.query);assert query['spaces']==['appDataFolder'];assert 'plmsBackup' in query['q'][0]
   rows=[copy.deepcopy(row) for row,_ in self.files.values() if row.get('appProperties',{}).get('plmsBackup')==g.MARKER]
   return json.dumps({'files':sorted(rows,key=lambda r:r['createdTime'],reverse=True)}).encode()
  if method=='DELETE':del self.files[ident];return b''
  row,data=self.files[ident]
  if parsed.query=='alt=media':return data+b'bad' if self.corrupt else data
  return json.dumps(row).encode()

def wait(cloud,job):
 for _ in range(500):
  current=cloud.job_status(job['jobId'])
  if current['state']!='running':return current
  time.sleep(.01)
 raise AssertionError('Background job did not finish')

class DriveTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)/'Database'/'plms.sqlite3';self.api=m.Backend(self.path)
  data=fixture();data['management']={'employees':[{'id':1,'serial':'1','name':'Employee'}],'trainees':[]}
  self.admin=self.api.handle({'action':'bootstrap','username':'admin','password':PASSWORD,'state':data})
  self.store=MemoryStore();self.google=Google();self.cloud=g.GoogleDrive(self.path,self.store,self.google,opener=lambda _url:False);self.api._google_drive=self.cloud
  self.cloud.configure(CLIENT);self.cloud.config.update(refresh_token='REFRESH-PRIVATE',email='lab@example.test');self.cloud._save()
 def tearDown(self):self.cloud.stop.set();self.cloud.cancel.set();self.api.db.close();self.tmp.cleanup()
 def call(self,action,**kw):return self.api.handle({'action':action,'token':self.admin['token'],**kw})
 def test_bundled_desktop_client_is_loaded_without_setup(self):
  bundle=pathlib.Path(self.tmp.name)/'bundled';bundle.mkdir()
  (bundle/'google-drive-client.json').write_text(json.dumps(CLIENT))
  with mock.patch.object(g.sys,'_MEIPASS',str(bundle),create=True):
   cloud=g.GoogleDrive(self.path,MemoryStore(),self.google)
  self.assertTrue(cloud.public_status()['configured'])
  self.assertFalse(cloud.public_status()['connected'])
  self.assertNotIn('client_secret',cloud.public_status())
 def test_cloud_export_is_verified_and_has_explicit_purpose(self):
  wait(self.cloud,self.cloud.backup());ident=next(iter(self.google.files))
  job=wait(self.cloud,self.call('drive_download',fileId=ident,purpose='export'))
  self.assertEqual(job['state'],'done');self.assertEqual(job['result']['purpose'],'export')
  self.assertEqual(job['result']['payload']['format'],'PLMS_BACKUP')
 def test_cloud_delete_checks_marker_and_never_deletes_local_copy(self):
  wait(self.cloud,self.cloud.backup());ident=next(iter(self.google.files))
  result=wait(self.cloud,self.call('drive_delete',fileId=ident))
  self.assertEqual(result['state'],'done');self.assertNotIn(ident,self.google.files)
  self.assertEqual(len(list((self.path.parent.parent/'Backup').glob('*.json'))),1)
  self.google.files['ordinary']=({'id':'ordinary','spaces':['drive'],'appProperties':{}},b'example')
  result=wait(self.cloud,self.cloud.delete_backup('ordinary'))
  self.assertEqual(result['state'],'error');self.assertIn('ordinary',self.google.files)
 def test_manual_cloud_backup_ignores_disabled_schedule(self):
  self.cloud.settings(False,168,7);self.assertFalse(self.cloud.tick())
  result=wait(self.cloud,self.call('drive_backup'));self.assertEqual(result['state'],'done')
  self.assertFalse(self.cloud.config['enabled']);self.assertEqual(self.cloud.config['hours'],168)
 def test_full_backup_is_hidden_verified_and_restorable(self):
  outcome=wait(self.cloud,self.cloud.backup());self.assertEqual(outcome['state'],'done',outcome)
  row,data=next(iter(self.google.files.values()));self.assertEqual(row['parents'],['appDataFolder']);self.assertEqual(row['appProperties']['plmsBackup'],g.MARKER)
  payload=g.decode_backup(data);self.assertEqual(payload['data']['management']['employees'][0]['name'],'Employee');self.assertTrue(payload['data']['users'][0]['password'].startswith('pbkdf2-'))
  self.assertNotIn('REFRESH-PRIVATE',g.compact(payload));self.assertNotIn('ACCESS-PRIVATE',g.compact(self.cloud.public_status()))
  job=wait(self.cloud,self.call('drive_download',fileId=row['id']));self.assertEqual(job['state'],'done',job)
  restored=self.call('restore',state=job['result']['payload']['data']);self.assertEqual(restored['state']['patients'][0]['name'],'Patient One')
  self.assertEqual(len(list((self.path.parent.parent/'Backup').glob('PLMS-Google-*.json'))),1)
 def test_offline_retains_local_copy_and_last_success(self):
  self.cloud.config['lastSuccess']='2020-01-01T00:00:00Z';self.google.offline=True
  outcome=wait(self.cloud,self.cloud.backup());self.assertEqual(outcome['state'],'error');self.assertEqual(self.cloud.public_status()['lastSuccess'],'2020-01-01T00:00:00Z')
  self.assertEqual(len(list((self.path.parent.parent/'Backup').glob('*.json'))),1);self.assertTrue(self.cloud.public_status()['lastError'])
 def test_bad_upload_checksum_is_not_success(self):
  self.google.corrupt=True;outcome=wait(self.cloud,self.cloud.backup());self.assertEqual(outcome['state'],'error');self.assertFalse(self.cloud.public_status()['lastSuccess'])
 def test_retention_only_deletes_this_device_backups(self):
  self.cloud.config['retain']=3
  for i in range(5):
   own={'id':'old'+str(i),'createdTime':'2000-01-0'+str(i+1),'appProperties':{'plmsBackup':g.MARKER,'deviceId':self.cloud.config['deviceId']}}
   self.google.files[own['id']]=(own,b'old')
  other={'id':'other','createdTime':'1999','appProperties':{'plmsBackup':g.MARKER,'deviceId':'other-device'}};self.google.files['other']=(other,b'other')
  outcome=wait(self.cloud,self.cloud.backup());self.assertEqual(outcome['state'],'done',outcome);self.assertIn('other',self.google.files);self.assertEqual(len(self.google.files),4)
 def test_scheduler_due_retry_busy_and_restart(self):
  self.cloud.settings(True,1,3);self.google.offline=True
  self.assertTrue(self.cloud.tick(100000));wait(self.cloud,{'jobId':self.cloud.job['id']});self.assertFalse(self.cloud.tick(100001));self.assertTrue(self.cloud.tick(100301));wait(self.cloud,{'jobId':self.cloud.job['id']})
  restarted=g.GoogleDrive(self.path,self.store,self.google);self.assertTrue(restarted.public_status()['enabled']);self.assertEqual(restarted.config['hours'],1)
  restarted.config['enabled']=False;self.assertFalse(restarted.tick(999999))
 def test_disconnect_is_local_and_preserves_cloud_files(self):
  wait(self.cloud,self.cloud.backup());self.cloud.disconnect();self.assertFalse(self.cloud.public_status()['connected']);self.assertEqual(len(self.google.files),1)
  self.assertFalse(any('revoke' in call[1] for call in self.google.calls))
 def test_invalid_settings_or_web_client_rejected(self):
  for args in [(True,2,14),(True,24,0),(True,True,14),(True,24,True),('yes',24,14)]:
   with self.assertRaises(g.DriveError):self.cloud.settings(*args)
  with self.assertRaises(g.DriveError):self.cloud.configure({'web':CLIENT['installed']})
  before=copy.deepcopy(self.store.value);self.cloud.configure(CLIENT);self.assertEqual(self.store.value['refresh_token'],before['refresh_token'])
 def test_download_rejects_regular_drive_or_tampered_files(self):
  self.google.files['evil']=({'id':'evil','spaces':['drive'],'appProperties':{'plmsBackup':g.MARKER}},b'anything')
  self.assertEqual(wait(self.cloud,self.cloud.download('evil'))['state'],'error')
  wait(self.cloud,self.cloud.backup());ident=next(k for k in self.google.files if k!='evil');self.google.corrupt=True
  self.assertEqual(wait(self.cloud,self.cloud.download(ident))['state'],'error')
  for ident in ['../secret','?key=bad','']:
   with self.assertRaises(g.DriveError):self.cloud.download(ident)
 def test_non_admin_and_expired_session_denied_for_every_action(self):
  self.api.db.execute("UPDATE app_state SET body=json_set(body,'$.users[0].role','Viewer')")
  for action in g.ACTIONS:
   with self.assertRaises(m.ApiError):self.call(action)
   with self.assertRaises(m.ApiError):self.api.handle({'action':action,'token':'forged'})
 def test_oauth_pkce_state_and_system_browser(self):
  checked={}
  def browser(url):
   parsed=urllib.parse.urlsplit(url);query=urllib.parse.parse_qs(parsed.query);checked.update(query);self.assertEqual(parsed.hostname,'accounts.google.com');self.assertEqual(query['code_challenge_method'],['S256']);self.assertEqual(query['scope'],[g.SCOPE])
   def callback():
    wrong=query['redirect_uri'][0]+'?state=bad&code=stolen'
    try:urllib.request.urlopen(wrong,timeout=3)
    except Exception:pass
    response=urllib.request.urlopen(query['redirect_uri'][0]+'?'+urllib.parse.urlencode({'state':query['state'][0],'code':'GOOD'}),timeout=3);response.read();response.close()
   threading.Thread(target=callback,daemon=True).start();return True
  self.cloud.opener=browser;outcome=wait(self.cloud,self.cloud.connect());self.assertEqual(outcome['state'],'done',outcome)
  token_calls=[call for call in self.google.calls if call[1]==g.TOKEN_URL];parameters=urllib.parse.parse_qs(token_calls[-1][3].decode());verifier=parameters['code_verifier'][0]
  challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode();self.assertEqual(checked['code_challenge'],[challenge]);self.assertEqual(self.cloud.public_status()['email'],'lab@example.test')
 def test_oauth_cancel_does_not_replace_connection(self):
  self.cloud.opener=lambda url: True;job=self.cloud.connect();time.sleep(.03);self.cloud.cancel_connect();result=wait(self.cloud,job)
  self.assertEqual(result['state'],'error');self.assertIn('canceled',result['error']);self.assertEqual(self.store.value['refresh_token'],'REFRESH-PRIVATE')
 def test_dpapi_roundtrip_on_windows_and_no_plaintext_fallback(self):
  if os.name=='nt':self.assertEqual(g.protect_windows(g.protect_windows(b'refresh-secret'),True),b'refresh-secret')
  else:
   with self.assertRaises(g.DriveError):g.protect_windows(b'secret')
 def test_credential_file_is_not_app_state_or_backup(self):
  calls=[]
  def codec(data,decrypt=False):
   calls.append(decrypt)
   return data[7:] if decrypt else b'SEALED:'+data
  store=g.CredentialStore(self.path,codec,pathlib.Path(self.tmp.name)/'private');store.write({'refresh_token':'private'})
  self.assertEqual(store.read(),{'refresh_token':'private'});self.assertEqual(calls,[False,True]);self.assertNotIn('private',self.api.db.execute('SELECT body FROM app_state').fetchone()[0])
  with mock.patch.object(self.store,'read',side_effect=g.DriveError('Bad DPAPI file')):
   recovered=g.GoogleDrive(self.path,self.store,self.google)
   self.assertFalse(recovered.public_status()['connected']);self.assertIn('Set up',recovered.public_status()['lastError'])
   recovered.configure(CLIENT);self.assertTrue(recovered.public_status()['configured'])

 def test_failed_settings_or_disconnect_write_does_not_change_active_config(self):
  before=copy.deepcopy(self.cloud.config)
  with mock.patch.object(self.store,'write',side_effect=g.DriveError('Disk full')):
   for operation in [lambda:self.cloud.settings(True,6,3),self.cloud.disconnect,lambda:self.cloud.configure({'installed':{**CLIENT['installed'],'client_id':'9876543210-other.apps.googleusercontent.com'}})]:
    with self.assertRaises(g.DriveError):operation()
    self.assertEqual(self.cloud.config,before)

 def test_new_database_does_not_reuse_old_google_authorization(self):
  other=pathlib.Path(self.tmp.name)/'fresh.sqlite3'
  fresh=g.GoogleDrive(other,self.store,self.google)
  self.assertFalse(fresh.public_status()['connected']);self.assertFalse(fresh.public_status()['enabled'])
  self.assertNotEqual(fresh.config['databaseId'],self.cloud.config['databaseId'])

 def test_cross_runtime_integrity_fixture(self):
  payload=json.loads((pathlib.Path(__file__).parents[2]/'frontend/fixtures/google-drive-integrity.json').read_text())
  self.assertEqual(g.bundle_digest(payload),payload['integrity']['value'])

 def test_gzip_limit_and_integrity_validation(self):
  with mock.patch.object(g,'MAX_BACKUP',10):
   with self.assertRaises(g.DriveError):g.decode_backup(gzip.compress(b'x'*11))
  with self.assertRaises(g.DriveError):g.decode_backup(b'not json')
  payload,raw=g.build_backup(self.path);payload['data']['patients'][0]['name']='tampered'
  with self.assertRaises(g.DriveError):g.decode_backup(g.compact(payload).encode())

if __name__=='__main__':unittest.main()

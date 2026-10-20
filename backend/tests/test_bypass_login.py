import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from server import Backend,ApiError
from test_backend import fixture

class BypassLoginTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'plms.sqlite3';self.api=Backend(self.path)
  self.auth=self.api.handle({'action':'bootstrap','username':'U001','password':'123','state':fixture()})
 def tearDown(self):self.api.db.close();self.temp.cleanup()
 def toggle(self,value):
  current=self.api.handle({'action':'read','token':self.auth['token']});current['state']['users'][0]['bypassLogin']=value
  return self.api.handle({'action':'commit','token':self.auth['token'],'revision':current['revision'],'state':current['state']})
 def test_default_off_and_enable_survives_reopen(self):
  self.assertIsNone(self.api.handle({'action':'bypass_login'}));updated=self.toggle(True)
  self.assertTrue(updated['state']['users'][0]['bypassLogin']);self.api.db.close();self.api=Backend(self.path)
  bypass=self.api.handle({'action':'bypass_login'});self.assertEqual(bypass['userId'],'U001');self.assertTrue(bypass['token'])
  self.assertTrue(self.api.handle({'action':'read','token':bypass['token']})['state']['users'][0]['bypassLogin'])
  events=self.api.handle({'action':'audit','token':bypass['token']})['events'];self.assertTrue(any('Bypass Login' in e['action'] for e in events))
 def test_disabling_reinstates_manual_login(self):
  self.toggle(True);self.assertTrue(self.api.handle({'action':'bypass_login'})['token']);self.toggle(False)
  self.assertIsNone(self.api.handle({'action':'bypass_login'}));self.assertTrue(self.api.handle({'action':'login','username':'Noman Tahir','password':'123'})['token'])
 def test_bypass_session_preserves_password_checks_and_logout(self):
  self.toggle(True);bypass=self.api.handle({'action':'bypass_login'})
  with self.assertRaises(ApiError):self.api.handle({'action':'password','token':bypass['token'],'current':'wrong','password':'A stronger replacement password'})
  self.api.handle({'action':'logout','token':bypass['token']})
  with self.assertRaises(ApiError):self.api.handle({'action':'read','token':bypass['token']})
 def test_inactive_and_non_privileged_accounts_cannot_auto_login(self):
  self.toggle(True);revision,state=self.api.load();state['users'][0]['status']='Inactive'
  import json
  self.api.db.execute('UPDATE app_state SET body=? WHERE id=1',(json.dumps(state),));self.assertIsNone(self.api.handle({'action':'bypass_login'}))
  state['users'][0]['status']='Active';state['users'][0]['role']='Technologist';self.api.db.execute('UPDATE app_state SET body=? WHERE id=1',(json.dumps(state),));self.assertIsNone(self.api.handle({'action':'bypass_login'}))
 def test_unprivileged_cannot_configure_bypass_even_with_user_edit_permission(self):
  user={'id':'T','role':'Technologist'};state=self.auth['state'];state['userPermissionOverrides']={'T':{'users.edit':True,'users.manage_bypass_login':True}}
  old=copy.deepcopy(state['users'][0]);new={**old,'bypassLogin':True}
  with self.assertRaises(ApiError):self.api.user_change(user,state,old,new)
 def test_fresh_database_still_requires_first_manual_login(self):
  with tempfile.TemporaryDirectory() as folder:
   other=Backend(Path(folder)/'fresh.sqlite3')
   try:self.assertIsNone(other.handle({'action':'bypass_login'}));self.assertFalse(other.initialized())
   finally:other.db.close()

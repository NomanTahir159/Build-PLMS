import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from server import Backend, ApiError
from test_backend import fixture

class PackageDefaultsTests(unittest.TestCase):
 def test_both_login_names_work_on_fresh_install_and_after_restart(self):
  for login in ('U001','Noman Tahir',' noman tahir '):
   with self.subTest(login=login), tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'plms.sqlite3';api=Backend(path)
    try:
     auth=api.handle({'action':'bootstrap','username':login,'password':'123','state':fixture()})
     self.assertEqual([(u['id'],u['name']) for u in auth['state']['users']],[('U001','Noman Tahir')])
     self.assertEqual(api.db.execute('SELECT COUNT(*) FROM credentials').fetchone()[0],1)
     for alias in ('u001','Noman Tahir'):
      self.assertEqual(api.handle({'action':'login','username':alias,'password':'123'})['userId'],'U001')
     api.db.close();api=Backend(path)
     self.assertEqual(api.handle({'action':'login','username':'Noman Tahir','password':'123'})['userId'],'U001')
    finally:api.db.close()
 def test_invalid_first_login_creates_no_account(self):
  with tempfile.TemporaryDirectory() as folder:
   api=Backend(Path(folder)/'plms.sqlite3')
   try:
    with self.assertRaises(ApiError):api.handle({'action':'bootstrap','username':'Noman Tahir','password':'wrong','state':fixture()})
    self.assertFalse(api.initialized())
   finally:api.db.close()

class ProcessingBypassDesktopTests(unittest.TestCase):
 def test_enabled_admin_can_book_direct_result_order(self):
  with tempfile.TemporaryDirectory() as folder:
   api=Backend(Path(folder)/'plms.sqlite3')
   try:
    auth=api.handle({'action':'bootstrap','username':'U001','password':'123','state':fixture()});token=auth['token']
    def commit(data,rev):return api.handle({'action':'commit','token':token,'state':data,'revision':rev})
    auth['state']['users'][0]['bypassProcessing']=True;current=commit(auth['state'],auth['revision'])
    data=copy.deepcopy(current['state']);data['patients'].append({'lab':'3','name':'Bypass Test'})
    bypass={'enabled':True,'at':'2026-10-15T00:00:00Z','actor':{'id':'U001','name':'Noman Tahir','role':'Administrator'}}
    data['orders'].append({'lab':'3','patient':'Bypass Test','tests':['Hemoglobin'],'department':'Hematology','sample':'Received','status':'In Progress','processingBypass':bypass,'testStates':{'Hemoglobin':{'sampleStatus':'Received'}}})
    result=commit(data,current['revision']);self.assertEqual(result['state']['orders'][-1]['sample'],'Received')
    self.assertNotEqual(result['state']['orders'][-1].get('reportStatus'),'Approved')
   finally:api.db.close()
 def test_disabled_bypass_rejected_by_database(self):
  with tempfile.TemporaryDirectory() as folder:
   api=Backend(Path(folder)/'plms.sqlite3')
   try:
    auth=api.handle({'action':'bootstrap','username':'U001','password':'123','state':fixture()});data=auth['state'];data['patients'].append({'lab':'3','name':'Invalid Bypass'})
    data['orders'].append({'lab':'3','tests':['Hemoglobin'],'department':'Hematology','processingBypass':{'actor':{'id':'U001'}}})
    with self.assertRaises(ApiError):api.handle({'action':'commit','token':auth['token'],'state':data,'revision':auth['revision']})
   finally:api.db.close()

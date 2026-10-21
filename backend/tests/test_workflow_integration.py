import copy, unittest
import test_backend as fixtures
m=fixtures.m

class WorkflowIntegrationTests(unittest.TestCase):
 setUp=fixtures.BackendTests.setUp
 tearDown=fixtures.BackendTests.tearDown
 call=fixtures.BackendTests.call
 account=fixtures.BackendTests.account
 def setup_order(self,profiles=False):
  st=self.call('read');data=st['state'];o=data['orders'][0]
  o.update(sample='Collected',status='Pending',reportStatus='In Progress',registeredAt='2026-10-09',testStates={})
  data['patients'][0]['status']='Pending'
  if profiles:
   data['catalog'][0]['profiles']=['A','B'];o['tests']=['A','B'];o['sample']='Received';o['status']='In Progress';o['testStates']={'A':{'sampleStatus':'Received','resultStatus':'Approved'},'B':{'sampleStatus':'Received','resultStatus':'Processed'}}
  self.call('commit',state=data,revision=st['revision'])
  if profiles:
   st=self.call('read');data=st['state'];data['results']['1']={'A::HB':'12','B::HB':'13'};self.call('commit',state=data,revision=st['revision'])
 def test_receive_without_order_edit_or_result_approval(self):
  self.setup_order();tech=self.account('Technologist');st=self.call('read',tech);data=st['state'];o=data['orders'][0]
  o.update(sample='Received',status='In Progress',bookingDateLockedAt='2026-10-09T10:00:00Z',bookingDateLockReason='Sample received')
  o['testStates']={'Hemoglobin':{'sampleStatus':'Received','receivedAt':'2026-10-09T10:00:00Z','sampleHistory':[{'action':'Received'}]}}
  data['patients'][0]['status']='In Progress'
  self.call('commit',tech,state=data,revision=st['revision'])
 def test_save_result_date_without_booking_permission(self):
  self.setup_order();tech=self.account('Technologist');st=self.call('read',tech);data=st['state'];o=data['orders'][0]
  o.update(sample='Received',status='In Progress',resultEnteredAt='2026-10-09T10:00:00Z',bookingDateLockedAt='2026-10-09T10:00:00Z',bookingDateLockReason='Result entry',tat='In Progress')
  o['testStates']={'Hemoglobin':{'sampleStatus':'Received','resultStatus':'All','resultEnteredAt':o['resultEnteredAt']}}
  data['patients'][0]['status']='In Progress';data['results']['1']['HB']='15'
  self.call('commit',tech,state=data,revision=st['revision'])
  st=self.call('read',tech);data=st['state'];data['orders'][0]['testStates']['Hemoglobin']['resultEnteredAt']='2026-10-10T10:00:00Z';data['orders'][0]['resultEnteredAt']='2026-10-10T10:00:00Z'
  self.call('commit',tech,state=data,revision=st['revision'])
 def test_contextual_edit_does_not_require_amending_other_profile(self):
  self.setup_order(True);tech=self.account('Technologist');st=self.call('read',tech);data=st['state'];data['results']['1']['B::HB']='20'
  self.call('commit',tech,state=data,revision=st['revision']);self.assertEqual(self.call('read')['state']['results']['1']['A::HB'],'12')
 def test_unknown_context_and_approved_context_remain_protected(self):
  self.setup_order(True);tech=self.account('Technologist');st=self.call('read',tech)
  for code in ['Unknown::HB','A::HB']:
   data=copy.deepcopy(st['state']);data['results']['1'][code]='99'
   with self.assertRaises(m.ApiError):self.call('commit',tech,state=data,revision=st['revision'])
 def test_global_approval_cannot_bypass_permission(self):
  self.setup_order();tech=self.account('Technologist');st=self.call('read',tech);data=st['state'];data['orders'][0]['reportStatus']='Approved'
  with self.assertRaises(m.ApiError):self.call('commit',tech,state=data,revision=st['revision'])
 def test_rejecting_last_item_finalizes_existing_approved_item(self):
  self.setup_order(True)
  st=self.call('read');data=st['state'];data['rolePermissions']['Technologist']['results.reject']=True;self.call('commit',state=data,revision=st['revision'])
  tech=self.account('Technologist');st=self.call('read',tech);data=st['state'];o=data['orders'][0]
  o['testStates']['B'].update(resultStatus='Rejected',resultRejectedAt='2026-10-09T10:00:00Z');o.update(reportStatus='Approved',status='Reported',reportedAt='2026-10-09T10:00:00Z',approvedBy='Consultant Pathologist',tat='Completed')
  data['patients'][0]['status']='Reported'
  self.call('commit',tech,state=data,revision=st['revision'])
 def test_edit_only_verifier_can_return_incomplete_results_to_entry(self):
  self.setup_order(True)
  st=self.call('read');data=st['state'];data['rolePermissions']['Technologist']['results.enter']=False;self.call('commit',state=data,revision=st['revision'])
  tech=self.account('Technologist');st=self.call('read',tech);data=st['state'];data['orders'][0]['testStates']['B']['resultStatus']='All';data['results']['1']['B::HB']=''
  self.call('commit',tech,state=data,revision=st['revision'])
  stored=self.call('read')['state'];self.assertEqual(stored['orders'][0]['testStates']['B']['resultStatus'],'All');self.assertEqual(stored['results']['1']['B::HB'],'')
 def test_scoped_result_notes_and_save_timestamp_without_order_edit(self):
  self.setup_order();tech=self.account('Technologist');st=self.call('read');data=st['state'];o=data['orders'][0]
  o.update(sample='Received',status='In Progress',testStates={'Hemoglobin':{'sampleStatus':'Received','resultStatus':'All'}})
  self.call('commit',state=data,revision=st['revision'])
  st=self.call('read',tech);data=st['state'];o=data['orders'][0]
  notes={'scopeVersion':2,'items':{'"Hemoglobin"':{'comments':'Clinical correlation advised.','remarks':'Reference interval varies.','instructions':'','advise':'','templateSelections':{},'updatedAt':'2026-10-21T08:00:00Z'}}}
  o['resultReportContent']=copy.deepcopy(notes);o['testStates']['Hemoglobin']['resultSavedAt']='2026-10-21T08:00:00Z'
  data['results']['1']['HB']='15.0'
  self.call('commit',tech,state=data,revision=st['revision'])
  self.api.db.close();self.api=m.Backend(self.path);auth=self.api.handle({'action':'login','username':'Technologist','password':fixtures.PASSWORD})
  self.assertEqual(auth['state']['orders'][0]['resultReportContent'],notes)
  self.assertEqual(auth['state']['results']['1']['HB'],'15.0')

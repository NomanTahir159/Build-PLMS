const fs=require('fs'),vm=require('vm'),assert=require('assert'),html=fs.readFileSync(require('path').resolve(__dirname,'../../src/System/index.html'),'utf8').replace(/\r\n?/g,'\n');
function fn(n,next){const a=html.indexOf('function '+n+'('),b=html.indexOf('\nfunction '+next+'(',a);assert(a>=0&&b>a);return html.slice(a,b)}
const c={Date,Set,Number,String,Math,Array,console,state:{orders:[],results:{}},isApprovedOrder:()=>false,bookedItemTests:()=>[{code:'C'}],resultValueFor:(o,k,code)=>c.state.results[o.lab]?.[k+'::'+code],requirePermission:()=>true,persist(){},renderAll(){},toast(){},clearResultBatch(){},consumeCurrentResultSessionItem(){},canResultAction:()=>true,resultVerificationEligible:()=>true,syncOrderResolution:()=>c.resolutions++,resolutions:0};
vm.createContext(c);const run=s=>vm.runInContext(s,c);
run(fn('orderHasProcessingEvidence','currentOrderDateLocked'));run(fn('orderWorkflowStatus','orderPermissions'));run(fn('workflowItemState','sampleItemStatus'));run(fn('sampleItemStatus','sampleItemTime'));run(fn('setSampleItemStatus','syncOverallSampleStatus'));run(html.split('\n').find(l=>l.startsWith('function syncOverallSampleStatus(')));run(fn('resultItemStatus','resultItemTime'));run(fn('requestFreshSampleForResult','askFreshSampleReason'));run(fn('repeatCurrentResultEntry','navigateResultRecord'));run(fn('reperformCurrentResultEntry','retestCurrentResultEntry'));run(fn('resultAction','printResultItem'));run(fn('rejectCurrentResultEntry','reperformCurrentResultEntry'));
const fresh=()=>({lab:'L',tests:['A','B'],sample:'Collected',status:'Pending'});
c.o=fresh();c.state.orders=[c.o];c.orderByLab=()=>c.o;
assert.equal(run('finalizedOrderDateLocked(o)'),false);
run("setSampleItemStatus(o,'A','Received')");assert.equal(run('orderWorkflowStatus(o)'),'Processing');assert.equal(run('finalizedOrderDateLocked(o)'),true);assert.equal(run("sampleItemStatus(o,'B')"),'Collected');const first=c.o.bookingDateLockedAt;
run("setSampleItemStatus(o,'B','Rejected');setSampleItemStatus(o,'B','Resampled')");assert.equal(c.o.bookingDateLockedAt,first);assert.equal(run('finalizedOrderDateLocked(o)'),true);
run("setSampleItemStatus(o,'B','Received')");assert.equal(c.o.sample,'Received');
c.state.results.L={'A::C':'12'};run("requestFreshSampleForResult(o,'A','Repeat specimen')");assert.equal(c.o.testStates.A.freshSampleOriginalValues.C,'12');assert.equal(run("sampleItemStatus(o,'B')"),'Received');assert.equal(c.o.testStates.A.sampleStatus,'Fresh Sample Requested');assert.equal(run('finalizedOrderDateLocked(o)'),true);
run("setSampleItemStatus(o,'A','Rejected');setSampleItemStatus(o,'A','Resampled');setSampleItemStatus(o,'A','Received')");assert.equal(c.o.testStates.A.resultStatus,'Fresh Sample');assert.equal(c.o.sample,'Received');
c.currentResultLab='L';c.currentResultLabel='A';run('repeatCurrentResultEntry()');assert.equal(c.o.testStates.A.sampleStatus,'Resampled');assert.equal(c.o.testStates.A.resultStatus,'Repeated');assert.equal(run('finalizedOrderDateLocked(o)'),true);
run("setSampleItemStatus(o,'A','Received');reperformCurrentResultEntry()");assert.equal(c.o.testStates.A.sampleStatus,'Received');assert.equal(c.o.testStates.A.resultStatus,'Repeated');
run('rejectCurrentResultEntry()');assert.equal(c.o.testStates.A.resultStatus,'Rejected');assert.equal(c.o.testStates.A.sampleStatus,'Received');assert(c.resolutions>0);
// Historical and mixed states remain locked even without the new permanent marker.
for(const field of ['receivedAt','sampleRejectedAt','resampledAt','processedAt','submittedAt','approvedAt','repeatedAt','freshSampleRequestedAt']){c.o=fresh();c.o.testStates={A:{[field]:'2026-10-09T10:00:00Z'}};assert.equal(run('finalizedOrderDateLocked(o)'),true,field)}
for(const status of ['Received','Rejected','Resampled','Fresh Sample Requested','Fresh Sample']){c.o=fresh();c.o.testStates={A:{sampleStatus:status}};assert.equal(run('finalizedOrderDateLocked(o)'),true,status)}
for(const status of ['Processed','Restored','Repeated','Approved','Rejected','Fresh Sample Requested','Fresh Sample']){c.o=fresh();c.o.testStates={A:{resultStatus:status}};assert.equal(run('finalizedOrderDateLocked(o)'),true,status)}
c.o=fresh();c.o.testStates={A:{sampleStatus:'Collected',sampleHistory:[{action:'Received',at:'old'}]}};assert.equal(run('finalizedOrderDateLocked(o)'),true);
c.o=fresh();c.o.orderStatus='Pending';c.o.testStates={A:{sampleStatus:'Received'}};assert.equal(run('orderWorkflowStatus(o)'),'Processing');
c.o=fresh();delete c.state.results.L;assert.equal(run('finalizedOrderDateLocked(o)'),false);
console.log('Passed received/mixed/rejected/resampled/repeated/fresh-specimen transitions, historical date locks and contextual snapshots.');

const fs=require('fs'),vm=require('vm'),assert=require('assert');const html=fs.readFileSync(require('path').resolve(__dirname,'../../src/System/index.html'),'utf8').replace(/\r\n?/g,'\n');
function fn(n,next){const a=html.indexOf('function '+n+'('),b=html.indexOf('\nfunction '+next+'(',a);assert(a>=0&&b>a);return html.slice(a,b)}
const order={lab:'1',tests:['CBC'],registeredAt:'2026-10-09T13:00:00.000Z',sample:'Received',testStates:{CBC:{sampleStatus:'Received',resultStatus:'All'}}};
const c={Date,Set,Number,String,Math,Array,console,state:{orders:[order],patients:[{lab:'1',registeredAt:order.registeredAt,date:'09-Oct-2026'}],results:{}},currentResultLab:'1',currentResultLabel:'CBC',orderFormMode:'order',fLab:{value:'1'},allowed:true,editable:true,complete:true,collects:0,persists:0,toast:s=>c.message=s,document:{getElementById:()=>null,addEventListener(){},querySelector:()=>null},window:{addEventListener(){}},orderByLab:l=>l==='1'?order:null,patientByLab:()=>c.state.patients[0],requirePermission:()=>c.allowed,orderPermissions:()=>({edit:c.editable}),workflowItemState:(o,k)=>o.testStates[k]||{},resultSampleEligible:(o,k)=>o.testStates[k]?.sampleStatus==='Received',isApprovedOrder:()=>false,isBookedItemProcessed:()=>c.complete,collectResultValues:()=>{c.collects++;return {'CBC::CBC':'12'}},bookedItemTests:()=>[{code:'CBC'}],isParameterExcluded:()=>false,saveResultReportContent(){},syncOrderResolution(){},renderAll(){},persist(){c.persists++},validateOrder:()=>true,validateCompleteOrder:()=>true,closeModal(){},formatResultEntryDate:d=>d.toISOString(),resultEntryDate:{textContent:''}};
c.contextualResultKey=(key,code)=>key+'::'+code;c.syncOverallSampleStatus=()=>{};
c.sampleItemStatus=(o,k)=>o.testStates[k]?.sampleStatus;
c.orderWorkflowStatus=o=>o?.orderStatus||o?.status||'Pending';
c.plmsAdministratorHasFullAccess=()=>false;c.plmsPrepareEditedLab=()=>true;vm.createContext(c);const run=s=>vm.runInContext(s,c);
run(fn('parsePlmsRecordDate','standardOrderDate'));const a=html.indexOf('/* Order booking date is draft'),b=html.indexOf('function orderDateText()',a);run(html.slice(a,b));run(fn('resultItemStatus','resultItemTime'));run(fn('canResultAction','requestFreshSampleForResult'));run(fn('commitCurrentResults','approveCurrentResultEntry'));run(fn('commitOrder','saveOrder'));run(fn('completeOrder','refreshNewOrder'));
run("selectedResultDate=new Date(2026,9,8,23,59);bookingCalendarContext='result'");let before=JSON.stringify(c.state);
assert.equal(run('commitCurrentResults(false,false)'),false);assert.equal(c.collects,0);assert.equal(c.persists,0);assert.equal(JSON.stringify(c.state),before);assert.equal(run("chooseOrderBookingDate('2026-10-08')"),false);
// Calendar-day rule allows the order day even if its recorded time is later.
run('selectedResultDate=new Date(2026,9,9,0,0)');assert.equal(run('commitCurrentResults(false,false)'),true);assert.equal(c.persists,1);
run('selectedResultDate=new Date(2026,9,10,12,0)');assert.equal(run('commitCurrentResults(false,true)'),true);assert.equal(order.testStates.CBC.resultStatus,'Processed');assert.equal(order.testStates.CBC.processedAt,run('selectedResultDate.toISOString()'));
assert.equal(run("canResultAction(state.orders[0],'CBC','approve')"),true);c.complete=false;assert.equal(run("canResultAction(state.orders[0],'CBC','approve')"),false);c.complete=true;
// Reverse chronology is blocked before modifying order or patient fields.
run('selectedOrderDate=new Date(2026,9,11)');before=JSON.stringify(c.state);assert.equal(run('commitOrder()'),false);run('completeOrder()');assert.equal(JSON.stringify(c.state),before);
run('selectedOrderDate=new Date(2026,9,9)');assert.equal(run('validateOrderBookingDate()'),false);c.editable=false;assert.equal(run('validateOrderBookingDate()'),false);c.editable=true;
// Rejected/approved/unreceived and missing profile contexts are blocked.
for(const status of ['Rejected','Approved']){order.testStates.CBC.resultStatus=status;assert.equal(run('commitCurrentResults(false,false)'),false)}order.testStates.CBC.resultStatus='Processed';order.testStates.CBC.sampleStatus='Collected';assert.equal(run('commitCurrentResults(false,false)'),false);order.testStates.CBC.sampleStatus='Received';c.currentResultLabel='';assert.equal(run('commitCurrentResults(false,false)'),false);c.currentResultLabel='CBC';c.allowed=false;assert.equal(run('commitCurrentResults(false,false)'),false);c.allowed=true;
// The final report-version wrapper rejects chronology before collecting/mutating result references.
c.window=c;const start=html.indexOf('window.commitCurrentResults=function()'),end=html.indexOf(';\nconst priorRender',start)+1;const core=c.commitCurrentResults;c.priorCommit=core;c.versions=()=>[];run(html.slice(start,end));run('selectedResultDate=new Date(2026,9,8)');const n=c.collects;assert.equal(run('commitCurrentResults(false,false)'),false);assert.equal(c.collects,n);
assert(html.includes('prefix==="results"?parsePlmsRecordDate(resultItemTime('));
console.log(process.env.TZ+': chronology, same-day entry, reverse order edits, sample/status/permission gates, complete approval and outer-save guard passed.');
// Saving one received profile cannot receive the remaining unreceived profiles.
run(html.split('\n').find(l=>l.startsWith('function syncOverallSampleStatus(')));
run(html.split('\n').find(l=>l.startsWith('function sampleItemStatus(')));
order.tests.push('Other');order.sample='Collected';run('selectedResultDate=new Date(2026,9,10,12,0)');
assert.equal(run('priorCommit(false,false)'),true);
assert.equal(run("sampleItemStatus(state.orders[0],'Other')"),'Collected');assert.equal(order.sample,'Collected');
console.log(process.env.TZ+': Profile-key submission and mixed sample-status preservation passed.');
// Finalized/rejected orders lock the visible control and direct picker/save paths.
const trigger={disabled:false,setAttribute(){}};c.document.getElementById=id=>id==='orderBookingDateTrigger'?trigger:null;
run("bookingCalendarContext='order';selectedOrderDate=new Date(2026,9,9)");
for(const status of ['Rejected','Completed','Reported']){
 order.status=status;run('syncOrderDateControl()');assert.equal(trigger.disabled,true);
 const draft=run('selectedOrderDate.toISOString()');assert.equal(run("chooseOrderBookingDate('2026-10-10')"),false);assert.equal(run('selectedOrderDate.toISOString()'),draft);
 run("openBookingCalendar('order')");assert.equal(run('validateOrderBookingDate()'),false);
}
order.status='Pending';run('syncOrderDateControl()');assert.equal(trigger.disabled,true);
order.orderStatus='Completed';run('syncOrderDateControl()');assert.equal(trigger.disabled,true);delete order.orderStatus;
console.log(process.env.TZ+': Rejected/completed date control, direct selection and save locks passed.');

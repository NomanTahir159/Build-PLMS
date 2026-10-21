const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync(require('path').resolve(__dirname,'../../src/System/index.html'),'utf8');
function fn(name){const m=html.match(new RegExp('function '+name+'\\([^]*?\\n\\}'));assert(m,name);return m[0]}
const c={resultSessionMode:()=>c.order&&['Processed','Restored'].includes(c.order.testStates[c.currentResultLabel]?.resultStatus)?'verify':'entry',Date,window:{},currentResultLab:'1',currentResultLabel:'Test',selectedResultDate:new Date(),state:{results:{},patients:[]},values:{},tests:[{code:'A'}],excluded:new Set(),denied:new Set(),messages:[],persisted:0,consumed:0,
validateResultCommitContext:()=>true,requirePermission:p=>!c.denied.has(p),resultItemStatus:o=>o.testStates.Test?.resultStatus||'All',sampleItemStatus:()=> 'Received',collectResultValues:()=>c.values,bookedItemTests:()=>c.tests,isParameterExcluded:(o,code)=>c.excluded.has(code),contextualResultKey:(label,code)=>label==='Profile'?'Profile::'+code:code,saveResultReportContent:()=>{},lockOrderBookingDate:()=>{},syncOverallSampleStatus:()=>{},syncOrderResolution:()=>{},patientByLab:()=>null,persist:()=>c.persisted++,renderAll:()=>{},toast:m=>c.messages.push(m),consumeCurrentResultSessionItem:()=>c.consumed++};
c.orderByLab=()=>c.order;
vm.createContext(c);vm.runInContext(fn('commitCurrentResults')+'\n'+fn('saveResults'),c);
function reset(values,tests=[{code:'A'}],label='Test',saved={}){c.currentResultLabel=label;c.values=values;c.tests=tests;c.order={lab:'1',tests:[label],testStates:{}};c.state.results={'1':saved};c.excluded.clear();c.denied.clear();c.persisted=0;c.consumed=0;c.messages=[];}
function blocked(){assert.equal(c.commitCurrentResults(true,true),false);assert.equal(c.persisted,0);assert.equal(c.order.testStates[c.currentResultLabel],undefined);assert(c.messages.length)}
reset({A:''});blocked();reset({A:'   '});blocked();reset({A:null});blocked();reset({});blocked();
reset({'Profile::A':'3','Profile::B':''},[{code:'A'},{code:'B'}],'Profile');blocked();
reset({A:''},[{code:'A'}],'Test',{A:'old value'});blocked();
reset({A:'0'});assert(c.commitCurrentResults(true,true));assert.equal(c.order.testStates.Test.resultStatus,'Processed');
reset({A:'Non-Reactive'});assert(c.commitCurrentResults(true,true));
reset({'Profile::A':'3','Profile::B':'4'},[{code:'A'},{code:'B'}],'Profile');assert(c.commitCurrentResults(true,true));assert.equal(c.order.testStates.Profile.resultStatus,'Processed');
reset({'Profile::A':'3','Profile::B':''},[{code:'A'},{code:'B'}],'Profile');c.excluded.add('B');assert(c.commitCurrentResults(true,true));
reset({A:''});assert(c.commitCurrentResults(true,false));assert.equal(c.order.testStates.Test.resultStatus,'All','Draft save must remain in Results Entry');
reset({A:''});c.saveResults(true);assert.equal(c.consumed,0,'Blocked batch item must not advance');assert.equal(c.persisted,0);
reset({A:'4'});c.denied.add('results.submit');assert.equal(c.commitCurrentResults(true,true),false);assert.equal(c.persisted,0);
console.log('PASS: blank, whitespace, null, no fields, partial profile and clearing an old value cannot submit. Zero/qualitative/complete profiles submit; excluded parameters skipped; draft stays in Results Entry; blocked batch stays open; submit permission enforced.');

for(const status of ['Processed','Restored']){
 reset({A:''});c.order.testStates.Test={resultStatus:status,submittedAt:'2026-10-15',processedAt:'2026-10-15',restoredAt:'2026-10-15'};assert(c.commitCurrentResults(true,false));assert.equal(c.order.testStates.Test.resultStatus,'All');assert(!c.order.testStates.Test.submittedAt);assert(!c.order.testStates.Test.processedAt);assert(!c.order.testStates.Test.restoredAt);assert.equal(c.order.reportStatus,'In Progress');
 reset({A:'4'});c.order.testStates.Test={resultStatus:status,submittedAt:'2026-10-15',processedAt:'2026-10-15'};assert(c.commitCurrentResults(true,false));assert.equal(c.order.testStates.Test.resultStatus,status);
}
console.log('PASS: clearing verification results returns to Results Entry; complete verification edits remain pending.');

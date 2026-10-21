const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const h=fs.readFileSync(require('path').resolve(__dirname,'../../src/System/index.html'),'utf8');
function fn(name){const m=h.match(new RegExp('function '+name+'\\([^]*?\\n\\}'));assert(m,name);return m[0];}
let c,orders,closed,valid,cancel,rendered,marks,handled;
function reset(mode='verify',crossPatient=false){
 closed=0;valid=true;cancel=false;rendered=[];marks=0;handled=[];
 orders={};for(const key of ['A','B','C','D']){const lab=crossPatient?key:'1';orders[lab]??={lab,testStates:{}};orders[lab].testStates[key]={resultStatus:mode==='verify'?'Processed':'All'};}
 c={Date,Set,currentResultSession:['A','B','C','D'].map(key=>({lab:crossPatient?key:'1',key,label:key,codes:[key]})),currentResultSessionIndex:0,currentResultLab:crossPatient?'A':'1',currentResultLabel:'A',currentResultCodes:null,resultReportWorkspaceLab:'workspace',window:{plmsMarkModalSaved:()=>marks++},
 orderByLab:lab=>orders[lab],requirePermission:()=>true,resultSampleEligible:()=>true,resultItemStatus:(o,key)=>o.testStates[key].resultStatus,resultVerificationEligible:(o,key)=>['Processed','Restored'].includes(o.testStates[key].resultStatus),canResultAction:()=>true,
 refreshResultEntry:()=>{rendered.push(c.currentResultLabel);},closeResultEntry:()=>{closed++;c.currentResultSession=[];},toast(){},persist(){},renderAll(){},setSampleItemStatus(){},askFreshSampleReason:()=>cancel?null:'New sample',
 requestFreshSampleForResult:(o,key)=>{o.testStates[key].resultStatus='Fresh Sample';return true},resultAction:(lab,key,action)=>{orders[lab].testStates[key].resultStatus=action==='approve'?'Approved':'Rejected'},
 commitCurrentResults:(_,submit)=>{if(!valid)return false;if(submit)orders[c.currentResultLab].testStates[c.currentResultLabel].resultStatus='Processed';return true;}};
 vm.createContext(c);for(const name of ['resultSessionMode','resultSessionItemUsable','loadResultSessionItem','consumeCurrentResultSessionItem','approveCurrentResultEntry','saveResults','rejectCurrentResultEntry','reperformCurrentResultEntry','retestCurrentResultEntry'])vm.runInContext(fn(name),c);
}
for(const crossPatient of [false,true]){
 reset('verify',crossPatient);
 for(const action of ['approveCurrentResultEntry','reperformCurrentResultEntry','retestCurrentResultEntry','rejectCurrentResultEntry']){handled.push(c.currentResultLabel);c[action]();}
 assert.deepEqual(handled,['A','B','C','D']);assert.equal(closed,1);assert.deepEqual(rendered,['B','C','D']);assert.equal(c.currentResultSession.length,0);assert(marks>=4);
 reset('entry',crossPatient);for(let i=0;i<4;i++){handled.push(c.currentResultLabel);c.saveResults(i%2===0);}assert.deepEqual(handled,['A','B','C','D']);assert.equal(closed,1);
}
reset();cancel=true;c.retestCurrentResultEntry();assert.equal(c.currentResultLabel,'A');assert.equal(c.currentResultSession.length,4);assert.equal(closed,0);
reset('entry');valid=false;c.saveResults(true);assert.equal(c.currentResultSession.length,4);assert.equal(closed,0);
// Starting at the last manually navigated record wraps only through the unhandled records.
reset();c.currentResultSessionIndex=3;c.currentResultLabel='D';for(let i=0;i<4;i++){handled.push(c.currentResultLabel);c.rejectCurrentResultEntry();}assert.deepEqual(handled,['D','A','B','C']);assert.equal(closed,1);
// A denied/stale action must leave the current record open.
reset();c.resultAction=()=>{};c.rejectCurrentResultEntry();assert.equal(c.currentResultSession.length,4);assert.equal(closed,0);
for(const name of ['approveCurrentResultEntry','reperformCurrentResultEntry','retestCurrentResultEntry','rejectCurrentResultEntry']){reset();c.currentResultSession=c.currentResultSession.slice(0,1);c[name]();assert.equal(closed,1,name+' closes after the only record');}
for(const submit of [false,true]){reset('entry');c.currentResultSession=c.currentResultSession.slice(0,1);c.saveResults(submit);assert.equal(closed,1);}
let scripts=0;for(const m of h.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)){const type=m[1].match(/type=["']([^"']+)/)?.[1];if(type&&!/javascript|module/.test(type))continue;if(m[2].trim()){new vm.Script(m[2]);scripts++;}}
console.log(`PASS: all six actions; patient and cross-patient selections; exactly one loop; manual wrap; canceled/invalid/failed actions stay open; ${scripts} scripts compile.`);

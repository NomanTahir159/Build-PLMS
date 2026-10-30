const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync(path.join(__dirname,'../../src/System/index.html'),'utf8').replace(/\r\n?/g,'\n');
const start=html.indexOf('let auditClearing=false;'),end=html.indexOf('window.deletePlmsAuditActivity=',start);
assert(start>=0&&end>start);
async function scenario({failure=false,confirm=true,permission=true}={}){
 const order=[],messages=[],nodes=new Map();
 const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'old',hidden:false,disabled:false,innerHTML:'old',dispatchEvent(){},classList:{remove(){}}});return nodes.get(id)};
 const c={Promise,Error,Event:class{},state:{patients:[{lab:'1'}]},auditRows:[{id:'old'}],filteredAudit:[{id:'old'}],auditPage:2,pending:[{id:'old'}],queue:Promise.resolve(),baseline:null,
  requirePermission:()=>permission,allowed:()=>permission,clone:x=>JSON.parse(JSON.stringify(x)),storeOutbox(){order.push('outbox')},renderAudit(){},fail(){},toast:t=>messages.push(t),
  transaction:async(store,mode,fn)=>{assert.equal(store,'audit');assert.equal(mode,'readwrite');fn({clear(){order.push('local-clear')}})},
  document:{getElementById:node},window:{plmsConfirmAuditClear:async()=>confirm,plmsReliability:{flush:async()=>order.push('flush')},plmsNativeAuth:{call:async action=>{assert.equal(action,'audit_clear');order.push('native-clear');if(failure)throw Error('Permission denied: audit.delete')}}}};
 vm.createContext(c);vm.runInContext(html.slice(start,end),c);await c.window.clearAllPlmsAudit();
 assert.equal(vm.runInContext('auditClearing',c),false,'unlock after completion or failure');
 return {c,order,messages};
}
(async()=>{
 let r=await scenario();assert.deepEqual(r.order,['flush','native-clear','local-clear','outbox']);assert.equal(r.c.auditRows.length,0);assert.equal(r.c.pending.length,0);assert(r.messages.includes('All activity history cleared.'));
 r=await scenario({failure:true});assert.deepEqual(r.order,['flush','native-clear']);assert.equal(r.c.auditRows.length,1);assert.equal(r.c.pending.length,1);assert(!r.messages.includes('All activity history cleared.'));
 for(const opts of [{confirm:false},{permission:false}]){r=await scenario(opts);assert.equal(r.order.length,0);assert.equal(r.c.auditRows.length,1);}
 console.log('Clear All: native permission/success response precedes local deletion; failures and cancellation retain visible history.');
})().catch(e=>{console.error(e);process.exit(1)});

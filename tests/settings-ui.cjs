const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert/strict'),{JSDOM}=require('jsdom');
const html=fs.readFileSync(path.join(__dirname,'../src/System/index.html'),'utf8');
const dom=new JSDOM(html,{runScripts:'outside-only',url:'https://plms.local/'}),w=dom.window;
for(const id of ['laboratoryIdentitySettingsModal','labNumberingSettingsModal','reportPrintingSettingsModal','backupRestoreSettingsModal']){
 const modal=w.document.getElementById(id);assert(modal,'Required settings dialog missing: '+id);assert(modal.querySelector('.modal-body'),'Settings dialog body missing: '+id);
}
w.plmsEnhanceReliabilitySelects=()=>{};w.refreshPermissionUI=()=>{};
const start=html.indexOf('function installUI(){'),end=html.indexOf('\nlet auditResetPromise;',start);assert(start>=0&&end>start);
vm.runInContext(html.slice(start,end)+'\ninstallUI();',dom.getInternalVMContext());
const card=w.document.querySelector('#page-tools [data-plms-runtime-ui="audit-card"]');assert(card,'Audit History card must be installed');assert.equal(card.dataset.requiredPermission,'audit.view');assert.equal(w.document.querySelectorAll('[data-plms-runtime-ui="audit-card"]').length,1);
assert(w.document.getElementById('plmsAuditHistoryModal'));assert(w.document.getElementById('plmsAuditClearAll'));assert(w.document.getElementById('plmsSnapshotBody'));
let permitted=true,opened='',rendered=0;
Object.assign(w,{requirePermission:()=>permitted,allowed:()=>permitted,resetExistingAuditOnce:async()=>{},flush:async()=>{},all:async()=>[],renderAudit:()=>{rendered++},openModal:id=>{opened=id},fail:e=>{throw e},toast:()=>{}});
const a=html.indexOf('window.openPlmsAuditHistory=async function(){'),b=html.indexOf('\nwindow.filterPlmsAudit=',a);assert(a>=0&&b>a);
vm.runInContext(html.slice(a,b),dom.getInternalVMContext());
(async()=>{
 await w.eval(card.querySelector('button').getAttribute('onclick'));
 assert.equal(opened,'plmsAuditHistoryModal');assert.equal(rendered,1);
 permitted=false;opened='';await w.openPlmsAuditHistory();assert.equal(opened,'','Audit permission must be enforced');
 assert(!w.document.getElementById('officeIntegrationModal'));
 console.log('Settings DOM: all four dialogs retained; audit card mounts, opens history and enforces permission; backup controls mount.');dom.window.close();
})().catch(e=>{console.error(e);process.exitCode=1;dom.window.close()});

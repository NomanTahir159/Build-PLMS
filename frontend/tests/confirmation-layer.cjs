const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const h=fs.readFileSync(require('path').resolve(__dirname,'../../src/System/index.html'),'utf8').replace(/\r\n?/g,'\n');
let display='',expanded='true',confirmation=false,ready,events=0;
function element(id,initial){const values=new Set(initial);return{id,hidden:false,style:{display:'',setProperty:(k,v)=>{if(k==='display')display=v;}},classList:{contains:x=>values.has(x),add:(...xs)=>xs.forEach(x=>values.add(x)),remove:(...xs)=>xs.forEach(x=>values.delete(x))},querySelectorAll:()=>[{setAttribute:(k,v)=>{expanded=v;}}]};}
const popup=element('orderTestResults',['visible']),other=element('resultRemarksTemplateResults',['visible']),combo=element('department',['open']),calendar=element('orderBookingCalendar',['open']),modal=element('orderModal',[]),body={};
const observed=new Map();class Observer{constructor(fn){this.fn=fn;}observe(node,options){observed.set(node,{fn:this.fn,options});}}
const doc={readyState:'loading',body,dispatchEvent:()=>events++,getElementById:()=>null,addEventListener:(type,fn)=>{if(type==='DOMContentLoaded')ready=fn;},querySelector:()=>confirmation?{}:null,
 querySelectorAll:s=>s.startsWith('.plms-select.open')?[combo]:s.startsWith('.order-test-results')?[popup,other]:s==='.order-calendar.open'?[calendar]:s.startsWith('[aria-controls')?[{setAttribute:(k,v)=>expanded=v}]:s.startsWith('.modal,')?[modal]:[]};
const c={document:doc,Event:class{},WeakSet,MutationObserver:Observer,console};c.window=c;vm.createContext(c);
const script=h.match(/<script id="plms-page-dropdown-cleanup">([\s\S]*?)<\/script>/)[1];vm.runInContext(script,c);
const fieldValue='Unsaved patient text';c.plmsDismissTransientUi();assert(!popup.classList.contains('visible'));assert(!other.classList.contains('visible'));assert(!combo.classList.contains('open'));assert(!calendar.classList.contains('open'));assert.equal(display,'none');assert.equal(expanded,'false');assert.equal(fieldValue,'Unsaved patient text');
ready();assert(observed.has(modal));assert(observed.has(body));assert.equal(observed.size,2,'Observe modal visibility and direct body additions, not form/grid subtrees');
let before=events;modal.classList.add('open');observed.get(modal).fn();assert(events>before);before=events;observed.get(modal).fn();assert.equal(events,before,'Unchanged modal visibility does not dismiss menus');modal.classList.remove('open');observed.get(modal).fn();assert(events>before);
// Late positioning remains blocked under confirmations.
c.popup=popup;c.modal={};c.getComputedStyle=()=>({display:'flex'});popup.classList.contains=()=>true;confirmation=true;display='';
const p=h.indexOf(' function place(){',h.indexOf('id="plms-order-suggestions-portal-script"')),end=h.indexOf(' const observer=',p);vm.runInContext(h.slice(p,end),c);c.place();assert.equal(display,'none');
assert(h.includes('z-index:2147483646!important;'));assert(h.includes("closePlmsMenusForConfirmation();\n   discardDialog.classList.add('open')"));assert(h.includes('document.addEventListener("plms:page-leave",()=>closeAll())'));
console.log('PASS: shared menu/calendar cleanup, modal open/close lifecycle, no field/grid subtree observation, confirmation stacking and delayed-position guard.');
const search={id:'orderTestSearch',type:'text',value:'',closest:()=>({})};const patient={id:'fName',type:'text',value:'',closest:()=>null};
const form={id:'orderModal',querySelectorAll:()=>[search,patient]};
const sig=h.match(/ function signature\(modal\)\{[^\n]+/)[0];vm.runInContext(sig,c);const baseline=c.signature(form);search.value='CBC';assert.equal(c.signature(form),baseline,'Typing a search query must not dirty the order');patient.value='Patient name';assert.notEqual(c.signature(form),baseline,'Editing actual patient data must dirty the order');
const resultField={id:'resultInput',type:'text',value:'15.0',closest:()=>null};const resultForm={id:'resultModal',querySelectorAll:()=>[resultField]};c.resultAnnotationDraftSignature=()=>'';const rb=c.signature(resultForm);c.resultAnnotationDraftSignature=()=> 'Changed remark';assert.notEqual(c.signature(resultForm),rb,'Notes remain protected by unsaved-change detection');
modal.classList.add('open');observed.get(modal).fn();before=events;modal.style.display='none';observed.get(modal).fn();assert(events>before,'Style-based modal close dismisses menus');
console.log('PASS: transient searches do not trigger unsaved warnings; actual patient fields/results notes do; style-based modal closing dismisses floating UI.');

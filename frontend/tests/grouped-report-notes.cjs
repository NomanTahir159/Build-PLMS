const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const h=fs.readFileSync(require('path').resolve(__dirname,'../../src/System/index.html'),'utf8');
const esc=v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const controls={};
for(const id of ['resultCommentsText','resultRemarksText','resultInstructionsText','resultAdviseText'])controls[id]={value:''};
controls.resultAnnotationScope={value:'',options:[],dispatchEvent(){},set innerHTML(s){this.options=[...s.matchAll(/<option value="([^"]*)"/g)].map(m=>({value:m[1]}));}};
const order={lab:'1',tests:['HB','ESR','APTT','CBC'],remarks:'Order remark'};
const orders={'1':order,'2':{lab:'2',tests:['HB']}};
const c={esc,window:{},document:{getElementById:id=>controls[id]||null},orderByLab:lab=>orders[lab],currentResultLab:'1',currentResultLabel:'HB',currentResultCodes:null,resultItemStatus:()=> 'Processed',bookedDirectTest:(o,key)=>key==='CBC'?null:{name:key},Event:class{constructor(type){this.type=type}},console,Map,Set};vm.createContext(c);
vm.runInContext(h.slice(h.indexOf('let resultReportWorkspaceLab='),h.indexOf('function switchResultEntryTab(')),c);
vm.runInContext('renderAllResultTemplateSelectors=()=>{};',c);
vm.runInContext(h.slice(h.indexOf('function reportAnnotationText('),h.indexOf('</script>',h.indexOf('function reportAnnotationText('))),c);
c.loadResultReportContent(order);assert.equal(controls.resultRemarksText.value,'');assert.equal(c.resultAnnotationDraftSignature(),'[]');
controls.resultRemarksText.value='HB note';controls.resultAdviseText.value='HB advise';c.saveResultReportContent(order);
assert.equal(c.storedResultReportContent(order,'HB').remarks,'HB note');assert.equal(c.storedResultReportContent(order,'HB').advise,'HB advise');assert.equal(c.storedResultReportContent(order).remarks,'Order remark');
assert.equal(c.resultAnnotationDraftSignature(),'[]');
c.currentResultLabel='ESR';c.loadResultReportContent(order);assert.equal(controls.resultRemarksText.value,'');controls.resultRemarksText.value='ESR note';c.saveResultReportContent(order);
assert.equal(c.storedResultReportContent(order,'HB').remarks,'HB note');assert.equal(c.storedResultReportContent(order,'ESR').remarks,'ESR note');
c.currentResultLabel='HB';c.loadResultReportContent(order);controls.resultRemarksText.value='';c.saveResultReportContent(order);assert.equal(c.storedResultReportContent(order,'HB').remarks,'');assert.equal(c.storedResultReportContent(order,'ESR').remarks,'ESR note');assert.equal(c.storedResultReportContent(order).remarks,'Order remark');
c.currentResultLabel='CBC';c.loadResultReportContent(order);controls.resultInstructionsText.value='CBC only';c.saveResultReportContent(order);assert.equal(c.storedResultReportContent(order,'CBC').instructions,'CBC only');assert.equal(c.storedResultReportContent(order).instructions,'');
order.resultReportContent.remarks='Outdated note';order.remarks='Updated in Edit Order';assert.equal(c.storedResultReportContent(order).remarks,'Updated in Edit Order');order.remarks='';assert.equal(c.storedResultReportContent(order).remarks,'');
order.remarks='Order remark';order.comments='Whole order comment';
const snapshot=JSON.parse(JSON.stringify(order));c.currentResultLab='2';c.loadResultReportContent(orders['2']);assert.equal(controls.resultRemarksText.value,'');assert.equal(c.resultAnnotationDraftSignature(),'[]');assert.equal(JSON.stringify(order),JSON.stringify(snapshot));
const rendered=c.resultReportAnnotations(order);assert(rendered.includes('Remarks:'));assert(rendered.includes('Instructions:'));assert(!rendered.includes('CBC —'));assert(rendered.includes('Whole order comment'));assert(!c.resultReportAnnotations(order,'APTT'));
assert.equal(c.storedResultReportContent({remarks:'legacy'}).remarks,'legacy');assert.equal(c.storedResultReportContent({remarks:'legacy'},'HB').remarks,'');
const data=new Map();let serial=0;
class N{
 constructor(tag,cls='',text='',height=24){this.tagName=tag.toUpperCase();this.classes=new Set(cls.split(' ').filter(Boolean));this.children=[];this.parent=null;this.dataset={};this.text=text;this.height=height;this.style={setProperty(){},removeProperty(){}};}
 get classList(){return{add:v=>this.classes.add(v),remove:v=>this.classes.delete(v),contains:v=>this.classes.has(v)}}
 set className(v){this.classes=new Set(v.split(' ').filter(Boolean))}get className(){return [...this.classes].join(' ')}
 get textContent(){return this.text+this.children.map(n=>n.textContent).join('')}set textContent(v){this.text=String(v);this.children=[]}
 append(...nodes){for(const n of nodes){if(n.tagName==='#FRAGMENT'){this.append(...[...n.children]);continue}n.remove();n.parent=this;this.children.push(n)}}
 prepend(n){n.remove();n.parent=this;this.children.unshift(n)}
 replaceChildren(...nodes){for(const n of this.children)n.parent=null;this.children=[];this.append(...nodes)}
 remove(){if(this.parent){this.parent.children=this.parent.children.filter(n=>n!==this);this.parent=null}}
 before(n){const p=this.parent,i=p.children.indexOf(this);n.remove();n.parent=p;p.children.splice(i,0,n)}
 setAttribute(k,v){this[k]=v}
 matches(selector){if(selector.startsWith('.'))return this.classes.has(selector.slice(1));return this.tagName===selector.toUpperCase()}
 all(){return this.children.flatMap(n=>[n,...n.all()])}
 querySelectorAll(selector){
  if(selector===':scope > .stranded-report')return this.children.filter(n=>n.classes.has('stranded-report'));
  if(selector===':scope > .stranded-results > .stranded-result-table')return this.children.filter(n=>n.classes.has('stranded-results')).flatMap(n=>n.children.filter(t=>t.classes.has('stranded-result-table')));
  if(selector===':scope > .stranded-results > .lab-report-annotations')return this.children.filter(n=>n.classes.has('stranded-results')).flatMap(n=>n.children.filter(t=>t.classes.has('lab-report-annotations')));
  if(selector===':scope > .stranded-results > .lab-report-annotations > .lab-report-annotation')return this.children.filter(n=>n.classes.has('stranded-results')).flatMap(n=>n.children.filter(t=>t.classes.has('lab-report-annotations'))).flatMap(n=>n.children.filter(t=>t.classes.has('lab-report-annotation')));
  if(selector.startsWith(':scope > '))return this.children.filter(n=>n.matches(selector.slice(9)));
  if(selector==='.custom-report-sheet:has(> .stranded-report)')return this.all().filter(n=>n.classes.has('custom-report-sheet')&&n.children.some(c=>c.classes.has('stranded-report')));
  return this.all().filter(n=>n.matches(selector));
 }
 querySelector(s){return this.querySelectorAll(s)[0]||null}
 cloneNode(deep=false){const n=new N(this.tagName,this.className,this.text,this.height);n.dataset={...this.dataset};if(deep)n.append(...this.children.map(n=>n.cloneNode(true)));return n}
 getBoundingClientRect(){return{top:this.classes.has('stranded-results')?100:0,height:this.height}}
 get tBodies(){return this.children.filter(n=>n.tagName==='TBODY')}get tHead(){return this.children.find(n=>n.tagName==='THEAD')}
 get rows(){return this.children}get cells(){return this.children}
}
class Template extends N{
 constructor(){super('template');this.content=new N('#fragment')}
 set innerHTML(value){assert(data.has(value),'Unknown fixture HTML');this.content=data.get(value).cloneNode(true)}
 get innerHTML(){const key='rendered-'+(++serial);data.set(key,this.content.cloneNode(true));return key}
}
const document={createElement:tag=>tag==='template'?new Template():new N(tag),createDocumentFragment:()=>new N('#fragment'),body:new N('body')};
Object.assign(c,{document,state:{catalog:[]},orderedProfileTests:()=>[],getComputedStyle:()=>({marginBottom:'0'})});
vm.runInContext(h.slice(h.indexOf('function groupedReportAnnotationSources('),h.indexOf('function layoutPlmsDepartmentReports(')),c);
vm.runInContext(h.slice(h.indexOf('function layoutPlmsDepartmentReports('),h.indexOf('</script>',h.indexOf('function layoutPlmsDepartmentReports('))),c);
function table(keys,{profile='',department='Hematology',special='',rows=1}={}){
 const table=new N('table','stranded-result-table'),head=new N('thead'),body=new N('tbody');
 if(profile)head.append(new N('tr','stranded-profile-row',profile));
 table.append(new N('colgroup'),head,body);if(special)table.dataset.specialResultGroup=special;
 for(let i=0;i<rows;i++)for(const key of keys){const row=new N('tr','stranded-test-row');row.dataset.testCode=key+'-'+i;row.dataset.reportDepartment=department;row.dataset.reportBookedKey=key;row.append(new N('td','',key));body.append(row)}
 return table;
}
function note(key,text){const block=new N('div','lab-report-annotations');block.dataset.reportBookedKey=key;block.append(new N('div','lab-report-annotation',text,35));return block;}
function render(tables,notes){const fragment=new N('#fragment'),sheet=new N('div','custom-report-sheet'),article=new N('article','stranded-report'),main=new N('div','stranded-results');article.append(new N('div','stranded-department-name','Department of Hematology'),main);main.append(...tables,...notes);sheet.append(article);fragment.append(sheet);const key='fixture-'+(++serial);data.set(key,fragment);return c.layoutPlmsDepartmentReports(key);}
function flat(result){return data.get(result).querySelectorAll('.stranded-results').flatMap(n=>n.children).filter(n=>n.classes.has('stranded-result-table')||n.classes.has('lab-report-annotations'));}
let result=render([table(['CBC'],{profile:'CBC',rows:4}),table(['HB','ESR','APTT']),table(['RENAL'],{profile:'Renal'})],[note('CBC','CBC remarks'),note('HB','HB note'),note('ESR','ESR note'),note('APTT','APTT note'),note('','Order note')]);
for(let i=0;i<3;i++){
 const nodes=flat(result);
 assert.deepEqual(nodes.map(n=>n.classes.has('stranded-result-table')?'TABLE:'+n.tBodies[0].rows.map(r=>r.dataset.reportBookedKey).join(','):n.textContent),['TABLE:CBC,CBC,CBC,CBC','CBC remarks','TABLE:HB,ESR,APTT','HB note','ESR note','APTT note','TABLE:RENAL','Order note']);
 assert.equal(data.get(result).querySelectorAll('.stranded-test-row').length,8);result=c.layoutPlmsDepartmentReports(result);
}
// A profile with several band tables gets its notes after its final table.
result=render([table(['Hormones'],{profile:'Hormones',special:'a'}),table(['Hormones'],{profile:'Hormones',special:'b'}),table(['HB'])],[note('Hormones','Hormone note'),note('','Order note')]);
assert.deepEqual(flat(result).map(n=>n.tagName==='TABLE'?'table':n.textContent),['table','table','Hormone note','table','Order note']);
// ELISA antibodies share a table and both bookings retain notes below it.
const elisa=table(['unused']);delete elisa.tBodies[0].rows[0].dataset.reportBookedKey;elisa.tBodies[0].rows[0].dataset.reportBookedKeys=JSON.stringify(['HAV IgM','HAV IgG']);
result=render([elisa],[note('HAV IgM','IgM note'),note('HAV IgG','IgG note'),note('not printed','Unrelated'),note('','Order note')]);
assert.deepEqual(flat(result).map(n=>n.tagName==='TABLE'?'table':n.textContent),['table','IgM note','IgG note','Order note']);
// Report-level notes follow the last department; no note creates a split table.
result=render([table(['CBC'],{profile:'CBC'}),table(['Thyroid'],{profile:'Thyroid',department:'Chemistry'})],[note('CBC','CBC note'),note('Thyroid','Thyroid note'),note('','Order note')]);
assert.deepEqual(flat(result).map(n=>n.tagName==='TABLE'?'table':n.textContent),['table','CBC note','table','Thyroid note','Order note']);
result=render([table(['CBC'],{profile:'CBC',rows:50}),table(['HB','ESR','APTT'])],[note('CBC','CBC continued note'),note('HB','HB note'),note('','Order note')]);
assert.equal(data.get(result).querySelectorAll('.stranded-test-row').length,53);
assert.equal(data.get(result).querySelectorAll('.lab-report-annotation').filter(n=>n.textContent==='CBC continued note').length,1);
const sequence=flat(result),cbcNote=sequence.findIndex(n=>n.textContent==='CBC continued note'),lastCBC=sequence.reduce((i,n,index)=>n.tagName==='TABLE'&&n.tBodies[0].rows.some(r=>r.dataset.reportBookedKey==='CBC')?index:i,-1);assert.equal(cbcNote,lastCBC+1);
// Notes for an unrelated booking do not change a partial report's signature.
assert.deepEqual(JSON.parse(JSON.stringify(c.resultReportAnnotationSignature(order,['CBC']))),[['Whole order comment','Order remark','',''],[['CBC',['','','CBC only','']]]]);
console.log('PASS: scope selection, draft isolation, save/reopen/clear, profile notes, grouped HB/ESR/APTT, ELISA antibodies, mixed departments, continuation pages, no table split for notes, and no duplicates after repeated pagination.');
if(c.legacyResultAnnotationOwner){
 const cbc='Blood C/E, CBC',renal='Renal Profile (RFTs)';
 c.bookedItemTests=key=>key===cbc?[{code:'HB'},{code:'RBC'}]:[{code:'UREA'}];
 c.resultValueFor=(o,key,code)=>c.state.results?.[o.lab]?.[code];
 const legacy={lab:'3',tests:[cbc,renal],resultReportContent:{remarks:'CBC old remarks',updatedAt:'2026-10-21T10:00:00.000Z'},testStates:{[cbc]:{resultSavedAt:'2026-10-21T10:00:00.001Z'}}};
 c.state.results={'3':{HB:'15.0',RBC:'5.0'}};
 assert.equal(c.legacyResultAnnotationOwner(legacy).owner,cbc);
 assert.equal(c.storedResultReportContent(legacy,cbc).remarks,'CBC old remarks');assert.equal(c.storedResultReportContent(legacy).remarks,'');
 assert(c.resultReportAnnotations(legacy).includes('Remarks:'));
 // The old case shown by the screenshot: CBC first, Renal on another page.
 result=render([table([cbc],{profile:cbc}),table([renal],{profile:renal,department:'Routine Chemistry'})],[note(cbc,c.storedResultReportContent(legacy,cbc).remarks)]);
 assert.deepEqual(flat(result).map(n=>n.tagName==='TABLE'?'table':n.textContent),['table','CBC old remarks','table']);
 // Sole populated booking recovers notes when older timestamps are absent.
 const noTime=JSON.parse(JSON.stringify(legacy));delete noTime.resultReportContent.updatedAt;assert.equal(c.legacyResultAnnotationOwner(noTime).owner,cbc);
 // Explicitly whole-order notes and actual Order-form notes retain their scope.
 const explicit=JSON.parse(JSON.stringify(legacy));explicit.resultReportContent.scopeVersion=2;assert.equal(c.legacyResultAnnotationOwner(explicit),null);assert.equal(c.storedResultReportContent(explicit).remarks,'CBC old remarks');
 const ordered=JSON.parse(JSON.stringify(legacy));ordered.remarks='CBC old remarks';assert.equal(c.legacyResultAnnotationOwner(ordered),null);
 const ambiguous=JSON.parse(JSON.stringify(noTime));c.state.results['3'].UREA='20';assert.equal(c.legacyResultAnnotationOwner(ambiguous),null);delete c.state.results['3'].UREA;
 // Saving makes the recovered scope explicit, with no duplicated global text.
 orders['3']=legacy;c.document.getElementById=id=>controls[id]||null;c.currentResultLab='3';c.currentResultLabel=cbc;c.loadResultReportContent(legacy);assert.equal(controls.resultRemarksText.value,'CBC old remarks');c.saveResultReportContent(legacy);
 assert.equal(legacy.resultReportContent.scopeVersion,2);assert.equal(c.storedResultReportContent(legacy).remarks,'');assert.equal(c.storedResultReportContent(legacy,cbc).remarks,'CBC old remarks');assert.equal(c.legacyResultAnnotationOwner(legacy),null);
 console.log('PASS: legacy ownership recovery and order note protection.');
}

function detailedNote(booked,kind,text){
 const block=new N('div','lab-report-annotations');block.dataset.reportBookedKey=booked;
 const row=new N('div','lab-report-annotation');row.dataset.reportNoteKind=kind;row.dataset.reportNoteText=text;
 row.append(new N('div','lab-report-annotation-title',kind[0].toUpperCase()+kind.slice(1)+':'),new N('div','lab-report-annotation-text',text));block.append(row);return block;
}
result=render([table(['HB','ESR','APTT']),table(['CBC'],{profile:'CBC'})],[
 detailedNote('HB','comments','1. Clinical correlation advised.\n2. Repeat sample requested.'),
 detailedNote('ESR','comments','Clinical correlation advised.\nRepeat sample requested.'),
 detailedNote('HB','remarks','1. Interpret clinically.\n2. Ranges vary by age.'),
 detailedNote('ESR','remarks','1. Interpret clinically.\n2. Verified by repeat analysis.'),
 detailedNote('APTT','remarks','  Ranges   vary by age.  '),
 detailedNote('CBC','remarks','Profile-specific note.'),detailedNote('','remarks','Whole-order note.')]);
for(let i=0;i<3;i++){
 const notes=flat(result).filter(n=>n.classes.has('lab-report-annotations'));
 assert.equal(notes.length,3);const shared=notes[0];
 assert.equal(shared.querySelectorAll('.lab-report-annotation-title').length,2);
 assert.equal(shared.querySelectorAll('.lab-report-annotation-text')[0].textContent,'1. Clinical correlation advised.2. Repeat sample requested.');
 assert.equal(shared.querySelectorAll('.lab-report-annotation-text')[1].textContent,'1. Interpret clinically.2. Ranges vary by age.3. Verified by repeat analysis.');
 assert(notes[1].textContent.includes('Profile-specific note.'));assert(notes[2].textContent.includes('Whole-order note.'));
 assert.equal(data.get(result).querySelectorAll('.stranded-test-row').length,4);
 result=c.layoutPlmsDepartmentReports(result);
}
const safe=c.groupedReportAnnotationSources([{kind:'remarks',title:'Remarks:',text:'<script>alert(1)</script>',booked:'HB'}]);assert.equal(safe[0].lines[0],'<script>alert(1)</script>');
console.log('PASS: one heading per category, duplicate whole notes and numbered lines removed, distinct lines retained, profile/order positions preserved, repeated pagination stable.');

const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(require('path').resolve(__dirname,'../../src/System/index.html'),'utf8').replace(/\r\n?/g,'\n');
function fn(name,next){const a=html.indexOf('function '+name+'('),b=html.indexOf('\nfunction '+next+'(',a);assert(a>=0&&b>a);return html.slice(a,b)}
const nodes={};function el(id){return nodes[id]??={value:'',dataset:{},setAttribute(){},focus(){},classList:{contains(){return false},remove(){},toggle(){}},querySelector(){return null}}}
const c={Date,Set,Number,String,Math,Array,console,document:{getElementById:el,querySelector:()=>el('dateText'),addEventListener(){}},window:{addEventListener(){}},setTimeout(){},state:{patients:[{lab:'1',record:'10001',registeredAt:'2025-04-05T12:30:00.000Z',date:'05-Apr-2025',name:'Existing',labYear:2025}],orders:[{lab:'1',patient:'Existing',registeredAt:'2025-04-05T12:30:00.000Z',resultEnteredAt:'2025-04-06T12:30:00.000Z'}]},patientAddSavedLab:'',orderFormMode:'order',requirePermission:()=>true,validatePatientOnly:()=>true,nextPatientId:()=> 'P2',nextRecordNumber:()=> '10002',toast(){},renderAll(){},persist(){c.saved=JSON.parse(JSON.stringify(c.state))},plmsPatientYear:p=>p.labYear||new Date(p.registeredAt).getFullYear(),resetOrderForm(){vm.runInContext('setOrderBookingDate(new Date())',c)},fillOrderPatientFields:p=>c.fName.value=p.name,setOrderPatientState(){},setOrderRecordBadge(){},openModal(){},existingPatientOrderSeed:null};
c.patientByLab=l=>c.state.patients.find(p=>p.lab===l);c.orderByLab=l=>c.state.orders.find(o=>o.lab===l);
for(const k of ['fLab','fName','fGender','fAge','fPhone','fLocation','fRecord','fCNIC','fAddress'])c[k]=el(k);
c.orderRecordBadge=el('orderRecordBadge');c.orderRecordBadge.dataset.record='10002';
c.orderWorkflowStatus=o=>o?.orderStatus||o?.status||'Pending';
vm.createContext(c);vm.runInContext(fn('parsePlmsRecordDate','standardOrderDate'),c);
const a=html.indexOf('/* Order booking date is draft'),b=html.indexOf('function orderDateText()',a);vm.runInContext(html.slice(a,b),c);
vm.runInContext(fn('orderDateText','clearOrderPatientFields'),c);vm.runInContext(fn('setOrderFormMode','validatePatientOnly'),c);vm.runInContext(fn('savePatientOnly','saveCurrentOrderForm'),c);vm.runInContext(fn('editPatient','savePatientEdit'),c);
c.closeModal=()=>{};c.plmsAdministratorHasFullAccess=()=>false;c.plmsEditingPatientLab='';c.plmsEditingOrderLab='';c.plmsSyncPatientRelations=()=>{};c.plmsPrepareEditedLab=()=>true;
const run=s=>vm.runInContext(s,c);
run("setOrderFormMode('patient')");assert.equal(el('orderBookingDateTrigger').disabled,false);
c.fLab.value='2';c.fName.value='New';run("setOrderBookingDate(new Date());chooseOrderBookingDate('2022-06-15')");assert.equal(run('savePatientOnly()'),true);const added=c.state.patients[1];assert.equal(added.date,'15-Jun-2022');assert.equal(added.labYear,new Date().getFullYear());assert.equal(c.state.orders.length,1);
const saved=added.registeredAt;run("editPatient('2')");assert.equal(run('selectedOrderDate.toISOString()'),saved);assert.equal(el('orderModalTitle').textContent,'Edit Patient');run("chooseOrderBookingDate('2022-06-16');savePatientOnly()");assert.equal(added.date,'16-Jun-2022');assert.equal(c.state.patients.length,2);
const linked=JSON.stringify(c.state.orders[0]);run("editPatient('1');chooseOrderBookingDate('2024-02-29');savePatientOnly()");assert.equal(c.state.patients[0].date,'05-Apr-2025');assert.equal(c.state.patients[0].labYear,2025);assert.equal(c.state.orders[0].registeredAt,'2025-04-05T12:30:00.000Z');assert.equal(c.state.orders[0].resultEnteredAt,'2025-04-06T12:30:00.000Z');
c.patientAddSavedLab='';let before=JSON.stringify(c.state);assert.equal(run('savePatientOnly()'),false);assert.equal(JSON.stringify(c.state),before);
assert.equal(run("chooseOrderBookingDate('2025-02-29')"),false);
assert.equal(html.match(/id="plms-standard-modal-dates"/g).length,1);assert(html.includes('class="plms-modal-date" id="resultDateBadge"'));assert(!html.includes('pointer-events:none}\n#orderBookingCalendar'));assert(!html.includes('id="orderBookingDateInput"'));
console.log(process.env.TZ+': Add/Edit Patient date save, reopening, allocation year, linked dates and duplicate guard passed.');

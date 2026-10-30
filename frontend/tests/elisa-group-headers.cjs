const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync(require('path').join(__dirname,'../../src/System/index.html'),'utf8');
const test=(code,name)=>({code,name,unit:'U',range:'1 - 9',department:'Special Chemistry'});
const map={P1:[test('A','Alpha'),test('B','Beta')],P2:[test('C','Delta')],S1:[test('D','Single One')],S2:[test('E','Single Two')]};
const c={state:{},window:{plmsSpecialChemistryBaseRange:t=>t.range,plmsReportReferenceRules:()=>[]},bookedDirectTest:(o,k)=>k.startsWith('S')?map[k][0]:null,bookedItemTests:k=>map[k]||[],isParameterExcluded:()=>false,isOrderItemRejected:()=>false,contextualResultKey:(k,code)=>k+'::'+code,plmsCurrentCatalogDefinition:()=>true,resolveProfileReference:(p,t)=>({unit:t.unit,range:t.range}),patientByLab:()=>({}),effectiveCalculationRule:()=>null,profileTestDefinition:()=>null,resultValueFor:()=> '5',resultValueRuleFor:()=>null,reportResultCell:(t,v)=>v,formatPlmsReportReference:r=>r,formatPlmsReportResult:v=>v,plmsResultReportRange:()=>'',esc:s=>String(s??''),specialReferenceRange:r=>r.range,specialReferenceHeading:()=> 'Age',specialReferenceLabel:()=> 'Adult',specialClinicalBandRows:()=>'',plmsReportReferenceDecimals:()=>null};
vm.createContext(c);
let a=html.indexOf(' function reportBookingKeys('),b=html.indexOf(' // The configured Range Value',a);vm.runInContext(html.slice(a,b),c);
a=html.indexOf(' function specialChemistryResults(');b=html.indexOf(' function paginate(host)',a);vm.runInContext(html.slice(a,b),c);
const count=(s,name)=>(s.match(new RegExp('class="'+name+'"','g'))||[]).length;
const currentCatalog=JSON.parse(html.match(/<script[^>]*id="plms-embedded-catalog"[^>]*>([\s\S]*?)<\/script>/)[1]).catalog;
const names=['HAV IgG','HEV IgG','Dengue IgG','Anti TTG IgG','HAV IgM','HEV IgM','Dengue IgM','Anti TTG IgA'];
const keys=names.map((name,i)=>{const k='S'+(20+i);map[k]=[currentCatalog.find(t=>t.name===name)];assert(map[k][0],name);return k});
c.isParameterExcluded=()=>false;
const antibodyReport=c.elisaResults({order:{lab:'1',tests:keys},patient:{}});
const bodies=[...antibodyReport.matchAll(/<table class="elisa-result-body">[\s\S]*?<tbody>([\s\S]*?)<\/tbody><\/table>/g)].map(m=>m[1]);
assert.equal(bodies.length,4);for(const body of bodies)assert.equal((body.match(/<tr>/g)||[]).length,2);
for(const [index,first,second] of [[0,'HAV IgM','HAV IgG'],[1,'HEV IgM','HEV IgG'],[2,'Dengue IgM','Dengue IgG'],[3,'Anti TTG IgA','Anti TTG IgG']]){assert(bodies[index].indexOf(first)>=0);assert(bodies[index].indexOf(first)<bodies[index].indexOf(second));}
assert.equal(count(antibodyReport,'stranded-result-heading'),4,'Each antibody family has its own header');assert.equal(count(antibodyReport,'stranded-section-space'),3,'Space separates interpretation blocks from next group');
// Different cut-offs remain separate and labeled, while result rows stay together.
const altered=structuredClone(map.S24[0]);altered.resultValueRules=[{operator:'<',value:'0.1',interpretation:'Non-Reactive'}];map.S24=[altered];
const differing=c.elisaResults({order:{lab:'1',tests:['S20','S24']},patient:{}});
assert(differing.includes('Interpretation of Results: HAV IgG'));assert(differing.includes('Interpretation of Results: HAV IgM'));assert.equal((differing.match(/class="elisa-result-body"/g)||[]).length,1);
c.isParameterExcluded=(o,code)=>code===String(map.S20[0].code);const excluded=c.elisaResults({order:{lab:'1',tests:['S20','S24']},patient:{}});assert(!excluded.includes('<td>HAV IgG</td>'));assert(excluded.includes('<td>HAV IgM</td>'));
console.log('PASS: interleaved HAV/HEV/Dengue/Anti-TTG bookings grouped into antibody pairs including IgA; one main header; different cut-offs separately labeled; exclusions preserved.');


c.isParameterExcluded=()=>false;
const individual=c.elisaResults({order:{lab:'1',tests:['S1','S2']},patient:{}});assert.equal(count(individual,'stranded-result-heading'),2);assert.equal(count(individual,'stranded-section-space'),1);
const profiles=c.elisaResults({order:{lab:'1',tests:['P1','P2']},patient:{}});assert.equal(count(profiles,'stranded-profile-row'),2,'Profile name appears once per profile');assert.equal(count(profiles,'stranded-result-heading'),3,'Each separate group inside profile has header');assert.equal(count(profiles,'stranded-section-space'),2);
assert(html.includes('.elisa-result-body > tbody > tr{height:0.7cm!important}'));
let n=0;for(const m of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)){if(/type=["'](?:application|text)\//.test(m[1]))continue;new vm.Script(m[2]);n++}
console.log('PASS: each antibody group or single test gets its own table/header, inter-group space after interpretations, profile titles appear once, row height retained; '+n+' scripts compiled.');

const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const h=fs.readFileSync(require('path').resolve(__dirname,'../../src/System/index.html'),'utf8');
let compiled=0;for(const m of h.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)){const type=m[1].match(/type=["']([^"']+)/)?.[1];if(type&&!/javascript|module/.test(type))continue;if(m[2].trim()){new vm.Script(m[2]);compiled++;}}
const cls=new Set(),props={};let scrolled=0;
const panel={getBoundingClientRect:()=>({bottom:700})},search={getBoundingClientRect:()=>({bottom:400})};
const box={classList:{add:x=>cls.add(x),remove:x=>cls.delete(x)},innerHTML:'',style:{setProperty:(k,v)=>props[k]=v},closest:()=>panel,querySelector:()=>({scrollIntoView:()=>scrolled++})};
const input={value:'c',closest:()=>search};const clear={classList:{toggle(){}}};
const ctx={window:{innerHeight:900,addEventListener(){}},document:{getElementById:id=>({input,box,clear})[id]},resultTextCfg:()=>({search:'input',results:'box',clear:'clear',category:'Remarks'}),resultTextTemplateItems:()=>[{name:'Clinical note',code:'RM1',description:'Interpret clinically'}],resultTextTemplateSearchHighlight2:{},esc:String};vm.createContext(ctx);
const a=h.indexOf('function renderResultTextTemplateSearch(kind){',h.indexOf('const resultTextTemplateSearchHighlight2='));const b=h.indexOf('function resultTextTemplateSearchKeydown',a);vm.runInContext(h.slice(a,b),ctx);
ctx.renderResultTextTemplateSearch('remarks');assert(cls.has('visible'));assert(box.innerHTML.startsWith('<div class="result-template-menu-scroll">'));assert.equal(props['--result-template-menu-height'],'286px');assert.equal(scrolled,1);
input.value='';ctx.renderResultTextTemplateSearch('remarks');assert(!cls.has('visible'));assert.equal(box.innerHTML,'');
assert.equal((h.match(/class="result-template-search-anchor"/g)||[]).length,4);
assert(h.includes('position:absolute!important;top:100%!important;left:0!important;right:0!important;'));
console.log(`PASS: four anchored overlays, available-space sizing, inset scrolling, search/clear behavior; ${compiled} executable scripts compile.`);

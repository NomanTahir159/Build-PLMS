const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert/strict'),{spawnSync}=require('child_process');
const root=path.resolve(__dirname,'..'),h=fs.readFileSync(path.join(root,'src/System/index.html'),'utf8').replace(/\r\n?/g,'\n');let scripts=0;
for(const m of h.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)){if(!m[1].includes('src=')&&!(/type=["']([^"']+)["']/.test(m[1])&&!/type=["'](?:text\/javascript|application\/javascript|module)["']/.test(m[1]))&&m[2].trim()){new vm.Script(m[2]);scripts++;}}
for(const file of ['native-backend.js','native-office.js'])new vm.Script(fs.readFileSync(path.join(root,'src/System',file),'utf8').replace(/\r\n?/g,'\n'));
const seed=JSON.parse(fs.readFileSync(path.join(root,'src/Catalog/catalog.seed.json'),'utf8'));assert.equal(seed.catalog.length,192);assert.equal(new Set(seed.catalog.map(t=>t.code)).size,192);
for(const id of ['plmsCatalogAutosaveBtn','catalogOpenExcelBtn','catalogImportExcelBtn','plmsSaveUpdatedHtmlBtn'])assert(!new RegExp('<button[^>]*id="'+id+'"').test(h));
assert(h.includes('plmsBuildEditableDocxFromTemplate'));
assert(h.includes('src="native-office.js"'));
assert(!fs.readFileSync(path.join(root,'src/System/native-backend.js'),'utf8').includes('lastFailure=null;apply(data);')); 
const desktop=fs.readFileSync(path.join(root,'src/System/desktop.js'),'utf8');
for(const marker of ['<script src="native-backend.js"></script>',"plmsNativeAuth.login(username,password)","plms_frontend_ready",'plms-login-username-flat-background','orderProgressMarkup(o)'])assert((h+desktop).includes(marker),'Missing integration: '+marker);
assert(!/https:\/\/(?:cdnjs\.cloudflare\.com|fonts\.googleapis\.com)/.test(h),'External runtime font dependency');
for(const file of ['src/Resources/vendor/fontawesome/css/all.min.css','src/Resources/vendor/material-symbols/material-symbols.css','src-tauri/icons/icon.ico'])assert(fs.existsSync(path.join(root,file)),file);
for(const file of fs.readdirSync(path.join(__dirname,'tests')).filter(x=>x.endsWith('.cjs')).sort()){
 const run=spawnSync(process.execPath,[path.join(__dirname,'tests',file)],{cwd:root,stdio:'inherit',env:{...process.env,TZ:'Asia/Karachi'}});if(run.status!==0)process.exit(run.status||1);
}
console.log('Desktop integration and '+scripts+' inline scripts verified.');

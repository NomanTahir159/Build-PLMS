const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert/strict');
const root=path.resolve(__dirname,'../..'),h=fs.readFileSync(path.join(root,'src/System/index.html'),'utf8').replace(/\r\n?/g,'\n'),native=fs.readFileSync(path.join(root,'src/System/native-backend.js'),'utf8').replace(/\r\n?/g,'\n');
const config=JSON.parse(fs.readFileSync(path.join(root,'src-tauri/tauri.conf.json')));
const pkg=JSON.parse(fs.readFileSync(path.join(root,'package.json'))),lock=JSON.parse(fs.readFileSync(path.join(root,'package-lock.json'))),cargo=fs.readFileSync(path.join(root,'src-tauri/Cargo.toml'),'utf8');
assert.match(config.version,/^\d+\.\d+\.\d+$/);assert.equal(pkg.version,config.version);assert.equal(lock.version,config.version);assert.equal(lock.packages[''].version,config.version);assert(cargo.includes('version = \"'+config.version+'\"'));assert(h.includes('<dt>Build</dt><dd>'+config.version+'</dd>'));assert.equal(config.bundle.windows.nsis.installMode,'perMachine');
const seed=JSON.parse(fs.readFileSync(path.join(root,'src/Catalog/catalog.seed.json')));assert.equal(seed.catalog.length,192);
const embedded=JSON.parse(h.match(/<script[^>]*id="plms-embedded-catalog"[^>]*>([\s\S]*?)<\/script>/)[1]);assert.deepEqual(embedded,seed);
const accountSection=h.slice(h.indexOf('if(!Array.isArray(state.users)||state.users.length===0)'),h.indexOf('let plmsDefaultAdmin='));assert(!/U002|U003|Lab Technologist|Consultant Pathologist/.test(accountSection));
for(const id of ['plmsCatalogAutosaveBtn','catalogOpenExcelBtn','catalogImportExcelBtn','plmsSaveUpdatedHtmlBtn'])assert(!new RegExp('<button[^>]*id="'+id+'"').test(h));

// Exercise the exact first-login guard from the native adapter for both aliases.
const guard=native.match(/if\((!\['u001','noman tahir'\][^\n]+?)\)throw Error\('Username or password is incorrect\.'/)[1];
for(const username of ['U001','u001','Noman Tahir',' noman tahir '])assert.equal(vm.runInNewContext(guard,{username,password:'123'}),false);
assert.equal(vm.runInNewContext(guard,{username:'Noman Tahir',password:'bad'}),true);
const desktop=fs.readFileSync(path.join(root,'src/System/desktop.js'),'utf8').replace(/\r\n?/g,'\n');
assert(desktop.includes("invoke('plms_frontend_ready'"));
assert(desktop.includes("invoke('plms_window_background'"));
assert.equal(config.app.windows[0].decorations,false);
assert.equal(config.app.windows[0].url,'System/index.html');
assert.equal(config.productName,'Medicsoft PLMS');
console.log('Package defaults: single account, login aliases, toolbar controls removed, native theme and folder configuration passed.');

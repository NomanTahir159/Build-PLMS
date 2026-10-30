/* DOM/interaction contract for the exact HTML document embedded by NSIS.
   npm install --prefix <test-runtime> jsdom@26.1.0; set NODE_PATH accordingly. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),{JSDOM}=require('jsdom');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'src-tauri/installer/ui/dialog.html'),'utf8');
let receive;const messages=[];
const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.chrome={webview:{postMessage:s=>messages.push(s),addEventListener:(type,fn)=>{assert.equal(type,'message');receive=fn;}}};}});
const w=dom.window,d=w.document,q=s=>d.querySelector(s);
const show=data=>receive({data:{state:'install',folder:'C:\\Program Files\\Medicsoft\\PLMS',desktop:true,launch:true,remove:false,maintenance:'repair',canRepair:true,percent:68,...data}});
assert(messages.includes('ready'));assert(q('.product-logo').src.startsWith('data:image/svg+xml;base64,'));
const buttons=()=>Array.from(d.querySelectorAll('#plms-footer-actions button')).map(b=>b.textContent);
const expected={install:['Cancel','Install'],installing:['Cancel'],installed:['Finish'],maintenance:['Cancel','Continue'],uninstall:['Cancel','Uninstall'],uninstalling:[],uninstalled:['Finish']};
for(const [state,labels] of Object.entries(expected)){show({state});assert.equal(w.plmsInstaller.state.state,state);assert.deepEqual(buttons(),labels,state);assert.equal(q('.setup-progress').hidden,!['installing','uninstalling'].includes(state));assert(q('.product-logo'));assert(!q('table'));assert(!q('.preview-controls'));if(['installed','uninstalled'].includes(state)){assert(q('.success .success-mark'));assert(q('.success > div'));}if(state==='maintenance')assert(q('.retention .info-mark'));}
show({state:'install'});q('#plms-folder').value='D:\\PLMS';q('#plms-desktop').checked=false;q('.glass.primary').click();assert.equal(messages.at(-1),'install\tD:\\PLMS\t0\t1');q('.glass.primary').click();assert.equal(messages.filter(x=>x.startsWith('install\t')).length,1,'prevent duplicate submit');
receive({data:{kind:'unlock'}});q('#plms-browse').click();assert.equal(messages.at(-1),'browse\tD:\\PLMS\t0\t1');receive({data:{kind:'folder',folder:'E:\\Lab'}});assert.equal(q('#plms-folder').value,'E:\\Lab');assert.equal(q('#plms-desktop').checked,false);
show({state:'maintenance'});q('input[value="uninstall"]').click();q('.glass.primary').click();assert.equal(messages.at(-1),'continue\tuninstall');show({state:'maintenance',canRepair:false,maintenance:'uninstall'});assert(q('input[value="repair"]').disabled);
show({state:'uninstall'});assert.equal(q('#plms-delete-data').checked,false);q('#plms-delete-data').checked=true;q('.glass.danger').click();assert.equal(messages.at(-1),'uninstall\t1');show({state:'uninstalled',remove:true});assert(q('.success small').textContent.includes('removed'));show({state:'uninstalled',remove:false});assert(q('.success small').textContent.includes('retained'));
show({state:'installing',percent:9});receive({data:{kind:'progress',percent:57}});assert.equal(q('#plms-heading').textContent,'Installing (57%)');assert.equal(q('.setup-progress').getAttribute('aria-valuenow'),'57');assert.equal(q('.setup-progress > div').style.width,'57%');assert.equal(q('.glass').disabled,false);assert.equal(d.querySelectorAll('.status-line,.status-detail').length,2);
show({state:'installed'});q('.glass.primary').click();assert.equal(messages.at(-1),'finish');
show({state:'install'});d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));assert.equal(messages.at(-1),'cancel');
assert.equal(q('.lab-microscope svg').getAttribute('viewBox'),'0 0 24 24');
assert(!/setInterval|fetch\(|XMLHttpRequest|WebSocket/.test(fs.readFileSync(path.join(root,'src-tauri/installer/ui/host.js'),'utf8')),'no simulated progress or network code');
dom.window.close();console.log('Seven HTML states, controls, native messages, retained/deleted text, real progress and embedded artwork passed.');

require("./settings-ui.cjs");

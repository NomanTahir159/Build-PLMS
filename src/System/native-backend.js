/* Native-only adapter: every trusted read/write passes through the private worker. */
(()=>{
 const invoke=window.__TAURI__?.core?.invoke;
 if(!invoke){document.documentElement.classList.add('plms-auth-required');window.plmsNativeAuth={authenticated:false,login:async()=>{throw Error('Open PLMS using the desktop application.')}};return;}
 document.documentElement.classList.add('plms-native-startup-pending');
 let resolveStartup;const startup=new Promise(resolve=>resolveStartup=resolve);
 const key='SGRH_LAB_MANAGEMENT_V1',oldGet=Storage.prototype.getItem,oldSet=Storage.prototype.setItem;
 let legacy=null;try{legacy=JSON.parse(oldGet.call(localStorage,key)||'null')}catch(_){}
 let memory=legacy?JSON.stringify(legacy):null,token=null,revision=0,hydrating=false,queue=[],running=false,restoreNext=false,readyData=null,lastActivity=Date.now(),sessionStarted=Date.now(),lastPing=0,lastFailure=null;
 sessionStorage.removeItem('PLMS_LOGIN_USER');sessionStorage.setItem('PLMS_LOGGED_OUT','1');
 const raw=async request=>{try{const result=await invoke('plms_backend',{request});if(!result?.ok)throw Error(result?.error||'Database operation failed.');return result.data;}catch(e){throw e instanceof Error?e:Error(typeof e==='string'?e:'The local database connection failed. Close and reopen PLMS, then try again.');}};
 const ready=raw({action:'status'}).then(d=>(readyData=d,d));ready.catch(()=>{});
 function notice(text){const el=document.getElementById('plmsLoginMessage');if(el)el.textContent=text;}
 function apply(data,render=true){
  hydrating=true;try{state=data.state;revision=data.revision;memory=JSON.stringify(state);sessionStorage.setItem('PLMS_LOGIN_USER',data.userId);if(render){window.refreshPermissionUI?.();window.renderAll?.();window.applyTheme?.();}}finally{hydrating=false;}
 }
 async function migrateSnapshots(){
  // Transfer old full recovery copies only after the server accepts them; then remove browser copies.
  if(state.users.find(u=>String(u.id)===sessionStorage.getItem('PLMS_LOGIN_USER'))?.role!=='Administrator')return;
  const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('PLMS_RELIABILITY_V1',2);r.onupgradeneeded=()=>{for(const n of ['audit','backups','meta'])if(!r.result.objectStoreNames.contains(n))r.result.createObjectStore(n,{keyPath:'id'});};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
  try{
   const rows=await new Promise((resolve,reject)=>{const tx=db.transaction('backups','readonly'),r=tx.objectStore('backups').getAll();r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
   if(rows.length){for(const row of rows){await plmsReliability.verify(row.payload);await plmsCredentials.secureUsers(row.payload.data.users);row.payload.format='PLMS_BACKUP';row.payload.version=2;row.payload.auditEvents=row.payload.auditEvents||[];const bytes=new TextEncoder().encode(JSON.stringify({data:row.payload.data,auditEvents:row.payload.auditEvents}));row.payload.integrity={algorithm:'SHA-256',value:[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('')};}await raw({action:'snapshot_import',token,rows});await new Promise((resolve,reject)=>{const tx=db.transaction('backups','readwrite');tx.objectStore('backups').clear();tx.oncomplete=resolve;tx.onabort=()=>reject(tx.error)});}
  }finally{db.close()}
 }
 function lock(){token=null;queue=[];window.plmsNativeAuth.authenticated=false;sessionStorage.removeItem('PLMS_LOGIN_USER');sessionStorage.setItem('PLMS_LOGGED_OUT','1');document.documentElement.classList.remove('plms-authenticated');document.documentElement.classList.add('plms-auth-required');memory=null;hydrating=true;try{for(const k of ['patients','orders','users','inventory','qcEntries','criticalAlerts'])state[k]=[];for(const k of ['results','resultReferences','reportVersions','reportVersionAssets','resultReportContent','reportText','userPermissionOverrides'])state[k]={};document.querySelectorAll('.modal.open').forEach(el=>el.classList.remove('open'));document.querySelectorAll('iframe[srcdoc]').forEach(el=>el.srcdoc='');window.renderAll?.();}finally{hydrating=false;}}
 async function drain(){
  if(running||!token)return;running=true;
  while(queue.length&&token){
   const job=queue.shift();
   try{const data=await raw({action:job.restore?'restore':'commit',token,state:job.state,revision});revision=data.revision;if(!queue.length){lastFailure=null;apply(data,false);}}
   catch(e){lastFailure=e;queue=[];try{apply(await raw({action:'read',token}))}catch(_){lock();}window.toast?.(e.message,'info');break;}
  }
  running=false;
 }
 Storage.prototype.getItem=function(k){return this===localStorage&&k===key?memory:oldGet.call(this,k)};
 Storage.prototype.setItem=function(k,v){
  if(this!==localStorage||k!==key)return oldSet.call(this,k,v);
  memory=String(v);if(!token||hydrating)return;
  let candidate;try{candidate=JSON.parse(memory)}catch(_){return;}
  queue.push({state:candidate,restore:restoreNext});restoreNext=false;
  // Coalesce only unsent ordinary snapshots, never a restore.
  if(queue.length>1&&!queue.at(-2).restore&&!queue.at(-1).restore)queue.splice(queue.length-2,1);
  void drain();
 };
 async function acceptLogin(response){
   token=response.token;window.plmsNativeAuth.authenticated=true;queue=[];apply(response);
   try{await migrateSnapshots()}catch(e){window.toast?.('Existing recovery snapshots were retained for migration: '+e.message,'info');}lastActivity=sessionStarted=Date.now();lastPing=0;lastFailure=null;oldSet.call(localStorage,'PLMS_NATIVE_MIGRATION_COMPLETED','1');localStorage.removeItem(key);legacy=null;
   sessionStorage.removeItem('PLMS_LOGGED_OUT');document.documentElement.classList.remove('plms-auth-required');document.documentElement.classList.add('plms-authenticated');
   const u=state.users.find(u=>String(u.id)===response.userId);document.querySelector('.header .user-name').textContent=u?.name||'User';document.querySelector('.header .user-role').textContent=u?.role||'';
   const pw=document.getElementById('plmsLoginPassword');if(pw)pw.value='';notice('');
   window.refreshPermissionUI?.();navigate(window.plmsPreferredStartupPage?.()||'dashboard',{historyMode:'replace'});window.plmsSetInterfaceScale?.(state.settings?.appearance?.scalePercent||100);window.plmsSetTableDensity?.(state.settings?.appearance?.tableDensity||'comfortable');window.plmsSetSidebarMode?.(state.settings?.appearance?.sidebarMode||'auto');return response;
 }
 window.plmsNativeAuth={authenticated:false,startup,
  async login(username,password){
   const status=await ready;let response;
   if(!status.initialized){
    if(!['u001','noman tahir'].includes(username.trim().toLowerCase())||password!=='123')throw Error('Username or password is incorrect.');
    await plmsCredentials.ready;
    const candidate=JSON.parse(JSON.stringify(state));
    // Retain clinical records before any older client migration/reset logic can discard them.
    if(!legacy){for(const k of ['patients','orders','inventory','qcEntries'])candidate[k]=[];for(const k of ['results','resultReferences','reportVersions','reportVersionAssets','resultReportContent','reportText'])candidate[k]={};}
    if(legacy){Object.assign(candidate,JSON.parse(JSON.stringify(legacy)));await plmsCredentials.secureUsers(candidate.users);}
    response=await raw({action:'bootstrap',username,password,state:candidate});readyData.initialized=true;
   }else response=await raw({action:'login',username,password});
   return acceptLogin(response);
  },
  async call(action,extra={}){if(!token)throw Error('Sign in first.');return raw({...extra,action,token});},
  async flush(){while(running||queue.length)await new Promise(r=>setTimeout(r,20));if(lastFailure){const e=lastFailure;lastFailure=null;throw e;}},
  restoreNext(){restoreNext=true;},
  async logout(){await this.flush();try{await this.call('logout')}finally{lock();queue=[];hydrating=true;try{state.patients=[];state.orders=[];state.results={};state.resultReferences={};state.reportVersions={};state.reportVersionAssets={};state.users=[];memory=null;window.renderAll?.();}finally{hydrating=false;}}}
 };
 document.addEventListener('DOMContentLoaded',async()=>{
  const originalLogout=window.plmsLogout;window.plmsLogout=async()=>{try{await window.plmsNativeAuth.logout()}catch(e){notice(e.message)}finally{originalLogout?.()}};
  try{
   const status=await ready;
   const oldFlush=plmsReliability.flush;plmsReliability.flush=async()=>{await oldFlush();await window.plmsNativeAuth.flush()};
   const oldAudit=plmsReliability.getAudit;
   plmsReliability.getAudit=async()=>{
    const legacyEvents=await oldAudit();const native=await window.plmsNativeAuth.call('audit');
    return [...native.events.map(e=>({id:'native-'+e.id,time:new Date(e.time*1000).toISOString(),module:'Security',action:e.action,entity:'Local database',actor:{id:e.actor,name:state.users.find(u=>String(u.id)===e.actor)?.name||e.actor},changes:[]})),...legacyEvents];
   };
   const oldRestore=plmsReliability.prepareRestore;plmsReliability.prepareRestore=async(...args)=>{const r=await oldRestore(...args);window.plmsNativeAuth.restoreNext();return r};
   if(status.initialized){const response=await raw({action:'bypass_login'});if(response)await acceptLogin(response);}
  }catch(e){notice('The local database could not start. '+e.message);document.getElementById('plmsLoginForm')?.querySelectorAll('button[type="submit"]').forEach(x=>x.disabled=true);}finally{document.documentElement.classList.remove('plms-native-startup-pending');resolveStartup();}
 });
 function limits(){const v=state.settings?.sessionLimits||{};return {idleMinutes:[0,5,15,30,60,120,240].includes(v.idleMinutes)?v.idleMinutes:30,maxHours:[0,1,2,4,8,12,24].includes(v.maxHours)?v.maxHours:8};}
 for(const name of ['pointerdown','keydown','wheel','touchstart','plms-user-activity'])document.addEventListener(name,()=>{
  lastActivity=Date.now();const v=limits(),pingEvery=v.idleMinutes?Math.min(60000,v.idleMinutes*20000):300000;
  if(token&&Date.now()-lastPing>=pingEvery){lastPing=Date.now();window.plmsNativeAuth.call('ping').catch(()=>window.plmsLogout?.());}
 },{passive:true});
 setInterval(()=>{if(!token)return;const v=limits(),now=Date.now();if((v.idleMinutes>0&&now-lastActivity>=v.idleMinutes*60000)||(v.maxHours>0&&now-sessionStarted>=v.maxHours*3600000))window.plmsLogout?.();},10000);
 window.addEventListener('beforeunload',e=>{if(running||queue.length){e.preventDefault();e.returnValue='Changes are still being saved.'}});
})();

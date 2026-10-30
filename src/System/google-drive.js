/* Hidden Google Drive backups are owned by the private Windows worker. */
(()=>{
 'use strict';
 // Cloud v3 hashes values independently of JSON key/number serialization.
 // Existing local v2 backup validation is retained unchanged.
 async function verifyCloudBundle(bundle){
  if(bundle?.format!=='PLMS_BACKUP'||bundle.version!==3||bundle.integrity?.algorithm!=='SHA-256'||bundle.integrity?.canonicalization!=='plms-value-v1'||!Array.isArray(bundle.auditEvents))throw Error('Unsupported Google backup format.');
  const encoder=new TextEncoder(),parts=[];let size=0;
  const add=bytes=>{parts.push(bytes);size+=bytes.length;},text=value=>add(encoder.encode(value));
  function visit(value){
   if(value===null){text('z');return;}
   if(value===true){text('t');return;}
   if(value===false){text('f');return;}
   if(typeof value==='number'){if(!Number.isFinite(value))throw Error('Invalid backup number.');text('n');const bytes=new Uint8Array(8);new DataView(bytes.buffer).setFloat64(0,value===0?0:value,false);add(bytes);return;}
   if(typeof value==='string'){const bytes=encoder.encode(value);text('s'+bytes.length+':');add(bytes);return;}
   if(Array.isArray(value)){text('a'+value.length+':');value.forEach(visit);return;}
   if(value&&typeof value==='object'){const keys=Object.keys(value).sort();text('o'+keys.length+':');for(const key of keys){visit(key);visit(value[key]);}return;}
   throw Error('Invalid backup value.');
  }
  visit({data:bundle.data,auditEvents:bundle.auditEvents});
  const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}
  const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('');
  if(digest!==bundle.integrity.value)throw Error('Backup integrity check failed. No data was restored.');return true;
 }
 window.plmsVerifyDriveBackup=verifyCloudBundle;
 if(window.plmsReliability){const originalVerify=window.plmsReliability.verify;window.plmsReliability.verify=async function(bundle){return bundle?.version===3?verifyCloudBundle(bundle):originalVerify.apply(this,arguments);};}
 let info=null,jobId='',busy=false,polling=false,downloadPurpose='restore',lastListed=0,listedAccount='';
 window.plmsCloudBackupRows=[];
 const $=id=>document.getElementById(id),native=()=>!!window.__TAURI__?.core?.invoke&&!!window.plmsNativeAuth?.call;
 const admin=()=>String(window.currentPermissionUser?.()?.role||'').trim().toLowerCase()==='administrator';
 const when=value=>value?new Date(value).toLocaleString():'Never';
 function message(text,error=false){$('plmsDriveMessage').textContent=text;$('plmsDriveMessage').dataset.error=String(error);}
 const allowed=p=>!window.hasPermission||window.hasPermission(p);
 const table=()=>window.plmsRefreshBackupTable?.();
 async function call(action,extra={}){
  if(!native())throw Error('Google Drive connection and backups require the PLMS Windows app.');
  if(!admin())throw Error('Administrator access is required for Google Drive backups.');
  return window.plmsNativeAuth.call(action,extra);
 }
 function localSchedule(){
  const cfg=typeof state!=='undefined'?state.settings?.backup?.auto:null;
  return {frequency:cfg?.frequency||'daily',retain:Number(cfg?.retain||14)};
 }
 function render(status){
  info=status;const locked=busy||status.busy||!admin();
  $('plmsDriveAccount').textContent=status.connected?(status.email||'Google account connected'):'No Google account connected';
  $('plmsDriveConnect').hidden=!!status.connected;
  $('plmsDriveDisconnect').hidden=!status.connected;
  $('plmsDriveConnect').style.setProperty('display',status.connected?'none':'inline-flex','important');
  $('plmsDriveDisconnect').style.setProperty('display',status.connected?'inline-flex':'none','important');
  $('plmsDriveConnect').disabled=locked||(native()&&!status.configured);
  $('plmsDriveDisconnect').disabled=locked;
  if($('plmsDriveBackupNow'))$('plmsDriveBackupNow').disabled=locked||!status.connected||!allowed('backups.export')||!allowed('backups.manage');
  $('plmsDriveConnect').title=native()&&!status.configured?'This Windows build needs the bundled Google OAuth client':'Connect Google Drive';
  if(status.lastError)message(status.lastError,true);
  else if(status.busy&&status.operation!=='list')message(status.operation==='connect'?'Complete Google sign-in in your browser.':'Google backup operation in progress…');
  else if(!native())message('');
  else if(!status.configured)message('The Google connection must be bundled into this Windows build.');
  else if(!status.connected)message('Connect your Google account to enable automatic cloud backups.');
  else message(localSchedule().frequency==='off'?'Automatic backups are off.':'');
 }
 async function refresh(){if(!native()){render({connected:false,configured:true});return;}try{const status=await call('drive_status');render(status);if(!status.connected){window.plmsCloudBackupRows=[];listedAccount='';lastListed=0;await table();}}catch(e){message(e.message,true);}}
 window.plmsSyncDriveSchedule=async function(){
  if(!native()||!admin())return;
  const status=await call('drive_status');if(!status.connected)return;
  const cfg=localSchedule(),hours=({hourly:1,daily:24,weekly:168,off:24})[cfg.frequency];
  if(!hours)throw Error('Unsupported automatic backup schedule.');
  const enabled=cfg.frequency!=='off';
  if(status.enabled!==enabled||status.hours!==hours||status.retain!==cfg.retain)await call('drive_settings',{enabled,hours,retain:cfg.retain});
  await refresh();
 };
 async function finish(job){
  if(job.state==='error')throw Error(job.error||'Google Drive operation failed.');
  const result=job.result||{};
  if(job.kind==='connect'){await window.plmsSyncDriveSchedule();lastListed=0;return;}
  if(job.kind==='download'){
   if((result.purpose||downloadPurpose)==='export'){
    const blob=new Blob([JSON.stringify(result.payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download=(result.name||'PLMS_Cloud_Backup').replace(/\.gz$/i,'').replace(/\.json$/i,'')+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);message('Cloud backup exported.');
   }else{await window.plmsStageBackup(result.payload,result.name||'Google Drive backup');message('Backup validated. Use Restore Selected Backup to continue.');}
   return;
  }
  if(job.kind==='list'){
   window.plmsCloudBackupRows=(result.files||[]).map(row=>({id:row.id,time:row.createdTime,reason:row.appProperties?.reason||'Google Drive backup',bytes:Number(row.size)||0,backupType:'Cloud'}));
   lastListed=Date.now();listedAccount=info?.email||'';await table();return;
  }
  if(job.kind==='backup'){lastListed=0;message('Google backup uploaded and verified.');}
  if(job.kind==='delete'){
   window.plmsCloudBackupRows=window.plmsCloudBackupRows.filter(row=>row.id!==result.fileId);await table();lastListed=0;message('Cloud backup deleted.');
  }
 }
 async function poll(){
  if(!jobId||polling)return;polling=true;
  try{const job=await call('drive_job',{jobId});if(job.state!=='running'){jobId='';busy=false;await refresh();await finish(job);}}
  catch(e){jobId='';busy=false;await refresh();message(e.message,true);}
  finally{polling=false;}
 }
 async function run(action,extra={}){
  if(busy)return;busy=true;if(info)render(info);if(action!=='drive_list')message('Working…');
  await table();
  try{
   if(['drive_download','drive_backup'].includes(action))await window.plmsNativeAuth?.flush?.();
   if(action==='drive_download')downloadPurpose=extra.purpose||'restore';
   const result=await call(action,extra);
   if(result.jobId){jobId=result.jobId;await refresh();}
   else{busy=false;render(result);if(action==='drive_disconnect')message('Disconnected. Local backups continue; existing Google backups are retained.');}
  }catch(e){busy=false;await refresh();message(e.message,true);}
  finally{await table();}
 }
 window.plmsCloudActionsLocked=()=>busy||!!info?.busy||!info?.connected||!admin();
 window.exportPlmsCloudBackup=id=>run('drive_download',{fileId:id,purpose:'export'});
 window.selectPlmsCloudBackup=id=>run('drive_download',{fileId:id,purpose:'restore'});
 window.deletePlmsCloudBackup=id=>{
  if(!allowed('backups.manage')||window.plmsCloudActionsLocked())return;
  window.requestPlmsDeleteConfirmation('Delete Cloud Backup','Delete this Google Drive backup permanently? Local backups will remain.',()=>run('drive_delete',{fileId:id}));
 };
 window.backupPlmsToCloudNow=()=>run('drive_backup');
 function mount(){
  const body=$('backupRestoreSettingsModal')?.querySelector('.modal-body');if(!body)return;
  const card=document.createElement('div');card.id='plmsGoogleDriveCard';card.className='plms-backup-action-card';
  card.innerHTML=`<div class="plms-backup-action-icon"><i class="fa-brands fa-google-drive"></i></div><div><b>Google Drive Backups</b><small>Hidden cloud backups alongside local snapshots.</small><small id="plmsDriveAccount">No Google account connected</small><small id="plmsDriveMessage" role="status" aria-live="polite"></small></div><div class="plms-drive-actions"><button type="button" class="secondary" id="plmsDriveConnect"><i class="fa-brands fa-google-drive"></i>Connect Google Drive</button><button type="button" class="secondary" id="plmsDriveDisconnect" hidden><i class="fa-solid fa-link-slash" aria-hidden="true"></i>Disconnect</button></div>`;
  body.querySelector('.plms-backup-grid').append(card);
  $('plmsDriveConnect').onclick=()=>run('drive_connect');
  $('plmsDriveDisconnect').onclick=()=>window.requestPlmsDeleteConfirmation('Disconnect Google Drive','Disconnect this Google account? Local backups will continue and existing cloud backups will remain.',()=>run('drive_disconnect'),{kind:'disconnect'});
  document.addEventListener('change',event=>{if(['plmsBackupFrequency','plmsBackupRetention'].includes(event.target.id))window.plmsBackupScheduleDirty=true;});
  render({connected:false,configured:true});
  const oldOpen=window.openBackupRestoreSettings;
  window.openBackupRestoreSettings=function(){const result=oldOpen?.apply(this,arguments);lastListed=0;void refresh();return result;};
  const sync=()=>window.plmsSyncDriveSchedule().catch(e=>message('Local backups continue. Google schedule could not be updated: '+e.message,true));
  if(native()&&admin())void sync();
  setInterval(()=>{
   if(jobId){void poll();return;}
   if(!$('backupRestoreSettingsModal').classList.contains('open')||!native()||!admin()||busy)return;
   void (async()=>{await refresh();await table();if(info?.connected&&!info.busy&&(Date.now()-lastListed>30000||listedAccount!==info.email)){lastListed=Date.now();await run('drive_list');}})();
  },2000);
 }
 mount();
})();

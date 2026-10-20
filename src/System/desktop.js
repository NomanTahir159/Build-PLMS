/* Desktop frame integration: only approved PLMS screens enter navigation history. */
(function(){
 'use strict';
 const invoke=window.__TAURI__?.core?.invoke;if(!invoke)return;
 const back=document.getElementById('plmsDesktopBack'),forward=document.getElementById('plmsDesktopForward');
 let history=[],position=-1,replaying=false,closing=false;
 function update(){back.disabled=position<=0;forward.disabled=position<0||position>=history.length-1;}
 const previous=window.navigate;
 window.navigate=function(page,options){
  const result=previous.apply(this,arguments),actual=activeAppPage();
  if(!replaying&&window.plmsNativeAuth?.authenticated){
   if(options?.historyMode==='replace'&&position>=0)history[position]=actual;
   else if(history[position]!==actual){history=history.slice(0,position+1);history.push(actual);position=history.length-1;}
  }
  update();return result;
 };
 function move(delta){
  const target=position+delta;if(target<0||target>=history.length)return;
  const page=history[target];if(typeof canAccessPage==='function'&&!canAccessPage(page)){toast('This page is no longer available to your account.','info');return;}
  replaying=true;try{window.navigate(page,{historyMode:'replace'});if(activeAppPage()===page)position=target;}finally{replaying=false;update();}
 }
 back.addEventListener('click',()=>move(-1));forward.addEventListener('click',()=>move(1));
 async function requestClose(){
  if(closing)return;
  const docs=[document,...Array.from(document.querySelectorAll('iframe')).map(f=>{try{return f.contentDocument}catch(_){return null}}).filter(Boolean)];
  const helper=window.plmsPreferenceHelpers;
  const dirty=docs.flatMap(doc=>Array.from(doc.querySelectorAll('.modal.open,.profile-manager-modal.open'))).find(modal=>helper?.dirty(modal));
  if(dirty&&!helper.allow(dirty,requestClose))return;
  closing=true;
  try{if(window.plmsNativeAuth?.authenticated){persist();await window.plmsNativeAuth.flush();}await invoke('plms_window_action',{action:'close'});}catch(error){closing=false;toast(error.message||String(error),'info');}
 }
 window.plmsDesktopRequestClose=requestClose;
 document.getElementById('settingsExit')?.addEventListener('click',event=>{event.stopImmediatePropagation();requestClose();},true);
 document.querySelectorAll('[data-window-action]').forEach(button=>button.addEventListener('click',()=>button.dataset.windowAction==='close'?requestClose():invoke('plms_window_action',{action:button.dataset.windowAction}).catch(error=>toast(String(error),'info'))));
 document.querySelectorAll('.header .brand,.header .header-spacer,[data-desktop-drag]').forEach(region=>{
  region.addEventListener('mousedown',event=>{if(event.button===0)invoke('plms_window_action',{action:'drag'}).catch(()=>{});});
  region.addEventListener('dblclick',()=>invoke('plms_window_action',{action:'maximize'}).catch(()=>{}));
 });
 document.addEventListener('keydown',event=>{if(event.altKey&&['ArrowLeft','ArrowRight'].includes(event.key)&&!event.target.closest('input,textarea,select,[contenteditable=true]')){event.preventDefault();move(event.key==='ArrowLeft'?-1:1);}});
 const logout=window.plmsLogout;window.plmsLogout=async function(){history=[];position=-1;update();return logout?.apply(this,arguments);};
 async function ready(){
  await window.plmsNativeAuth.startup;
  await Promise.race([document.fonts.ready,new Promise(resolve=>setTimeout(resolve,1500))]);
  try{await invoke('plms_frontend_ready',{dark:document.documentElement.dataset.theme==='dark',system:(state.themeMode||'system')==='system'});}catch(error){console.error(error);}
  new MutationObserver(()=>invoke('plms_window_background',{dark:document.documentElement.dataset.theme==='dark',system:(state.themeMode||'system')==='system'}).catch(()=>{})).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready,{once:true});else ready();update();
})();

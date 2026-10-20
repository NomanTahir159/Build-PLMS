(function(){
 'use strict';
 if(!window.__TAURI__?.core?.invoke)return;
 const api=(path,body)=>window.plmsNativeAuth.call(path==='word/open'?'word_open':'word_updates',body||{});
 const encode=bytes=>{let result='';for(let i=0;i<bytes.length;i+=16384)result+=String.fromCharCode(...bytes.subarray(i,i+16384));return btoa(result)};
 let opening=false,syncing=false;
 window.officeEditWordTemplate=async function(id){
  if(!requirePermission('reports.manage_templates')||opening)return;
  const t=(state.reportTemplates||[]).find(x=>String(x.id)===String(id));if(!t)return;
  opening=true;
  try{
   const draft={...t};
   const holder=document.createElement('template');holder.innerHTML=String(t.content||t.html||'');
   holder.content.querySelectorAll('[data-report-binding="results"],[data-report-field="RESULTS_TABLE"]').forEach(el=>{const p=document.createElement('p');p.textContent='{{RESULTS_TABLE}}';el.replaceWith(p)});
   if(!/{{\s*RESULTS_TABLE\s*}}/.test(holder.content.textContent)){const p=document.createElement('p');p.textContent='{{RESULTS_TABLE}}';holder.content.appendChild(p);}
   draft.content=holder.innerHTML;draft.html=draft.content;
   const bytes=window.plmsBuildEditableDocxFromTemplate(draft);
   await api('word/open',{id:String(id),bytes:encode(bytes)});
   t.office=t.office||{};t.office.word={...(t.office.word||{}),linked:true,managed:true,bridge:'desktop',assetKey:'word:'+id,fileName:id+'.docx'};persist();
   renderTemplateConfiguration?.();toast('Template opened in Word. Save in Word to update PLMS.');
  }catch(error){toast(error.message,'info');}finally{opening=false;}
 };
 async function translateWordHtml(source){
  // Word styles are converted to inline CSS, so PLMS's existing sanitizer and
  // report renderer can retain font, color, paragraph and table formatting.
  const doc=new DOMParser().parseFromString(source,'text/html');
  doc.querySelectorAll('script,iframe,object,embed,link,meta,base').forEach(e=>e.remove());
  doc.querySelectorAll('*').forEach(e=>{for(const a of [...e.attributes])if(a.name.startsWith('on'))e.removeAttribute(a.name);});
  doc.querySelectorAll('img').forEach(e=>{if(!/^data:image\//i.test(e.src))e.remove();});
  const frame=document.createElement('iframe');frame.setAttribute('sandbox','allow-same-origin');frame.style.cssText='position:fixed;left:-10000px;top:0;width:800px;height:1100px;visibility:hidden';
  try{
   await new Promise(resolve=>{frame.onload=resolve;frame.srcdoc=doc.documentElement.outerHTML;document.body.appendChild(frame)});
   const body=frame.contentDocument.body;
   const properties=['font-family','font-size','font-weight','font-style','text-decoration','color','background-color','text-align','vertical-align','line-height','margin-top','margin-bottom','margin-left','margin-right','padding-top','padding-bottom','padding-left','padding-right','border-top','border-bottom','border-left','border-right','border-collapse','width','height'];
   for(const el of body.querySelectorAll('*')){
    const style=frame.contentWindow.getComputedStyle(el);
    for(const key of properties){const v=style.getPropertyValue(key);if(v)el.style.setProperty(key,v)}
   }
   // Word may split {{TOKENS}} across styled spans. Replace the containing
   // paragraph with its intact token text before the existing merge runs.
   for(const p of body.querySelectorAll('p')){if(/{{\s*[A-Z_]+\s*}}/.test(p.textContent)&&!/{{\s*[A-Z_]+\s*}}/.test(p.innerHTML)){const span=p.querySelector('span');if(span){for(const key of ['font-family','font-size','font-weight','color'])p.style.setProperty(key,span.style.getPropertyValue(key));}p.textContent=p.textContent;}}
   for(const row of body.querySelectorAll('tr')){const cells=[...row.cells].map(c=>c.textContent.trim());if(cells.join('|')==='Test Name|Result|Unit|Reference Range')row.remove();}
   body.querySelectorAll('style,script').forEach(e=>e.remove());
   return sanitizeReportTemplateHTML(body.innerHTML);
  }finally{frame.remove();}
 }
 window.plmsTranslateWordHtml=translateWordHtml;
 async function sync(){
  if(syncing||!window.plmsNativeAuth?.authenticated||!hasPermission('reports.manage_templates'))return;syncing=true;
  try{
   const updates=await api('word/updates');
   let changed=false;
   for(const u of updates){
    let t=(state.reportTemplates||[]).find(x=>String(x.id)===u.id);if(!t)continue;
    const prior=t.office?.word?.revision;
    if(u.error){if(prior!==u.revision){toast(u.error,'info');t.office=t.office||{};t.office.word={...(t.office.word||{}),revision:u.revision};changed=true;}continue;}
    if(prior===u.revision)continue;
    const content=await translateWordHtml(u.html);
    t=(state.reportTemplates||[]).find(x=>String(x.id)===u.id);if(!t)continue;
    if(!content.trim()||!/{{\s*RESULTS_TABLE\s*}}/.test(content)){if(window.__wordError!==u.revision){toast('Word template was not applied: keep {{RESULTS_TABLE}} in the document.','info');window.__wordError=u.revision;}continue;}
    t.content=content;t.layoutVersion='desktop-word';t.html=content;
    t.office=t.office||{};t.office.word={...(t.office.word||{}),managed:true,linked:true,bridge:'desktop',revision:u.revision,fileName:u.id+'.docx',assetKey:'word:'+u.id};
    if(u.page){t.margins=u.page.margins;t.orientation=u.page.orientation;t.pageSize=u.page.pageSize;}
    t.updatedAt=new Date().toISOString();changed=true;
    const raw=Uint8Array.from(atob(u.bytes),c=>c.charCodeAt(0));
    try{await PLMSOfficeBridge.putAsset('word:'+u.id,new File([raw],u.id+'.docx',{type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}));}catch(error){console.warn('Word browser cache unavailable; managed DOCX remains saved on disk.');}
    toast('Word changes applied to '+t.name+'.');
   }
   if(changed){persist();if(!document.querySelector('.modal.show,.modal.open,.modal.active'))renderTemplateConfiguration?.();}
  }catch(e){console.error('PLMS Word sync:',e.message);}finally{syncing=false;}
 }
 const priorRender=window.renderAssignedReportTemplate;
 window.renderAssignedReportTemplate=function(template,ctx){return template?.office?.word?.managed&&template.layoutVersion==='desktop-word'?window.plmsRenderNativeReportTemplate(template,ctx):priorRender(template,ctx)};
 renderAssignedReportTemplate=window.renderAssignedReportTemplate;
 setInterval(sync,2500);sync();
 window.openOfficeIntegrationModal=function(){
  document.getElementById('officeIntegrationMode').textContent='Windows App';
  document.getElementById('officeIntegrationModeText').textContent='Open report templates in Microsoft Word. Saved changes automatically update PLMS.';
  openModal('officeIntegrationModal');
 };
})();

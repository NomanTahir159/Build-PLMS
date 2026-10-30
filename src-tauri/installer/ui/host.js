(function(){
 'use strict';
 const root=document.getElementById('plms-setup-preview'),content=root.querySelector('#plms-page-content'),footer=root.querySelector('#plms-footer-actions'),win=root.querySelector('.setup-window');
 const states=['install','installing','installed','maintenance','uninstall','uninstalling','uninstalled'];
 const captions={install:['Installation Options','Set up Medicsoft PLMS on your computer'],installing:['Installing','Installing application files'],installed:['Installation Complete','Medicsoft PLMS is ready to use'],maintenance:['PLMS Is Already Installed','Choose how you want to continue'],uninstall:['Uninstall Medicsoft PLMS','Choose what to remove'],uninstalling:['Uninstalling','Removing application files'],uninstalled:['Uninstall Complete','Medicsoft PLMS has been removed']};
 let current={state:'install',percent:0,folder:'',desktop:true,launch:true,remove:false,maintenance:'repair',canRepair:true},locked=false;
 const bridge=window.chrome?.webview;
 function send(parts){if(bridge)bridge.postMessage(parts.join('\t'));else window.dispatchEvent(new CustomEvent('plms-preview-action',{detail:parts}));}
 function act(parts){if(locked)return;locked=true;send(parts);}
 function button(text,kind,action){const b=document.createElement('button');b.type='button';b.className='glass '+kind;b.textContent=text;b.addEventListener('click',action);footer.appendChild(b);return b;}
 function progress(value){const percent=Math.max(0,Math.min(100,Number(value)||0));current.percent=percent;const busy=current.state==='installing'||current.state==='uninstalling';root.querySelector('#plms-heading').textContent=captions[current.state][0]+(busy?' ('+percent+'%)':'');const track=root.querySelector('.setup-progress');track.hidden=!busy;track.setAttribute('aria-valuenow',String(percent));track.setAttribute('aria-label',current.state==='uninstalling'?'Uninstallation progress':'Installation progress');track.firstElementChild.style.width=percent+'%';}
 function show(data){
  if(!data||!states.includes(data.state))return;
  current={...current,...data};locked=false;
  const state=current.state,uninstall=state.startsWith('uninstall');
  root.querySelector('#plms-window-name').textContent='Medicsoft PLMS '+(uninstall?'Uninstall':'Setup');
  root.querySelector('#plms-subheading').textContent=captions[state][1];
  root.querySelector('#plms-footer-note').textContent='';footer.replaceChildren();progress(current.percent);
  if(state==='install'){
   content.innerHTML='<label class="folder-label" for="plms-folder">Installation Folder</label><div class="folder-row"><input id="plms-folder" aria-label="Installation folder" required><button type="button" class="glass" id="plms-browse">Browse…</button></div><label class="check"><input id="plms-desktop" type="checkbox"><span>Create a desktop shortcut</span></label><label class="check"><input id="plms-launch" type="checkbox"><span>Launch PLMS after installation</span></label>';
   content.querySelector('#plms-folder').value=current.folder;
   content.querySelector('#plms-desktop').checked=current.desktop;content.querySelector('#plms-launch').checked=current.launch;
   const values=()=>[content.querySelector('#plms-folder').value,content.querySelector('#plms-desktop').checked?'1':'0',content.querySelector('#plms-launch').checked?'1':'0'];
   content.querySelector('#plms-browse').onclick=()=>send(['browse',...values()]);
   button('Cancel','',()=>act(['cancel']));button('Install','primary',()=>{const field=content.querySelector('#plms-folder');if(!field.value.trim()){field.reportValidity();field.focus();return;}act(['install',...values()]);});
  }else if(state==='installing'||state==='uninstalling'){
   content.innerHTML='<p class="status-line">'+(uninstall?'Uninstalling':'Installing')+' Medicsoft PLMS…</p><p class="status-detail">'+(uninstall?(current.remove?'Removing selected PLMS data.':'Your saved data is being retained.'):'Copying application resources')+'</p>';
   root.querySelector('#plms-footer-note').textContent='Please wait while '+(uninstall?'removal':'setup')+' completes.';
   if(!uninstall)button('Cancel','',()=>act(['cancel']));
  }else if(state==='installed'||state==='uninstalled'){
   content.innerHTML='<div class="success"><span class="success-mark" aria-hidden="true">✓</span><div>'+(uninstall?'Uninstallation':'Installation')+' completed successfully.'+(uninstall?'<small>'+(current.remove?'Your selected PLMS data has been removed.':'Your patient records and backups have been retained.')+'</small>':'')+'</div></div>';
   button('Finish','primary',()=>act(['finish']));
  }else if(state==='maintenance'){
   content.innerHTML=['repair','uninstall','exit'].map((value,i)=>'<label class="radio-choice"><input type="radio" name="plms-maintenance" value="'+value+'" '+(current.maintenance===value?'checked':'')+(value==='repair'&&!current.canRepair?' disabled':'')+'><span><strong>'+['Repair Installation','Uninstall PLMS','Exit Setup'][i]+'</strong><small>'+['Reinstall application files and keep existing data.','Remove the application from this computer.','Keep the current installation.'][i]+'</small></span></label>').join('')+'<div class="retention"><span class="info-mark" aria-hidden="true">i</span><span>Your patient records and settings are retained by default.</span></div>';
   button('Cancel','',()=>act(['cancel']));button('Continue','primary',()=>act(['continue',content.querySelector('input:checked')?.value||'repair']));
  }else{
   content.innerHTML='<p class="question">Remove Medicsoft PLMS from this computer?</p><label class="check"><input type="checkbox" id="plms-delete-data"><span class="delete-label">Delete patient records, catalog, settings and backups<small>Leave unchecked to keep your data for reinstallation.</small></span></label>';
   content.querySelector('#plms-delete-data').checked=current.remove;
   button('Cancel','',()=>act(['cancel']));button('Uninstall','danger',()=>act(['uninstall',content.querySelector('#plms-delete-data').checked?'1':'0']));
  }
 }
 function fit(){const scale=Math.min(1,innerWidth/952,innerHeight/998);win.style.transform='translate(-50%,-50%) scale('+scale+')';}
 root.querySelector('[data-chrome=minimize]').onclick=()=>send(['minimize']);
 root.querySelector('[data-chrome=close]').onclick=()=>{if(current.state!=='uninstalling')act(['cancel']);};
 root.querySelector('.window-title').addEventListener('pointerdown',e=>{if(e.button===0&&!e.target.closest('button'))send(['drag']);});
 addEventListener('resize',fit);
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&current.state!=='uninstalling'){event.preventDefault();act(['cancel']);}else if(event.key==='Enter'&&!['installing','uninstalling'].includes(current.state)){event.preventDefault();footer.querySelector('.primary,.danger')?.click();}});
 if(bridge)bridge.addEventListener('message',event=>{const data=event.data;if(data?.kind==='progress')progress(data.percent);else if(data?.kind==='folder'){const field=content.querySelector('#plms-folder');if(field)field.value=data.folder;}else if(data?.kind==='unlock')locked=false;else {show(data);Promise.all(Array.from(root.querySelectorAll('img')).map(img=>img.complete?Promise.resolve():new Promise(resolve=>{img.addEventListener('load',resolve,{once:true});img.addEventListener('error',resolve,{once:true});}))).then(()=>send(['painted']));}});
 window.plmsInstaller={show,progress,get state(){return {...current}}};
 show(current);fit();if(bridge)send(['ready']);
})();

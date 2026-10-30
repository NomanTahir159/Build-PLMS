// Run once for each edited package, before packaging/building.
const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..'),read=name=>fs.readFileSync(path.join(root,name),'utf8');
const config=JSON.parse(read('src-tauri/tauri.conf.json')),previous=config.version;
if(!/^\d+\.\d+\.\d+$/.test(previous))throw Error('Expected a three-part app version.');
const [major,minor,patch]=previous.split('.').map(Number),next=`${major}.${minor}.${patch+1}`;
const writes=[];
for(const name of ['src-tauri/tauri.conf.json','package.json']){const value=JSON.parse(read(name));if(value.version!==previous)throw Error('Version mismatch in '+name);value.version=next;writes.push([name,JSON.stringify(value,null,2)+'\n']);}
const lock=JSON.parse(read('package-lock.json'));if(lock.version!==previous||lock.packages[''].version!==previous)throw Error('Version mismatch in package-lock.json');lock.version=lock.packages[''].version=next;writes.push(['package-lock.json',JSON.stringify(lock,null,2)+'\n']);
const cargo=read('src-tauri/Cargo.toml'),match=cargo.match(/(\[package\][\s\S]*?\nversion\s*=\s*")([^"]+)(")/);if(!match||match[2]!==previous)throw Error('Version mismatch in Cargo.toml');writes.push(['src-tauri/Cargo.toml',cargo.replace(match[0],match[1]+next+match[3])]);
const html=read('src/System/index.html'),about='<dt>Build</dt><dd>'+previous+'</dd>';if(!html.includes(about))throw Error('About build version does not match.');writes.push(['src/System/index.html',html.replace(about,'<dt>Build</dt><dd>'+next+'</dd>')]);
for(const [name,contents] of writes)fs.writeFileSync(path.join(root,name),contents);
console.log(`Medicsoft PLMS ${previous} → ${next}`);

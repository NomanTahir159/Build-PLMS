// Normalize the installer name without changing the app identity or installed folder.
const fs=require('node:fs'),path=require('node:path');
function nameInstaller(root=path.resolve(__dirname,'..')){
 const version=JSON.parse(fs.readFileSync(path.join(root,'src-tauri/tauri.conf.json'),'utf8')).version;
 if(!/^\d+\.\d+\.\d+$/.test(version))throw Error('Invalid app version.');
 const folder=path.join(root,'src-tauri/target/release/bundle/nsis');
 const target=`Medicsoft.PLMS_${version}_x64-setup.exe`;
 const matches=fs.readdirSync(folder).filter(name=>name.endsWith(`_${version}_x64-setup.exe`));
 if(matches.length!==1)throw Error('Expected one Windows x64 installer for '+version);
 if(matches[0]!==target)fs.renameSync(path.join(folder,matches[0]),path.join(folder,target));
 return path.join(folder,target);
}
if(require.main===module)console.log(nameInstaller());
module.exports={nameInstaller};

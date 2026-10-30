const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve(__dirname,'../..');
for(const file of ['src/System/desktop.js','src/System/index.html','src-tauri/src/lib.rs']){
 const source=fs.readFileSync(path.join(root,file),'utf8');
 for(const symbol of ['plmsOpenDataFolder','dataFolderAction','plmsDataFolderButton','plms_open_data_folder'])assert(!source.includes(symbol),'Unapproved Data Folder shortcut remains in '+file);
}
console.log('About page: Data Folder shortcut and unused native command removed.');

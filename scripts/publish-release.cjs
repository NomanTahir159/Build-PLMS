'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{spawnSync}=require('node:child_process');
function publishRelease({root=path.resolve(__dirname,'..'),env=process.env,run=spawnSync}={}){
 const required=['GH_TOKEN','GITHUB_REPOSITORY','GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_RUN_NUMBER'];
 for(const key of required)if(!env[key])throw Error('Missing release environment: '+key);
 if(!/^\d+$/.test(env.GITHUB_RUN_ID)||!/^\d+$/.test(env.GITHUB_RUN_ATTEMPT)||!/^\d+$/.test(env.GITHUB_RUN_NUMBER))throw Error('Invalid workflow run identifier.');
 if(!/^[a-f0-9]{40,64}$/i.test(env.GITHUB_SHA))throw Error('Invalid source commit.');
 const version=JSON.parse(fs.readFileSync(path.join(root,'src-tauri/tauri.conf.json'),'utf8')).version;
 if(!/^\d+\.\d+\.\d+(?:[-+][\w.-]+)?$/.test(version))throw Error('Invalid app version.');
 const directory=path.join(root,'src-tauri/target/release/bundle/nsis');
 const installers=fs.existsSync(directory)?fs.readdirSync(directory).filter(name=>name.endsWith('.exe')).sort():[];
 if(!installers.length)throw Error('No Windows installer found; release was not created.');
 const assets=[];
 for(const name of installers){
  const file=path.join(directory,name),checksum=file+'.sha256';
  if(!fs.statSync(file).size)throw Error('Installer is empty: '+name);
  if(!fs.existsSync(checksum))throw Error('Missing installer checksum: '+name);
  const expected=fs.readFileSync(checksum,'utf8').trim().match(/^([a-f0-9]{64})\s+\*?(.+)$/i);
  const actual=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  if(!expected||expected[1].toLowerCase()!==actual||expected[2]!==name)throw Error('Installer checksum mismatch: '+name);
  assets.push(file,checksum);
 }
 const tag=`plms-v${version}-${env.GITHUB_RUN_ID}-${env.GITHUB_RUN_ATTEMPT}`;
 const notes=path.join(env.RUNNER_TEMP||root,'plms-release-notes.md');
 fs.writeFileSync(notes,`Medicsoft PLMS ${version} for Windows x64.\n\nDownload the setup EXE and its .sha256 checksum from Assets below.\n\nSource commit: ${env.GITHUB_SHA}\nBuild: ${env.GITHUB_RUN_NUMBER}, attempt ${env.GITHUB_RUN_ATTEMPT}.\n\nThis installer is not code-signed. Existing installations retain their data.\n`);
 const args=['release','create',tag,...assets,'--repo',env.GITHUB_REPOSITORY,'--target',env.GITHUB_SHA,'--title',`Medicsoft PLMS ${version} - Build ${env.GITHUB_RUN_NUMBER}.${env.GITHUB_RUN_ATTEMPT}`,'--notes-file',notes,'--latest=false'];
 const result=run('gh',args,{cwd:root,env,encoding:'utf8',shell:false});
 if(result.error)throw Error('Unable to start GitHub CLI: '+result.error.message);
 if(result.status!==0)throw Error('Release upload failed: '+String(result.stderr||result.stdout||'GitHub CLI failed.').trim());
 const url=String(result.stdout||'').trim();
 if(env.GITHUB_STEP_SUMMARY)fs.appendFileSync(env.GITHUB_STEP_SUMMARY,`\n### Medicsoft PLMS installer\n\nDownload the installer and SHA-256 checksum from [GitHub Releases](${url||`https://github.com/${env.GITHUB_REPOSITORY}/releases/tag/${tag}`}).\n\n`);
 return {tag,url,assets};
}
module.exports={publishRelease};
if(require.main===module){try{const result=publishRelease();console.log('Installer uploaded to GitHub Releases: '+result.url);}catch(error){console.error(error.message);process.exitCode=1;}}

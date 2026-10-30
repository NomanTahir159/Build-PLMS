const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),{publishRelease}=require(path.join(root,'scripts/publish-release.cjs'));
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'plms-release-'));
try{
 fs.mkdirSync(path.join(temp,'src-tauri/target/release/bundle/nsis'),{recursive:true});
 fs.writeFileSync(path.join(temp,'src-tauri/tauri.conf.json'),JSON.stringify({version:'1.0.0'}));
 const directory=path.join(temp,'src-tauri/target/release/bundle/nsis'),name='Medicsoft PLMS_1.0.0_x64-setup.exe',file=path.join(directory,name);
 fs.writeFileSync(file,'installer fixture');const digest=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
 const env={GH_TOKEN:'test-only',GITHUB_REPOSITORY:'owner/repo',GITHUB_SHA:'a'.repeat(40),GITHUB_RUN_ID:'1234',GITHUB_RUN_ATTEMPT:'1',GITHUB_RUN_NUMBER:'42',RUNNER_TEMP:temp,GITHUB_STEP_SUMMARY:path.join(temp,'summary.md')};
 let calls=0,args;const run=(command,argv,options)=>{calls++;assert.equal(command,'gh');assert.equal(options.shell,false);args=argv;return{status:0,stdout:'https://github.com/owner/repo/releases/tag/build\n'};};
 assert.throws(()=>publishRelease({root:temp,env,run}),/Missing installer checksum/);assert.equal(calls,0);
 fs.writeFileSync(file+'.sha256','0'.repeat(64)+'  '+name);assert.throws(()=>publishRelease({root:temp,env,run}),/checksum mismatch/);assert.equal(calls,0);
 fs.writeFileSync(file+'.sha256',digest+'  '+name+'\n');
 const result=publishRelease({root:temp,env,run});assert.equal(result.tag,'plms-v1.0.0-1234-1');assert(args.includes(file));assert(args.includes(file+'.sha256'));assert.equal(args[args.indexOf('--target')+1],env.GITHUB_SHA);assert(args.includes('--latest=false'));assert(!args.includes('--clobber'));assert(fs.readFileSync(env.GITHUB_STEP_SUMMARY,'utf8').replace(/\r\n?/g,'\n').includes('GitHub Releases'));
 assert.notEqual(publishRelease({root:temp,env:{...env,GITHUB_RUN_ATTEMPT:'2'},run}).tag,result.tag,'A rerun gets its own release');
 assert.throws(()=>publishRelease({root:temp,env,run:()=>({status:1,stderr:'Permission denied'})}),/Release upload failed/);
 const workflow=fs.readFileSync(path.join(root,'.github/workflows/build-windows.yml'),'utf8').replace(/\r\n?/g,'\n');
 assert(!workflow.includes('actions/upload-artifact'));assert(workflow.includes('contents: write'));assert(workflow.includes('GH_TOKEN: ${{ github.token }}'));assert(workflow.includes('node scripts/publish-release.cjs'));
 console.log('PASS: Release delivery validates assets/checksums, targets exact commit, handles paths with spaces, uses unique rerun tags, propagates upload failures, and excludes Actions artifacts.');
}finally{fs.rmSync(temp,{recursive:true,force:true});}

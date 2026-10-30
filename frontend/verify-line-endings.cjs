const path=require('node:path'),{spawnSync}=require('node:child_process');
const hook=path.resolve(__dirname,'helpers/windows-newlines.cjs').split(path.sep).join('/');
const nodeOptions=[process.env.NODE_OPTIONS||'',`--require=${JSON.stringify(hook)}`].filter(Boolean).join(' ');
const result=spawnSync(process.execPath,[path.join(__dirname,'verify.cjs')],{cwd:path.resolve(__dirname,'..'),env:{...process.env,NODE_OPTIONS:nodeOptions},stdio:'inherit'});
if(result.error)throw result.error;
if(result.status!==0)process.exit(result.status||1);
console.log('Windows CRLF source simulation: all frontend suites passed.');

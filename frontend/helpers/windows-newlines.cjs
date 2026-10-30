// Emulate a Windows checkout for source-reading tests, including subprocesses.
const fs=require('node:fs'),path=require('node:path'),original=fs.readFileSync;
const source=path.resolve(__dirname,'../../src/System/index.html');
fs.readFileSync=function(file,...args){
 const value=original.call(this,file,...args);
 if(typeof file==='string'&&path.resolve(file)===source&&typeof value==='string')return value.replace(/\r\n?/g,'\n').replace(/\n/g,'\r\n');
 return value;
};

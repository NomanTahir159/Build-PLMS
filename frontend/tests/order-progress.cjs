const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync(require('path').resolve(__dirname,'../../src/System/index.html'),'utf8').replace(/\r\n?/g,'\n');
const src=html.slice(html.indexOf('function orderProgress(o){'),html.indexOf('function orderPermissions(o){'));
const context={orderWorkflowStatus:o=>o.status||'Pending',sampleItemStatus:(o,k)=>o.items[k].sample,resultItemStatus:(o,k)=>o.items[k].result||'All',isOrderItemRejected:(o,k)=>!!o.items[k].rejected,bookedItemTests:k=>[{code:k}],isParameterExcluded:()=>false,resultValueFor:(o,k)=>o.items[k].value,esc:s=>s};
vm.createContext(context);vm.runInContext(src,context);
const order=(items,status='Processing')=>({status,tests:Object.keys(items),items});
const check=(o,n)=>assert.equal(context.orderProgress(o).percent,n);
check(order({},'Completed'),100);
check(order({},'Pending'),0);
check(order({a:{sample:'Collected'}}),25);
check(order({a:{sample:'Received'}}),50);
check(order({a:{sample:'Received',value:'12'}}),65);
check(order({a:{sample:'Received',result:'Processed'}}),75);
check(order({a:{sample:'Received',result:'Approved'},b:{sample:'Received'}}),75);
check(order({a:{sample:'Received',result:'Approved'}}),99);
check(order({a:{sample:'Received',result:'Repeated',value:'old'}}),50);
check(order({a:{sample:'Received',result:'Fresh Sample Requested',value:'old'}}),0);
check(order({a:{sample:'Resampled',result:'Repeated',value:'old'}}),25);
check(order({a:{sample:'Rejected'}}),0);
for(const status of ['Rejected','Canceled']){const o=order({},status);check(o,0);assert.equal(context.orderProgress(o).tone,'stopped');}
assert.match(context.orderProgressMarkup(order({},'Completed')),/aria-valuenow="100"/);
assert.match(context.orderProgressMarkup(order({},'Completed')),/>100%<\/span>/);
assert.match(html, /\$\{orderProgressMarkup\(o\)\}<div class="order-actions"/);
let n=0;
for(const m of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)){if(!m[1].includes('src=')&&!m[1].includes('application/json')&&m[2].trim()){new vm.Script(m[2]);n++;}}
console.log('Order progress stages, mixed items, repeat/fresh samples, terminal states and markup passed. '+n+' inline scripts compiled.');

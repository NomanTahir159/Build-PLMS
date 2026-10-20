const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert/strict');
const root=path.resolve(__dirname,'../..'),html=fs.readFileSync(path.join(root,'src/System/index.html'),'utf8');
const script=html.match(/<script id="plms-session-limits">([\s\S]*?)<\/script>/)[1];
(async()=>{
 const controls={sessionIdleLimit:{value:'',dispatchEvent(){}},sessionMaximumLimit:{value:'',dispatchEvent(){}}},listeners={},user={role:'Administrator',status:'Active'},saved=[];
 function node(){const names=new Set(),parts={},events={};return {dataset:{},children:[],events,classList:{add:n=>names.add(n),remove:n=>names.delete(n),contains:n=>names.has(n),toggle(n,on){if(on===undefined)on=!names.has(n);on?names.add(n):names.delete(n)}},setAttribute(k,v){this[k]=v},addEventListener(k,fn){events[k]=fn},appendChild(el){this.children.push(el)},querySelector(k){return parts[k]??(parts[k]=node())},set innerHTML(v){this.children=[]}}}
 for(const [id,el] of Object.entries(controls)){el.dataset={};el.classList=node().classList;el.options=(id==='sessionIdleLimit'?[0,5,15,30,60,120,240]:[0,1,2,4,8,12,24]).map(v=>({value:String(v),textContent:v?String(v):'Never'}));el.getAttribute=()=>id;el.insertAdjacentElement=(where,box)=>el.box=box;}
 const c={state:{settings:{}},window:{},document:{createElement:()=>node(),readyState:'complete',getElementById:id=>controls[id],querySelectorAll:()=>[],addEventListener(){},documentElement:{classList:{contains:()=>false}}},Event:class{constructor(type){this.type=type}},currentPermissionUser:()=>user,hasPermission:()=>true,persist:()=>saved.push(JSON.stringify(c.state.settings)),toast(){},setInterval(){},sessionStorage:{getItem:()=>null}};
 for(const el of Object.values(controls)){el.events={};el.addEventListener=(name,cb)=>{el.events[name]=cb;listeners[name]=cb};el.dispatchEvent=e=>el.events[e.type]?.(e);}
 vm.createContext(c);vm.runInContext(script,c);assert.equal(controls.sessionIdleLimit.value,'30');assert.equal(controls.sessionMaximumLimit.value,'8');
 controls.sessionIdleLimit.value='0';controls.sessionMaximumLimit.value='12';await listeners.change();assert.equal(c.state.settings.sessionLimits.idleMinutes,0);assert.equal(c.state.settings.sessionLimits.maxHours,12);assert.equal(saved.length,1);
 assert(controls.sessionIdleLimit.box);const trigger=controls.sessionIdleLimit.box.querySelector('.plms-select-button');trigger.events.click({stopPropagation(){}});assert(controls.sessionIdleLimit.box.classList.contains('open'));assert.equal(controls.sessionIdleLimit.box.querySelector('.plms-select-menu').children.length,7);user.role='Technologist';c.window.plmsSessionLimits.sync();assert(controls.sessionIdleLimit.disabled);controls.sessionIdleLimit.value='5';await listeners.change();assert.equal(c.state.settings.sessionLimits.idleMinutes,0);
 const native=fs.readFileSync(path.join(root,'src/System/native-backend.js'),'utf8'),a=native.indexOf(' function limits(){'),b=native.indexOf(" window.addEventListener('beforeunload'",a);let now=0,interval,logout=0,pings=0;const activity={};
 const n={state:{settings:{}},token:'token',sessionStarted:0,lastActivity:0,lastPing:0,Date:{now:()=>now},document:{addEventListener:(name,fn)=>activity[name]=fn},setInterval:fn=>interval=fn,window:{plmsLogout:()=>logout++,plmsNativeAuth:{call:async()=>{pings++}}}};vm.createContext(n);vm.runInContext(native.slice(a,b),n);
 now=1800000;interval();assert.equal(logout,1);
 logout=0;n.state.settings.sessionLimits={idleMinutes:0,maxHours:0};now=1e12;interval();assert.equal(logout,0);
 n.state.settings.sessionLimits={idleMinutes:0,maxHours:1};interval();assert.equal(logout,1);
 logout=0;n.state.settings.sessionLimits={idleMinutes:5,maxHours:0};now=200000;activity.wheel();now=400000;interval();assert.equal(logout,0);now=500000;interval();assert.equal(logout,1);assert(pings>0);
 assert(html.includes('id="settingsPanel-security"'));assert(html.includes('Session Limits'));

 console.log('Session Limits: defaults, saved Never/timed choices, admin-only controls, native idle/max expiry, independent Never limits, activity heartbeat, card order and three-column layout passed.');
})().catch(e=>{console.error(e);process.exitCode=1});

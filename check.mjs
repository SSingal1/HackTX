import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const store=new Map(),els=new Map();
const el=()=>({innerHTML:'',textContent:'',className:'',value:'',dataset:{},classList:{toggle(){}},setAttribute(){},querySelectorAll(){return[]},focus(){}});
const document={getElementById(id){if(!els.has(id))els.set(id,el());return els.get(id)},querySelectorAll(){return[]},addEventListener(){},createElement:el,body:{style:{}}};
const ctx=vm.createContext({document,window:{addEventListener(){}},location:{hash:''},localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)},icon:()=>'',money:v=>'$'+Math.round(v),hydrateIcons(){},setTimeout(){},URL,Blob,console,modal(){},toast(){}});
vm.runInContext(fs.readFileSync('dist/guardian.js','utf8'),ctx);
function run(js){return vm.runInContext(js,ctx);}
assert.equal(run('calc().keep'),3800);
assert.equal(run('calc().replace'),7340);
assert.equal(run('calc().difference'),3540);
run('state.discount=true');assert.equal(run('calc().oop'),1750);
run("state.profile='covered'");assert.equal(run('calc().discount'),0);assert.equal(run('calc().oop'),800);
run("state.profile='limited';state.discount=false");assert.equal(run('calc().keepOK'),false);assert.equal(run('calc().replaceOK'),false);assert.equal(run('recommendation().warning'),true);
run("state.profile='alex';state.miles=24000");assert.equal(run('calc().fuelKeep'),2800);assert.equal(run('calc().fuelReplace'),1680);
run("state.profile='covered';state.repair=500");assert.equal(run('calc().oop'),0);assert.equal(run('calc().coverage'),500);
for(const tab of ['overview','maintenance','local','compare','plan']){const content=run(({overview:'overview()',maintenance:'maintenance()',local:'localView()',compare:'compare()',plan:'plan()'})[tab]);assert.ok(content.length>400,tab);assert.ok(!content.includes('NaN'),tab);}
for(const filename of ['index.html','guardian.html']){const text=fs.readFileSync('dist/'+filename,'utf8');for(const [,asset]of text.matchAll(/(?:src|href)="([^"#]+\.(?:js|css|svg))"/g)){assert.ok(fs.existsSync('dist/'+asset),asset);}}
console.log('PASS: costs, discounts, coverage caps, reserve safeguards, mileage, five views, and asset references.');

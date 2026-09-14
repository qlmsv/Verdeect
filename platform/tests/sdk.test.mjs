import test from 'node:test';
import assert from 'node:assert/strict';
import {assertModulePath,ModuleController} from '../packages/ui-sdk/dist/index.js';
const base='/_platform/apps/crm';
for(const path of [base,base+'/contacts/42',base+'/contacts?q=test#details']) {
  test('accepts local route '+path,()=>assert.equal(assertModulePath(base,path),path));
}
for(const path of ['https://evil.test','//evil.test','/admin','/_platform/apps/crm-evil',base+'/../manage',base+'/%2e%2e/manage',base+'/%252e%252e/manage',base+'/%5cadmin']) {
  test('rejects escaping route '+path,()=>assert.throws(()=>assertModulePath(base,path)));
}
class Element {
  dataset={};children=[];parent=null;
  ownerDocument={createElement:()=>new Element()};
  replaceChildren(child){this.children.forEach(c=>c.parent=null);this.children=[child];child.parent=this;}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);this.parent=null;}
}
const context={moduleId:'fixture',organizationId:'org-a',routeBase:base,locale:'ru',theme:'dark',tokens:{},navigate:()=>{},reportError:()=>{}};
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
test('mount, theme update and cleanup',async()=>{
  let unmounted=0,theme=''; const host=new ModuleController();const target=new Element();
  const module={mount:()=>({canLeave:()=>true,updateContext:c=>theme=c.theme,unmount:()=>unmounted++})};
  assert.equal(await host.open(async()=>module,target,context),true);
  await host.update({...context,theme:'light'});assert.equal(theme,'light');
  await host.dispose();assert.equal(unmounted,1);assert.equal(target.children.length,0);
});
test('unsaved changes block switch',async()=>{
  const host=new ModuleController();const target=new Element();let mounted=0;
  const module={mount:()=>{mounted++;return {canLeave:()=>false,updateContext:()=>{},unmount:()=>{}};}};
  await host.open(async()=>module,target,context);
  assert.equal(await host.open(async()=>module,target,context),false);assert.equal(mounted,1);
  await host.dispose();
});
test('organization cannot mutate a running module',async()=>{
  const host=new ModuleController();const module={mount:()=>({canLeave:()=>true,updateContext:()=>{},unmount:()=>{}})};
  await host.open(async()=>module,new Element(),context);
  await assert.rejects(host.update({...context,organizationId:'org-b'}));await host.dispose();
});
test('late module finishes detached and is unmounted',async()=>{
  const host=new ModuleController();const target=new Element();const d=deferred();let cleanup=0;let entered=false;
  const first={mount:async()=>{entered=true;await d.promise;return {canLeave:()=>true,updateContext:()=>{},unmount:()=>cleanup++};}};
  const loading=host.open(async()=>first,target,context);
  while(!entered) await new Promise(r=>setTimeout(r,0));
  const second={mount:()=>({canLeave:()=>true,updateContext:()=>{},unmount:()=>{}})};
  assert.equal(await host.open(async()=>second,target,context),true);
  d.resolve();assert.equal(await loading,false);assert.equal(cleanup,1);assert.equal(target.children.length,1);
  await host.dispose();
});
test('render failure reports locally and removes slot',async()=>{
  let error='';const host=new ModuleController();const target=new Element();
  assert.equal(await host.open(async()=>({mount(){throw new Error('fixture error');}}),target,{...context,reportError:e=>error=e.message}),false);
  assert.equal(error,'fixture error');assert.equal(target.children.length,0);
});

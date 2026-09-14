// Architectural fixture only. Not Twenty, not imported by the production host.
import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import type {ModuleContext, WebModule} from '../../../packages/ui-sdk/src/index';

function Fixture({context,onDirty}:{context:ModuleContext;onDirty:(value:boolean)=>void}) {
  const [draft,setDraft]=useState('');
  useEffect(() => {onDirty(Boolean(draft));},[draft,onDirty]);
  return <section style={{background:context.tokens.surface,color:context.tokens.text,padding:24}}>
    <h2>React contract fixture</h2><p>{context.organizationId} / {context.theme}</p>
    <label>Draft <input value={draft} onChange={e=>setDraft(e.target.value)} /></label>
    <button onClick={()=>context.navigate(context.routeBase+'/details')}>Nested route</button>
  </section>;
}
export const module:WebModule={
  mount(container,initialContext) {
    const root=createRoot(container); let dirty=false; let context=initialContext;
    const onDirty=(value:boolean)=>{dirty=value;};
    const render=()=>root.render(<Fixture context={context} onDirty={onDirty}/>);
    render();
    return {updateContext(next){context=next;render();},canLeave(){return !dirty;},unmount(){root.unmount();}};
  }
};

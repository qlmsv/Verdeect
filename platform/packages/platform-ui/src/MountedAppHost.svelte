<script lang="ts">
  import {onMount,onDestroy} from 'svelte';
  import {ModuleController,type ModuleLoader,type ModuleContext} from './sdk/index';
  export let loader:ModuleLoader;
  export let context:Omit<ModuleContext,'signal'>;
  let container:HTMLDivElement;
  let mounted=false;
  const controller=new ModuleController();
  onMount(() => {controller.open(loader,container,context).then(value=>mounted=value).catch(context.reportError);});
  onDestroy(() => {void controller.dispose().catch(context.reportError);});
  $: if(mounted) void controller.update(context).catch(context.reportError);
  // The navigation owner must await this BEFORE switching routes.
  export async function canLeave() {return controller.canLeave();}
</script>
<div bind:this={container} class="vp-mounted-app"></div>

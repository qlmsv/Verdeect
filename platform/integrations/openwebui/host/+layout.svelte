<script lang="ts">
  import {page} from '$app/stores';
  import {theme} from '$lib/stores';
  import PlatformFrame from '$lib/platform/PlatformFrame.svelte';
  import '$lib/platform/tokens.css';
</script>
<PlatformFrame onThemeChange={(value) => theme.set(value)} enabled={!$page.url.pathname.startsWith('/auth') && !$page.url.pathname.startsWith('/error')}><slot /></PlatformFrame>

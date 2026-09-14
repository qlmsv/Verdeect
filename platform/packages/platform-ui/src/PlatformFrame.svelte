<script lang="ts">
  import {onMount} from 'svelte';
  import {page} from '$app/stores';
  import {PlatformClient, type PlatformSession} from './client';
  export let enabled = true;
  export let onThemeChange: (value: 'dark' | 'light') => void = () => {};
  let session: PlatformSession | null = null;
  let mobileOpen = false;
  let dark = false;
  let failure = '';
  const api = new PlatformClient();
  onMount(() => {
    if (enabled) api.session().then(s => session = s).catch(e => failure = e.message);
    dark = document.documentElement.classList.contains('dark');
    const observer = new MutationObserver(() => dark = document.documentElement.classList.contains('dark'));
    observer.observe(document.documentElement, {attributes:true, attributeFilter:['class']});
    return () => observer.disconnect();
  });
  function toggleTheme() {
    dark = !dark;
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
    onThemeChange(dark ? 'dark' : 'light');
  }
  function guardChatExit(event: MouseEvent) {
    // M0: root upstream layout assumes document lifetime. Do not silently tear down a chat.
    if (!$page.url.pathname.startsWith('/_platform') && !confirm('Переход перезагрузит страницу. Сохраните черновик и дождитесь завершения ответа. Продолжить?')) event.preventDefault();
  }
</script>

{#if enabled}
<div class="vp-frame">
  <button class="vp-mobile-toggle" aria-label="Меню приложений" on:click={() => mobileOpen = !mobileOpen}>☰</button>
  <aside class:open={mobileOpen} aria-label="Приложения платформы">
    <div class="vp-mark" title="Платформа VERDEECT">V</div>
    <nav>
      {#each session?.modules ?? [] as module}
        <a href={module.route} data-sveltekit-reload on:click={guardChatExit}
          aria-current={module.id === 'chat' ? (!$page.url.pathname.startsWith('/_platform') ? 'page' : undefined) : ($page.url.pathname.startsWith(module.route) ? 'page' : undefined)}>
          <span aria-hidden="true">{module.id === 'chat' ? '◉' : '▤'}</span><small>{module.id === 'chat' ? 'ИИ' : module.title}</small>
        </a>
      {/each}
      {#if session && ['owner','admin'].includes(session.role)}
        <a href="/_platform/manage" data-sveltekit-reload on:click={guardChatExit} aria-current={$page.url.pathname === '/_platform/manage' ? 'page' : undefined}><span aria-hidden="true">⚙</span><small>Доступы</small></a>
      {/if}
    </nav>
    <div class="vp-bottom">
      {#if !session}<a href="/_platform/login" data-sveltekit-reload title={failure || 'Войти'}><span>↪</span><small>Вход</small></a>{/if}
      <button on:click={toggleTheme} aria-label="Переключить тему">{dark ? '☀' : '☾'}</button>
      {#if session}<a href="/_platform/manage" data-sveltekit-reload title={`${session.user.name}: ${session.organization.name}`}><span class="vp-avatar">{session.user.name.slice(0,1)}</span><small>{session.organization.name}</small></a>{/if}
    </div>
  </aside>
  <div class="vp-content"><slot /></div>
</div>
{:else}<slot />{/if}

<style>
  .vp-frame{height:100dvh;display:flex;background:var(--vp-bg);color:var(--vp-text)}
  aside{flex:0 0 var(--vp-rail);width:var(--vp-rail);box-sizing:border-box;border-right:1px solid var(--vp-border);display:flex;flex-direction:column;align-items:center;gap:16px;padding:18px 7px;background:var(--vp-panel);font-family:system-ui,sans-serif}
  .vp-mark{font-weight:700;font-size:22px;padding:8px}
  nav,.vp-bottom{display:flex;flex-direction:column;gap:8px;width:100%;align-items:center}
  .vp-bottom{margin-top:auto}
  a,button{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;width:60px;min-height:52px;text-decoration:none;border:0;border-radius:12px;background:transparent;color:var(--vp-muted);cursor:pointer}
  a:hover,button:hover,a[aria-current=page]{background:var(--vp-active);color:var(--vp-text)}
  a>span{font-size:21px}small{font-size:10px;max-width:60px;overflow:hidden;text-overflow:ellipsis} .vp-avatar{font-size:16px}
  .vp-content{flex:1;min-width:0;min-height:0;overflow:auto;position:relative;contain:layout;isolation:isolate}
  .vp-mobile-toggle{display:none}
  :focus-visible{outline:2px solid var(--vp-text);outline-offset:2px}
  @media(max-width:700px){aside{display:none}aside.open{display:flex;position:absolute;z-index:9000;height:100dvh;box-shadow:0 0 0 100vmax #0005}.vp-mobile-toggle{display:block;position:fixed;bottom:16px;left:12px;z-index:9001;width:44px;min-height:44px;background:var(--vp-active);border:1px solid var(--vp-border)}.vp-content{width:100%}}
</style>

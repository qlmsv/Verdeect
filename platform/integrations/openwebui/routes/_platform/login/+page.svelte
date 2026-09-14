<script lang="ts">
  import {onMount} from 'svelte';
  import {PlatformClient} from '$lib/platform/client';
  let ticket = ''; let error = ''; let busy = false;
  let config = {oidc_enabled:false, dev_login_enabled:false, production_ready:false};
  const api = new PlatformClient();
  onMount(() => {api.request<typeof config>('/auth/config').then(c => config = c).catch(e => error = e.message);});
  async function login() {
    busy = true; error = '';
    try { await api.request('/dev/login','POST',{ticket}); ticket=''; location.assign('/_platform/apps/meters'); }
    catch(e) { error = e instanceof Error ? e.message : 'Ошибка входа'; }
    finally {busy=false;}
  }
</script>
<svelte:head><title>Вход в платформу</title></svelte:head>
<div class="vp-page"><h1>Единый аккаунт</h1><p class="vp-muted">Вход в организацию и доступные приложения.</p>
  {#if error}<p class="vp-error" role="alert">{error}</p>{/if}
  {#if config.oidc_enabled}<div class="vp-card"><a href="/_platform/api/auth/login" data-sveltekit-reload>Войти через единый аккаунт</a></div>{/if}
  {#if config.dev_login_enabled}<div class="vp-card"><h2>Вход разработчика</h2><p class="vp-muted">Одноразовый билет из platformctl. Это не пользовательский пароль и не production-вход.</p><form on:submit|preventDefault={login}><label>Одноразовый билет<input type="password" bind:value={ticket} autocomplete="off" required minlength="32" /></label><button disabled={busy}>Войти на стенд</button></form></div>{/if}
  {#if !config.oidc_enabled && !config.dev_login_enabled}<p>Провайдер входа ещё не настроен.</p>{/if}
</div>

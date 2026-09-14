<script lang="ts">
  import {onMount} from 'svelte';
  import {PlatformClient, type PlatformSession} from '$lib/platform/client';
  type Member={id:string;name:string;email:string;role:string;active:boolean;grants:Record<string,string[]>};
  const api=new PlatformClient();
  let session:PlatformSession|null=null; let members:Member[]=[]; let error=''; let busy=''; let notice='';
  const scopeNames:Record<string,string>={'meters.read':'Просмотр','meters.readings.create':'Ввод показаний','meters.manage':'Добавление приборов'};
  onMount(() => {load();});
  async function load() {
    try {session=await api.session(); if(['owner','admin'].includes(session.role)) members=await api.request<Member[]>(`/organizations/${session.organization.id}/members`);}
    catch(e) {error=e instanceof Error ? e.message : 'Ошибка загрузки';}
  }
  function change(member:Member,scope:string,checked:boolean) {
    const next=new Set(member.grants.metering??[]); checked ? next.add(scope) : next.delete(scope);
    member.grants={...member.grants,metering:[...next]}; members=[...members];
  }
  async function save(member:Member) {
    if(!session)return; busy=member.id;error='';notice='';
    try {await api.request(`/organizations/${session.organization.id}/members/${member.id}/module-grants/metering`,'PUT',{scopes:member.grants.metering??[]});notice='Доступ к счётчикам сохранён. Старые служебные токены действуют не более 30 секунд.';}
    catch(e) {error=e instanceof Error ? e.message : 'Ошибка сохранения';} finally {busy='';}
  }
  async function logout() {
    try {await api.request('/session/logout','POST');location.assign('/_platform/login');}
    catch(e) {error=e instanceof Error ? e.message : 'Ошибка выхода';}
  }
</script>
<svelte:head><title>Доступы | Платформа</title></svelte:head>
<div class="vp-page"><h1>Сотрудники и доступы</h1><p class="vp-muted">{session?.organization.name ?? 'Организация'}</p>
  {#if error}<p class="vp-error" role="alert">{error}</p>{/if}{#if notice}<p role="status">{notice}</p>{/if}
  {#if session}
    <section class="vp-card"><strong>{session.user.name}</strong><p>{session.user.email}</p><button on:click={logout}>Завершить платформенную сессию</button><p class="vp-muted">Глобальный выход из OpenWebUI и IdP будет подключён следующим этапом.</p></section>
    {#if ['owner','admin'].includes(session.role)}
      {#each members as member}<section class="vp-card"><strong>{member.name}</strong><p class="vp-muted">{member.email} · {member.role}</p><div style="display:flex;gap:16px;flex-wrap:wrap">
        {#each Object.entries(scopeNames) as [scope,title]}<label style="flex-direction:row;align-items:center"><input type="checkbox" checked={(member.grants.metering??[]).includes(scope)} disabled={!member.active || Boolean(busy)} on:change={(e) => change(member,scope,e.currentTarget.checked)} />{title}</label>{/each}
        <button disabled={!member.active || Boolean(busy)} on:click={() => save(member)}>Сохранить</button>
      </div></section>{/each}
      <p class="vp-muted">Назначения OpenWebUI пока недоступны: серверный адаптер синхронизации ещё не реализован.</p>
    {:else}<p class="vp-muted">Управлять сотрудниками может администратор организации.</p>{/if}
  {/if}
</div>

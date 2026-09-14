<script lang="ts">
  import {onMount} from 'svelte';
  import {beforeNavigate} from '$app/navigation';
  import {PlatformClient, type PlatformSession, type Meter, type Reading} from '$lib/platform/client';
  const api = new PlatformClient();
  let session: PlatformSession | null = null;
  let meters: Meter[] = []; let readings: Reading[] = []; let selected: Meter | null = null;
  let loading = true; let historyLoading = false; let busy = false; let error = ''; let success = '';
  let label = ''; let serial = ''; let unit = 'm3'; let location = '';
  let value = ''; let measuredAt = ''; let kind = 'normal'; let note = '';
  let pendingFingerprint = ''; let pendingKey = '';
  $: dirty = Boolean(label || serial || value || note);
  onMount(() => {initialize();});
  beforeNavigate(({cancel}) => {if(dirty && !confirm('Есть несохранённые данные. Покинуть страницу?')) cancel();});
  function beforeUnload(event: BeforeUnloadEvent) { if(dirty) {event.preventDefault(); event.returnValue='';} }
  async function initialize() {
    try { session = await api.session(); meters = await api.request<Meter[]>('/meters'); }
    catch(e) {error=message(e);} finally {loading=false;}
  }
  function message(e: unknown) {return e instanceof Error ? e.message : 'Ошибка запроса';}
  function keyFor(path: string, body: unknown) {
    const fingerprint = path + JSON.stringify(body);
    if(fingerprint !== pendingFingerprint) {pendingFingerprint=fingerprint; pendingKey=crypto.randomUUID();}
    return pendingKey;
  }
  async function selectMeter(meter: Meter) {
    selected=meter; readings=[]; historyLoading=true; error='';
    try {const rows=await api.request<Reading[]>(`/meters/${meter.id}/readings`); if(selected?.id===meter.id) readings=rows;}
    catch(e) {if(selected?.id===meter.id) error=message(e);} finally {if(selected?.id===meter.id) historyLoading=false;}
  }
  async function createMeter() {
    busy=true; error=''; success='';
    const body={label,serial,unit,location};
    try {
      await api.request('/meters','POST',body,keyFor('/meters',body));
      label='';serial='';location='';pendingFingerprint='';pendingKey='';
      meters=await api.request<Meter[]>('/meters'); success='Счётчик добавлен';
    } catch(e) {error=message(e);} finally {busy=false;}
  }
  async function submitReading() {
    if(!selected) return;
    busy=true; error=''; success='';
    try {
      const body={value,measured_at:new Date(measuredAt).toISOString(),kind,note};
      const path=`/meters/${selected.id}/readings`;
      await api.request(path,'POST',body,keyFor(path,body));
      value='';note='';pendingFingerprint='';pendingKey='';
      await selectMeter(selected); success='Показание сохранено';
    } catch(e) {error=message(e);} finally {busy=false;}
  }
</script>
<svelte:head><title>Счётчики | Платформа</title></svelte:head>
<svelte:window on:beforeunload={beforeUnload} />
<div class="vp-page">
  <h1>Счётчики</h1><p class="vp-muted">{session?.organization.name ?? 'Рабочее пространство'} · приборы и история показаний</p>
  {#if error}<div class="vp-error" role="alert">{error} {#if !session}<a href="/_platform/login">Войти в платформу</a>{/if}</div>{/if}
  {#if success}<p role="status">{success}</p>{/if}
  {#if loading}<p aria-live="polite">Загрузка…</p>{:else if session}
    <div class="vp-card" style="overflow-x:auto"><table><thead><tr><th>Прибор</th><th>Серийный номер</th><th>Расположение</th><th>Единица</th><th></th></tr></thead><tbody>
      {#each meters as meter}<tr><td>{meter.label}</td><td>{meter.serial}</td><td>{meter.location || 'Не указано'}</td><td>{meter.unit}</td><td><button on:click={() => selectMeter(meter)} disabled={busy}>Показания</button></td></tr>{/each}
      {#if meters.length===0}<tr><td colspan="5" class="vp-muted">Счётчиков пока нет.</td></tr>{/if}
    </tbody></table></div>
    {#if session.permissions.includes('meters.manage')}<section class="vp-card"><h2>Новый счётчик</h2><form on:submit|preventDefault={createMeter}>
      <label>Название<input bind:value={label} required maxlength="160" /></label><label>Серийный номер<input bind:value={serial} required maxlength="100" /></label>
      <label>Расположение<input bind:value={location} maxlength="255" /></label><label>Единица<select bind:value={unit}><option value="m3">м³</option><option value="kWh">кВт·ч</option><option value="Gcal">Гкал</option></select></label><button disabled={busy}>Добавить</button>
    </form></section>{/if}
    {#if selected}<section class="vp-card"><h2>{selected.label}</h2>
      {#if session.permissions.includes('meters.readings.create')}<form on:submit|preventDefault={submitReading}>
        <label>Показание<input bind:value={value} inputmode="decimal" pattern="[0-9]+([.][0-9]{1,6})?" required placeholder="123.456" /></label><label>Дата и время<input type="datetime-local" bind:value={measuredAt} required /></label>
        <label>Тип<select bind:value={kind}><option value="normal">Обычное</option><option value="reset">Обнуление</option><option value="replacement">Замена</option></select></label>
        <label>Примечание<input bind:value={note} maxlength="1000" /></label><button disabled={busy}>Сохранить</button>
      </form>{/if}
      {#if historyLoading}<p>Загрузка истории…</p>{:else}<table style="margin-top:16px"><thead><tr><th>Дата</th><th>Значение</th><th>Тип</th></tr></thead><tbody>{#each readings as row}<tr><td>{new Date(row.measured_at).toLocaleString('ru-RU')}</td><td>{row.value} {selected.unit}</td><td>{row.kind}</td></tr>{/each}{#if readings.length===0}<tr><td colspan="3" class="vp-muted">Показаний пока нет.</td></tr>{/if}</tbody></table>{/if}
    </section>{/if}
  {/if}
</div>

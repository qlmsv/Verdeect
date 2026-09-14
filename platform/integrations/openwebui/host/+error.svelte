<script>import {page} from '$app/stores';</script>
<div class="vp-page"><h1>{$page.status}</h1><p>{$page.error?.message ?? 'Страница недоступна'}</p><a href="/_platform/login">Вернуться к входу</a></div>

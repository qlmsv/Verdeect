# VERDEECT Platform: M0.1

Начало реализации модульной платформы на контролируемом форке OpenWebUI. Это инженерная основа, не готовый MVP и не production-релиз.

## Размещение в репозитории

Новая платформа находится в `platform/`. Корень `qlmsv/Verdeect` содержит существующее приложение на LibreChat и не изменяется этой разработкой. Рабочая ветка: `codex/platform-m0-foundation`. Не запускать команды новой платформы из корня старого приложения.

В этой поставке находятся все 53 файла исходного кода, тестов и инфраструктуры пакета M0.1. Документация адаптирована к размещению в GitHub. Это не полный checkout OpenWebUI: его закреплённый исходный код получает отдельный bootstrap-скрипт. Полное исходное ТЗ v0.2 передано ранее отдельным документом; архитектурные решения и границы текущего этапа перечислены в `docs/ARCHITECTURE.md` и `docs/STATUS.md`.

## Что реализовано

| Компонент | Состояние |
| --- | --- |
| Platform API | Организации, членство, сессии, серверные проверки доступа, аудит назначений |
| Metering API | Отдельная БД, приборы, показания, история, идемпотентность |
| Связь сервисов | Подписанные полномочия на 30 секунд с проверкой пользователя, организации, audience и scope |
| Интерфейс | Svelte-исходники навбара, счётчиков, входа и доступа сотрудников |
| OpenWebUI | Закреплён upstream v0.11.3, подготовлен проверяемый сборщик изменений |
| OIDC | Контроллер и mock-тесты; живой Keycloak и общий вход ещё не проверены |
| Будущий Twenty | Контракт подключения интерфейса и отдельный React fixture; самой CRM в runtime нет |

**Не использовать для публичного клиентского сервиса.** Собственные сервисы намеренно отклоняют `APP_ENV=production`. Нельзя обходить ограничение переименованием окружения.

## Проверка после клонирования

Нужны Python 3.11+, Node.js 22 и Git. Все дальнейшие команды выполняются из `platform/`.

```bash
git clone --branch codex/platform-m0-foundation https://github.com/qlmsv/Verdeect.git
cd Verdeect/platform
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m pytest -q
npm install --ignore-scripts --no-audit --no-fund
npm run test:sdk
python scripts/smoke_local.py
```

При переносе в GitHub локально повторно прошли 68 Python-тестов, 16 тестов SDK и 8 HTTP smoke-сценариев. HTTP-проверка запускает два настоящих процесса на loopback-портах, использует временные БД и ключи, затем останавливает процессы. Она не запускает OpenWebUI, Docker или Keycloak. Подробности: `docs/IMPLEMENTATION_REPORT.md`.

## Подготовка локального интеграционного стенда

Этот сценарий пока не подтверждён полной сборкой и браузерными тестами.

```bash
python scripts/platformctl.py init
python scripts/bootstrap_fork.py

docker compose --env-file .dev/compose.env \
  -f infra/compose.dev.yaml --profile chat up --build -d

python scripts/platformctl.py ticket
```

После успешной сборки открыть `http://localhost:8080/_platform/login` и ввести одноразовый билет. Он действует 10 минут. Не публиковать билет, ключи или содержимое `.dev/`.

`/` открывает штатный чат; `/_platform/apps/meters` открывает счётчики; `/_platform/manage` открывает доступы. В текущем dev-профиле OpenWebUI имеет собственную тестовую учётную запись. **Это ещё не единый вход.** Переходы между upstream и собственными разделами перезагружают страницу с предупреждением; бесшовная навигация ещё не принята.

Остановка без удаления данных:

```bash
docker compose --env-file .dev/compose.env \
  -f infra/compose.dev.yaml --profile chat down
```

Не добавлять `-v`, если данные нужны.

## Структура

```text
services/platform_api/     организации, права, сессии, BFF, OIDC-контроллер
services/metering_api/     отдельная БД и API счётчиков
packages/python/          схемы и подписанные полномочия
packages/platform-ui/     навбар, клиент API, тема, хост модулей
packages/ui-sdk/          независимый от фреймворка контракт
modules/metering-ui/      страницы счётчиков
integrations/openwebui/   сборщик изменений и маршруты
fixtures/react-module/   изолированный React-пример, не Twenty
infra/                    локальный Compose и Dockerfile
scripts/                  bootstrap, dev CLI, HTTP smoke
```

Никакие существующие серверы этой поставкой не обновляются. Приоритет следующего этапа: настоящая сборка OpenWebUI, браузерный тест и совместный SSO, затем серверная проверка `chat.use` и отзыв сессий. Блокеры перечислены в `docs/STATUS.md`.

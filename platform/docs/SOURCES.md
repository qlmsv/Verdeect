# Источники и границы интеграции

Эта поставка реализует стартовый этап по ТЗ модульной платформы v0.2 из текущего проекта. Полное ТЗ остаётся отдельным ранее переданным артефактом. В репозитории его основные архитектурные решения перечислены в ARCHITECTURE.md; текущая реализация и блокеры перечислены в STATUS.md.

## Закреплённый upstream

OpenWebUI: https://github.com/open-webui/open-webui

Конкретные tag, commit и blob root layout находятся в `../upstream.lock.json`. Это база интеграционного прототипа, не утверждение о последней доступной версии. Сборщик должен сохранять upstream copyright/license/branding files и историю. Проверять условия фактически используемой версии перед коммерческой поставкой.

## Справочные первичные источники

- OpenWebUI development: https://docs.openwebui.com/getting-started/advanced-topics/development/
- OpenWebUI SSO: https://docs.openwebui.com/features/authentication-access/auth/sso/
- OpenWebUI RBAC: https://docs.openwebui.com/features/authentication-access/rbac/
- OpenWebUI updates: https://docs.openwebui.com/getting-started/updating/
- OpenWebUI license: https://docs.openwebui.com/license/
- Twenty source: https://github.com/twentyhq/twenty
- Twenty SSO: https://docs.twenty.com/user-guide/permissions-access/capabilities/sso-configuration
- React DOM integration: https://react.dev/reference/react-dom/client/createRoot
- Keycloak container setup: https://www.keycloak.org/server/containers

Ссылки сохранены для разработки, а не как подтверждение выполнения интеграционных тестов. Проверять документацию против выбранного релиза, не считать возможности main автоматически доступными в закреплённом образе.

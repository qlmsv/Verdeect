# Project rules

Read README.md and docs/STATUS.md before changing the implementation.

- M0.1 is a development milestone, not a production platform.
- Keep OpenWebUI upstream history separate; use upstream.lock.json and the reviewed overlay.
- No iframe. Do not replace the native OpenWebUI chat with a custom API-only UI.
- Twenty is out of M0/MVP runtime. Later integration must preserve its complete licensed UI/backend.
- Never add a universal admin token, trust browser tenant headers, or disable authorization to fix an integration.
- Do not print secrets, change production services, or push to main automatically.
- Run Python tests and SDK tests. Report unexecuted Docker, Svelte, IdP and browser checks explicitly.
- Keep application data in the owning service. Backend object-level ACLs, global logout and upstream authz are not yet complete.

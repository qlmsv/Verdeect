import time
import uuid
from uuid import UUID
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy import select, update, delete
from verdeect_common.db import database
from verdeect_common.schemas import StrictModel, MeterCreate, ReadingCreate
from verdeect_common.security import digest, mint_delegation
from .config import Settings
from .models import Base, User, Organization, Membership, ModuleGrant, WebSession, LoginTicket, AuditEvent
from .permissions import MODULES, ALLOWED_SCOPES, membership, scopes, authorize, admin
from .auth import COOKIE_NAME, COOKIE_PATH, get_session, require_csrf, require_origin, create_session
from .oidc import install_oidc

class TicketBody(StrictModel):
    ticket: str = Field(min_length=32, max_length=128)

class GrantBody(StrictModel):
    scopes: list[str] = Field(max_length=20)


def create_app(settings: Settings, *, metering_transport=None, oauth_client=None) -> FastAPI:
    engine, sessions = database(settings.database_url)
    Base.metadata.create_all(engine)  # Development bootstrap only. Not a production migration strategy.
    app = FastAPI(title="VERDEECT Platform API", version="0.0.1", docs_url="/_platform/api/docs", openapi_url="/_platform/api/openapi.json")
    app.state.sessions = sessions
    app.state.engine = engine
    app.state.settings = settings
    install_oidc(app, settings, sessions, oauth_client)

    @app.middleware("http")
    async def response_policy(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Request-ID"] = str(uuid.uuid4())
        return response

    @app.get("/healthz")
    def health():
        return {"status": "ok", "milestone": "M0.1", "production_ready": False}

    @app.get("/_platform/api/auth/config")
    def auth_config():
        return {"oidc_enabled": bool(settings.oidc_issuer), "dev_login_enabled": settings.allow_dev_login, "production_ready": False}

    @app.post("/_platform/api/dev/login")
    def dev_login(body: TicketBody, request: Request, response: Response):
        if not settings.allow_dev_login:
            raise HTTPException(404, "Not found")
        require_origin(request, settings.public_origin)
        with sessions() as db:
            hashed = digest(body.ticket)
            ticket = db.get(LoginTicket, hashed)
            if not ticket or ticket.used or ticket.expires_at <= int(time.time()):
                raise HTTPException(401, "Тестовый билет недействителен или уже использован")
            user = db.get(User, ticket.user_id)
            if not user or not user.active:
                raise HTTPException(401, "Аккаунт отключён")
            membership(db, user.id, settings.installation_org_id, settings.installation_org_id)
            # Atomic consume, including racing requests.
            changed = db.execute(update(LoginTicket).where(LoginTicket.token_hash == hashed,
                LoginTicket.used == False, LoginTicket.expires_at > int(time.time())).values(used=True)).rowcount
            if changed != 1:
                raise HTTPException(401, "Билет уже использован")
            create_session(db, ticket.user_id, response, settings.secure_cookies, request.cookies.get(COOKIE_NAME))
        return {"authenticated": True, "method": "development-ticket"}

    @app.get("/_platform/api/me")
    def me(request: Request):
        with sessions() as db:
            session, user = get_session(request, db)
            org, member = membership(db, user.id, settings.installation_org_id, settings.installation_org_id)
            allowed = []
            permissions = []
            for module_id, descriptor in MODULES.items():
                granted = scopes(db, user.id, org.id, module_id)
                permissions.extend(granted)
                if descriptor["permission"] in granted:
                    allowed.append(descriptor)
            return {"user": {"id": user.id, "name": user.name, "email": user.email},
                "organization": {"id": org.id, "name": org.name, "origin": org.origin},
                "role": member.role, "permissions": sorted(permissions), "modules": allowed,
                "csrf_token": session.csrf, "milestone": "M0.1", "production_ready": False}

    @app.get("/_platform/api/organizations")
    def organizations(request: Request):
        with sessions() as db:
            _, user = get_session(request, db)
            rows = db.execute(select(Organization).join(Membership, Membership.org_id == Organization.id)
                .where(Membership.user_id == user.id, Membership.active == True, Organization.active == True)).scalars()
            return [{"id": org.id, "name": org.name, "origin": org.origin} for org in rows]

    @app.get("/_platform/api/organizations/{org_id}/modules")
    def org_modules(org_id: str, request: Request):
        with sessions() as db:
            _, user = get_session(request, db)
            membership(db, user.id, org_id, settings.installation_org_id)
            return [m for key, m in MODULES.items() if m["permission"] in scopes(db, user.id, org_id, key)]

    @app.get("/_platform/api/organizations/{org_id}/members")
    def members(org_id: str, request: Request):
        with sessions() as db:
            _, user = get_session(request, db)
            admin(db, user.id, org_id, settings.installation_org_id)
            rows = db.execute(select(Membership, User).join(User, User.id == Membership.user_id)
                .where(Membership.org_id == org_id)).all()
            return [{"id": u.id, "name": u.name, "email": u.email, "role": m.role, "active": m.active and u.active,
                "grants": {key: scopes(db, u.id, org_id, key) for key in MODULES}} for m, u in rows]

    def change_grant(org_id, user_id, module_id, value, request):
        if module_id not in MODULES:
            raise HTTPException(404, "Модуль не установлен")
        with sessions() as db:
            session, user = get_session(request, db)
            require_csrf(request, session, settings.public_origin)
            admin(db, user.id, org_id, settings.installation_org_id)
            target = db.get(Membership, (org_id, user_id))
            if not target or not target.active:
                raise HTTPException(404, "Участник не найден")
            if module_id == "chat":
                raise HTTPException(409, "Синхронизация доступа OpenWebUI ещё не реализована. Не имитируем её переключателем.")
            if not set(value).issubset(ALLOWED_SCOPES[module_id]):
                raise HTTPException(422, "Недопустимое разрешение")
            grant = db.get(ModuleGrant, (org_id, user_id, module_id))
            old = list(grant.scopes) if grant else []
            if grant:
                grant.scopes = sorted(set(value))
            else:
                db.add(ModuleGrant(org_id=org_id, user_id=user_id, module_id=module_id, scopes=sorted(set(value))))
            db.add(AuditEvent(id=str(uuid.uuid4()), org_id=org_id, actor_id=user.id,
                action="module.grant.changed", target_id=f"{user_id}:{module_id}",
                payload={"before": old, "after": sorted(set(value))}, created_at=int(time.time())))
            db.commit()
            return {"status": "applied", "module": module_id, "delegation_max_remaining_seconds": 30}

    @app.put("/_platform/api/organizations/{org_id}/members/{user_id}/module-grants/{module_id}")
    def grant(org_id: str, user_id: str, module_id: str, body: GrantBody, request: Request):
        return change_grant(org_id, user_id, module_id, body.scopes, request)

    @app.delete("/_platform/api/organizations/{org_id}/members/{user_id}/module-grants/{module_id}")
    def revoke(org_id: str, user_id: str, module_id: str, request: Request):
        return change_grant(org_id, user_id, module_id, [], request)

    @app.post("/_platform/api/session/logout")
    def logout(request: Request, response: Response):
        with sessions() as db:
            session, _ = get_session(request, db)
            require_csrf(request, session, settings.public_origin)
            db.delete(session)
            db.commit()
        response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH, secure=settings.secure_cookies, httponly=True, samesite="lax")
        return {"logged_out": True, "global_logout": False, "note": "OpenWebUI and IdP logout pending next milestone"}

    async def forward_meter(request: Request, path: str, permission: str, payload=None):
        with sessions() as db:
            session, user = get_session(request, db)
            authorize(db, user.id, settings.installation_org_id, settings.installation_org_id, "metering", permission)
            if request.method not in {"GET", "HEAD"}:
                require_csrf(request, session, settings.public_origin)
            token = mint_delegation(settings.delegation_private_key, settings.installation_org_id, user.id, [permission])
        headers = {"Authorization": f"Bearer {token}"}
        if "idempotency-key" in request.headers:
            headers["Idempotency-Key"] = request.headers["idempotency-key"]
        try:
            async with httpx.AsyncClient(base_url=settings.metering_url, transport=metering_transport,
                timeout=10.0, follow_redirects=False, trust_env=False) as client:
                upstream = await client.request(request.method, path, json=payload, headers=headers)
        except httpx.RequestError:
            raise HTTPException(503, "Сервис счётчиков временно недоступен")
        if 300 <= upstream.status_code < 400 or upstream.status_code >= 500:
            raise HTTPException(502, "Ошибка сервиса счётчиков")
        try:
            data = upstream.json()
        except ValueError:
            raise HTTPException(502, "Некорректный ответ сервиса счётчиков")
        return JSONResponse(data, status_code=upstream.status_code)

    @app.get("/_platform/api/meters")
    async def list_meters(request: Request):
        return await forward_meter(request, "/meters", "meters.read")

    @app.post("/_platform/api/meters")
    async def create_meter(body: MeterCreate, request: Request):
        return await forward_meter(request, "/meters", "meters.manage", body.model_dump(mode="json"))

    @app.get("/_platform/api/meters/{meter_id}/readings")
    async def list_readings(meter_id: UUID, request: Request):
        return await forward_meter(request, f"/meters/{meter_id}/readings", "meters.read")

    @app.post("/_platform/api/meters/{meter_id}/readings")
    async def add_reading(meter_id: UUID, body: ReadingCreate, request: Request):
        return await forward_meter(request, f"/meters/{meter_id}/readings", "meters.readings.create", body.model_dump(mode="json"))

    return app


def from_env():
    return create_app(Settings.from_env())

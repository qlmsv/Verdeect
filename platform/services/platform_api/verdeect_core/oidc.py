"""Authlib owns OAuth/OIDC verification; application sessions remain server-side.

The short-lived Authlib state cookie is signed, HttpOnly, and contains only
transaction state (including PKCE), never access/refresh/ID tokens. A live IdP
integration test is still required before enabling a production release.
"""
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware
from verdeect_common.security import safe_return_path
from .auth import COOKIE_NAME, create_session
from .models import User
from .permissions import membership


def install_oidc(app, settings, session_factory, injected_client=None):
    if not settings.oidc_issuer:
        return
    if injected_client is None:
        try:
            from authlib.integrations.starlette_client import OAuth
        except ImportError as exc:
            raise RuntimeError("Install services/platform_api/requirements.txt to enable OIDC") from exc
        oauth = OAuth()
        oauth.register("identity", client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret,
            server_metadata_url=settings.oidc_issuer.rstrip("/") + "/.well-known/openid-configuration",
            client_kwargs={"scope": "openid profile email", "code_challenge_method": "S256"})
        client = oauth.create_client("identity")
    else:
        client = injected_client
    app.add_middleware(SessionMiddleware, secret_key=settings.oauth_cookie_secret,
        session_cookie="verdeect_oidc_state", max_age=600,
        path="/_platform/api/auth", https_only=settings.secure_cookies, same_site="lax")

    @app.get("/_platform/api/auth/login")
    async def oidc_login(request: Request, return_to: str = "/_platform/apps/meters"):
        try:
            path = safe_return_path(return_to)
        except ValueError:
            raise HTTPException(400, "Недопустимый адрес возврата")
        request.session["return_to"] = path
        return await client.authorize_redirect(request,
            settings.public_origin + "/_platform/api/auth/callback")

    @app.get("/_platform/api/auth/callback")
    async def oidc_callback(request: Request):
        try:
            token = await client.authorize_access_token(request)
            claims = token.get("userinfo")
            if not token.get("id_token") or not claims or claims.get("iss") != settings.oidc_issuer or not claims.get("sub"):
                raise ValueError("Verified OIDC identity missing")
        except Exception:
            request.session.clear()
            raise HTTPException(401, "Проверка единого входа не пройдена")
        try:
            destination = safe_return_path(request.session.get("return_to", "/_platform/apps/meters"))
        except ValueError:
            destination = "/_platform/apps/meters"
        request.session.clear()
        with session_factory() as db:
            # Never link accounts by an email supplied by the browser or IdP.
            user = db.scalar(select(User).where(User.issuer == claims["iss"], User.subject == claims["sub"]))
            if not user or not user.active:
                raise HTTPException(403, "Аккаунт не назначен в платформу. Требуется подготовленное членство.")
            membership(db, user.id, settings.installation_org_id, settings.installation_org_id)
            response = RedirectResponse(destination, status_code=303)
            create_session(db, user.id, response, settings.secure_cookies, request.cookies.get(COOKIE_NAME))
        # Do not persist provider access/refresh tokens in cookies or localStorage.
        return response

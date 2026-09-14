from fastapi import HTTPException
from sqlalchemy.orm import Session
from .models import Membership, Organization, OrganizationModule, ModuleGrant

MODULES = {
    "chat": {"id": "chat", "title": "ИИ-чат", "route": "/", "permission": "chat.use"},
    "metering": {"id": "metering", "title": "Счётчики", "route": "/_platform/apps/meters", "permission": "meters.read"},
}
ALLOWED_SCOPES = {
    "chat": {"chat.use"},
    "metering": {"meters.read", "meters.manage", "meters.readings.create"},
}


def membership(db: Session, user_id: str, org_id: str, installation: str):
    if org_id != installation:
        raise HTTPException(404, "Организация недоступна в этой установке")
    org = db.get(Organization, org_id)
    member = db.get(Membership, (org_id, user_id))
    if not org or not org.active or not member or not member.active:
        raise HTTPException(403, "Нет доступа к организации")
    return org, member


def scopes(db: Session, user_id: str, org_id: str, module_id: str) -> list[str]:
    enabled = db.get(OrganizationModule, (org_id, module_id))
    grant = db.get(ModuleGrant, (org_id, user_id, module_id))
    if not enabled or not enabled.enabled or not grant:
        return []
    return sorted(set(grant.scopes) & ALLOWED_SCOPES.get(module_id, set()))


def authorize(db: Session, user_id: str, org_id: str, installation: str, module_id: str, permission: str):
    membership(db, user_id, org_id, installation)
    allowed = scopes(db, user_id, org_id, module_id)
    if permission not in allowed:
        raise HTTPException(403, "Недостаточно прав")
    return allowed


def admin(db: Session, user_id: str, org_id: str, installation: str):
    org, member = membership(db, user_id, org_id, installation)
    if member.role not in {"owner", "admin"}:
        raise HTTPException(403, "Требуются права администратора организации")
    return org, member

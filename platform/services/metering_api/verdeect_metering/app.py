from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import UUID, uuid4
import jwt
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from verdeect_common.db import database
from verdeect_common.security import digest, verify_delegation
from verdeect_common.schemas import MeterCreate, ReadingCreate
from .models import Base, Meter, Reading, Operation

@dataclass(frozen=True)
class Settings:
    database_url: str
    installation_org_id: str
    delegation_public_key: str
    environment: str = "development"
    def __post_init__(self):
        if self.environment not in {"development", "test"}:
            raise ValueError("M0.1 is development-only")
        if not self.installation_org_id or not self.delegation_public_key:
            raise ValueError("Installation identity and verification key required")


def create_app(settings: Settings):
    engine, sessions = database(settings.database_url)
    Base.metadata.create_all(engine)
    app = FastAPI(title="VERDEECT Metering API", version="0.0.1")
    app.state.sessions = sessions
    app.state.engine = engine

    def principal(request: Request, permission: str):
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            raise HTTPException(401, "Delegation required")
        try:
            claims = verify_delegation(header[7:], settings.delegation_public_key, settings.installation_org_id)
        except (jwt.InvalidTokenError, ValueError, TypeError):
            raise HTTPException(401, "Invalid delegation")
        if permission not in claims["scope"]:
            raise HTTPException(403, "Insufficient scope")
        return claims

    def get_meter(db, meter_id):
        meter = db.get(Meter, str(meter_id))
        if not meter or meter.org_id != settings.installation_org_id:
            raise HTTPException(404, "Счётчик не найден")
        return meter

    def serialize_meter(m):
        return {"id": m.id, "label": m.label, "serial": m.serial, "unit": m.unit, "location": m.location}

    def serialize_reading(r):
        return {k: getattr(r, k) for k in ("id", "meter_id", "value", "measured_at", "kind", "note", "author_id", "created_at")}

    def idempotent(db, actor, key, operation_path, body, action):
        fingerprint = digest(json.dumps({"operation": operation_path, "payload": body}, sort_keys=True, separators=(",", ":")))
        existing = db.get(Operation, (actor, str(key)))
        if existing:
            if existing.request_hash != fingerprint:
                raise HTTPException(409, "Idempotency-Key уже использован с другим запросом")
            return JSONResponse(existing.result, status_code=201, headers={"Idempotent-Replay": "true"})
        try:
            result = action()
            db.add(Operation(actor_id=actor, key=str(key), request_hash=fingerprint, result=result))
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.get(Operation, (actor, str(key)))
            if existing and existing.request_hash == fingerprint:
                return JSONResponse(existing.result, status_code=201, headers={"Idempotent-Replay": "true"})
            raise HTTPException(409, "Конфликт повторного запроса или серийного номера")
        return JSONResponse(result, status_code=201)

    @app.get("/healthz")
    def health():
        return {"status": "ok", "module": "metering", "production_ready": False}

    @app.get("/meters")
    def meters(request: Request):
        principal(request, "meters.read")
        with sessions() as db:
            return [serialize_meter(m) for m in db.scalars(select(Meter).where(Meter.org_id == settings.installation_org_id).order_by(Meter.label, Meter.id).limit(1000))]

    @app.post("/meters")
    def create_meter(body: MeterCreate, request: Request, idempotency_key: UUID = Header(alias="Idempotency-Key")):
        claims = principal(request, "meters.manage")
        with sessions() as db:
            def action():
                meter = Meter(id=str(uuid4()), org_id=settings.installation_org_id, **body.model_dump())
                db.add(meter)
                return serialize_meter(meter)
            return idempotent(db, claims["sub"], idempotency_key, "/meters", body.model_dump(mode="json"), action)

    @app.get("/meters/{meter_id}/readings")
    def readings(meter_id: UUID, request: Request):
        principal(request, "meters.read")
        with sessions() as db:
            get_meter(db, meter_id)
            return [serialize_reading(r) for r in db.scalars(select(Reading).where(Reading.meter_id == str(meter_id)).order_by(Reading.measured_at.desc(), Reading.id.desc()).limit(100))]

    @app.post("/meters/{meter_id}/readings")
    def add_reading(meter_id: UUID, body: ReadingCreate, request: Request, idempotency_key: UUID = Header(alias="Idempotency-Key")):
        claims = principal(request, "meters.readings.create")
        with sessions() as db:
            get_meter(db, meter_id)
            def action():
                reading = Reading(id=str(uuid4()), meter_id=str(meter_id), value=format(body.value, "f"),
                    measured_at=body.measured_at.isoformat(), kind=body.kind, note=body.note,
                    author_id=claims["sub"], created_at=datetime.now(timezone.utc).isoformat())
                db.add(reading)
                return serialize_reading(reading)
            return idempotent(db, claims["sub"], idempotency_key, f"/meters/{meter_id}/readings", body.model_dump(mode="json"), action)
    return app


def from_env():
    return create_app(Settings(database_url=os.environ["DATABASE_URL"],
        installation_org_id=os.environ["INSTALLATION_ORG_ID"],
        delegation_public_key=Path(os.environ["DELEGATION_PUBLIC_KEY_FILE"]).read_text(),
        environment=os.getenv("APP_ENV", "development")))

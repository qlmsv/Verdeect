from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Meter(Base):
    __tablename__ = "meters"
    __table_args__ = (UniqueConstraint("org_id", "serial"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), index=True)
    label: Mapped[str] = mapped_column(String(160))
    serial: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(20))
    location: Mapped[str] = mapped_column(String(255), default="")

class Reading(Base):
    __tablename__ = "readings"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    meter_id: Mapped[str] = mapped_column(ForeignKey("meters.id"), index=True)
    value: Mapped[str] = mapped_column(String(40))
    measured_at: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(String(1000))
    author_id: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[str] = mapped_column(String(40))

class Operation(Base):
    __tablename__ = "idempotency_operations"
    actor_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON)

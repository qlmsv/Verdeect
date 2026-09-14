from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class MeterCreate(StrictModel):
    label: str = Field(min_length=1, max_length=160)
    serial: str = Field(min_length=1, max_length=100)
    unit: Literal["m3", "kWh", "Gcal"]
    location: str = Field(default="", max_length=255)

    @field_validator("label", "serial")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Value cannot be blank")
        return value.strip()

class ReadingCreate(StrictModel):
    value: Decimal = Field(ge=0, max_digits=20, decimal_places=6)
    measured_at: datetime
    kind: Literal["normal", "reset", "replacement"] = "normal"
    note: str = Field(default="", max_length=1000)

    @field_validator("value", mode="before")
    @classmethod
    def decimal_string(cls, value):
        if not isinstance(value, str):
            raise ValueError("Send value as a decimal string, not a binary float")
        return value

    @field_validator("measured_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone is required")
        if value > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Measurement cannot be in the future")
        return value.astimezone(timezone.utc)

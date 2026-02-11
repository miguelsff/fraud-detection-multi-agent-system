"""Transaction and behavioral signal models produced by collection agents."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionSignals(BaseModel):
    """Contextual signals extracted from a transaction."""

    amount_ratio: float = Field(ge=0)
    is_off_hours: bool
    is_foreign: bool
    is_unknown_device: bool
    channel_risk: Literal["low", "medium", "high"]
    flags: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount_ratio": 3.6,
                "is_off_hours": True,
                "is_foreign": False,
                "is_unknown_device": False,
                "channel_risk": "medium",
                "flags": ["high_amount", "off_hours"],
            }
        }
    )


class BehavioralSignals(BaseModel):
    """Behavioral deviation signals from customer history analysis."""

    deviation_score: float
    anomalies: list[str]
    velocity_alert: bool

    @field_validator("deviation_score")
    @classmethod
    def validate_deviation_score(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("deviation_score must be between 0.0 and 1.0")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "deviation_score": 0.78,
                "anomalies": ["amount_spike", "unusual_hour"],
                "velocity_alert": False,
            }
        }
    )

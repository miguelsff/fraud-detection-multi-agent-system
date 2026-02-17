"""Transaction and customer behavior models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Transaction(BaseModel):
    """A financial transaction to be analyzed for fraud."""

    transaction_id: str
    customer_id: str
    amount: float = Field(gt=0)
    currency: str
    country: str
    channel: str
    device_id: str
    timestamp: datetime
    merchant_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transaction_id": "T-1001",
                "customer_id": "C-501",
                "amount": 1800.00,
                "currency": "PEN",
                "country": "PE",
                "channel": "web",
                "device_id": "D-01",
                "timestamp": "2025-01-15T03:15:00Z",
                "merchant_id": "M-200",
            }
        }
    )


class CustomerBehavior(BaseModel):
    """Historical behavior profile for a customer."""

    customer_id: str
    usual_amount_avg: float = Field(ge=0)
    usual_hours: str
    usual_countries: list[str]
    usual_devices: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "C-501",
                "usual_amount_avg": 500.00,
                "usual_hours": "08:00-22:00",
                "usual_countries": ["PE"],
                "usual_devices": ["D-01", "D-02"],
            }
        }
    )

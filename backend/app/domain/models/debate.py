"""Debate models for adversarial pro-fraud vs pro-customer argumentation."""

from pydantic import BaseModel, ConfigDict, field_validator


class DebateArguments(BaseModel):
    """Arguments from the adversarial debate between pro-fraud and pro-customer agents."""

    pro_fraud_argument: str
    pro_fraud_confidence: float
    pro_fraud_evidence: list[str]
    pro_customer_argument: str
    pro_customer_confidence: float
    pro_customer_evidence: list[str]

    @field_validator("pro_fraud_confidence", "pro_customer_confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pro_fraud_argument": "La transacción de S/1800 a las 03:15 representa 3.6x el promedio del cliente. "
                "El horario nocturno combinado con el monto elevado coincide con el patrón FP-01 de fraude.",
                "pro_fraud_confidence": 0.78,
                "pro_fraud_evidence": [
                    "amount_ratio: 3.6x",
                    "off_hours: 03:15",
                    "policy_match: FP-01",
                ],
                "pro_customer_argument": "El cliente ha realizado compras anteriores por montos similares en este comercio. "
                "El dispositivo D-01 es conocido y el país coincide con su perfil habitual (PE).",
                "pro_customer_confidence": 0.55,
                "pro_customer_evidence": [
                    "known_device: D-01",
                    "same_country: PE",
                    "merchant_history: positive",
                ],
            }
        }
    )

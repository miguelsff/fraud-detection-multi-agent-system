"""Evidence models for policy matches, threat intel, and aggregated evidence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RiskCategory = Literal["low", "medium", "high", "critical"]


class PolicyMatch(BaseModel):
    """A single policy match from RAG retrieval."""

    policy_id: str
    description: str
    relevance_score: float

    @field_validator("relevance_score")
    @classmethod
    def validate_relevance_score(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("relevance_score must be between 0.0 and 1.0")
        return v


class PolicyMatchResult(BaseModel):
    """Aggregated result from the Policy RAG agent."""

    matches: list[PolicyMatch]
    chunk_ids: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "matches": [
                    {
                        "policy_id": "FP-01",
                        "description": "Transacciones nocturnas superiores a 3x el promedio requieren verificación adicional",
                        "relevance_score": 0.92,
                    }
                ],
                "chunk_ids": ["chunk-fp01-001"],
            }
        }
    )


class ThreatSource(BaseModel):
    """A single external threat intelligence source."""

    source_name: str
    confidence: float

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class ThreatIntelResult(BaseModel):
    """Result from the External Threat agent."""

    threat_level: float
    sources: list[ThreatSource]

    @field_validator("threat_level")
    @classmethod
    def validate_threat_level(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("threat_level must be between 0.0 and 1.0")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "threat_level": 0.35,
                "sources": [
                    {
                        "source_name": "merchant_watchlist",
                        "confidence": 0.4,
                    }
                ],
            }
        }
    )


class AggregatedEvidence(BaseModel):
    """Consolidated evidence from all collection agents."""

    composite_risk_score: float = Field(ge=0, le=100)
    all_signals: list[str]
    all_citations: list[str]
    risk_category: RiskCategory

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "composite_risk_score": 68.5,
                "all_signals": [
                    "high_amount",
                    "off_hours",
                    "amount_spike",
                    "policy_match_FP-01",
                ],
                "all_citations": ["FP-01: Transacciones nocturnas > 3x promedio"],
                "risk_category": "high",
            }
        }
    )

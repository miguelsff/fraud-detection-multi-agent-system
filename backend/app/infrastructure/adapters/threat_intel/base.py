"""Re-export ThreatProvider ABC from ports (backward compatibility)."""

from app.application.ports.threat_intel import ThreatProvider

__all__ = ["ThreatProvider"]

"""Helper functions extracted from external_threat.py.

Provides baseline calculation, provider classification, and
threat analysis response parsing.
"""

import re
from typing import Optional

from ..models import ThreatSource
from ..utils.logger import get_logger
from .llm_utils import clamp_float, parse_json_response

logger = get_logger(__name__)


def calculate_baseline_from_sources(sources: list[ThreatSource]) -> float:
    """Calculate deterministic baseline threat level from all sources.

    Strategy:
    - Use max confidence as primary signal (highest risk source)
    - Add 0.1 bonus for each additional source (multi-source corroboration)
    - Clamp result to [0.0, 1.0]
    """
    if not sources:
        return 0.0

    max_confidence = max(s.confidence for s in sources)
    multi_source_bonus = 0.1 * (len(sources) - 1) if len(sources) > 1 else 0.0
    threat_level = min(1.0, max_confidence + multi_source_bonus)

    return round(threat_level, 2)


def classify_provider_type(source_name: str) -> str:
    """Classify provider type based on source_name for LLM context.

    Returns:
        Human-readable provider type: "FATF", "OSINT", or "Sanctions"
    """
    source_lower = source_name.lower()

    if any(keyword in source_lower for keyword in ["fatf", "blacklist", "graylist", "elevated_risk"]):
        return "FATF"
    elif any(keyword in source_lower for keyword in ["osint", "web_search"]):
        return "OSINT"
    elif any(keyword in source_lower for keyword in ["sanctions", "opensanctions"]):
        return "Sanctions"
    else:
        return "Unknown"


def parse_threat_analysis(response_text: str) -> tuple[Optional[float], str]:
    """Parse LLM response to extract threat level and explanation.

    Returns:
        Tuple of (threat_level, explanation). threat_level is None if parsing fails.
    """
    # Stage 1: JSON parsing
    data = parse_json_response(response_text, "threat_level", "external_threat")
    if data:
        try:
            threat_level = clamp_float(float(data["threat_level"]))
            explanation = data.get("explanation", "No explanation provided")
            logger.info("llm_threat_response_parsed_json", threat_level=threat_level)
            return threat_level, explanation
        except (KeyError, ValueError):
            pass

    # Stage 2: Regex fallback
    pattern = r'"?threat_level"?\s*:\s*(0\.\d+|1\.0|0|1)'
    match = re.search(pattern, response_text, re.IGNORECASE)
    if match:
        threat_level = clamp_float(float(match.group(1)))
        logger.info("llm_threat_response_parsed_regex", threat_level=threat_level)
        return threat_level, "Extracted via regex"

    return None, "Parse failed"

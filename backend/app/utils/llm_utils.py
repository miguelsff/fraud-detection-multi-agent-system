"""Shared LLM response parsing utilities.

Consolidates the JSON extraction and parsing logic duplicated across
decision_arbiter, debate, policy_rag, external_threat, and explainability agents.
"""

import json
import re

from ..exceptions import LLMParsingError


def extract_json_from_text(text: str, anchor_field: str, agent_name: str = "unknown") -> str:
    """Extract JSON object from LLM response text.

    Tries two strategies:
    1. JSON inside markdown code blocks (```json ... ```)
    2. Raw JSON containing the anchor_field

    Args:
        text: Raw LLM response text
        anchor_field: A field name expected in the JSON (e.g., "decision", "argument")
        agent_name: Agent name for error reporting

    Returns:
        Extracted JSON string

    Raises:
        LLMParsingError: If no JSON found
    """
    # Strategy 1: markdown code block
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        return json_match.group(1)

    # Strategy 2: raw JSON with anchor field
    json_match = re.search(rf'\{{.*"{anchor_field}".*\}}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)

    raise LLMParsingError(agent_name, text)


def parse_json_response(text: str, anchor_field: str, agent_name: str = "unknown") -> dict | None:
    """Extract and parse JSON from LLM response text.

    Args:
        text: Raw LLM response text
        anchor_field: A field name expected in the JSON
        agent_name: Agent name for error reporting

    Returns:
        Parsed dict, or None if parsing fails
    """
    try:
        json_str = extract_json_from_text(text, anchor_field, agent_name)
        return json.loads(json_str)
    except (LLMParsingError, json.JSONDecodeError):
        return None


def clamp_float(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a float value to a range.

    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Clamped value
    """
    return max(min_val, min(max_val, float(value)))

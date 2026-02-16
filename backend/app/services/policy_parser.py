"""Markdown parser for fraud detection policies.

Handles bidirectional conversion between markdown files and Pydantic models.
Extracted from PolicyService following SRP.
"""

import re

from ..exceptions import InvalidPolicyFormatError
from ..models.policy import PolicyAction, PolicyCreate, PolicyResponse, PolicySeverity


def parse_markdown_to_model(content: str, file_name: str) -> PolicyResponse:
    """Parse markdown content to PolicyResponse model.

    Args:
        content: Markdown file content
        file_name: Name of the source file

    Returns:
        PolicyResponse model

    Raises:
        InvalidPolicyFormatError: If markdown structure is invalid
    """
    header_match = re.search(r"^## (FP-\d{2}):\s*(.+)$", content, re.MULTILINE)
    if not header_match:
        raise InvalidPolicyFormatError("missing policy header (## FP-XX: Title)")

    policy_id = header_match.group(1)
    title = header_match.group(2).strip()

    description = _extract_section(content, "Descripción")
    criteria = _extract_list_section(content, "Criterios de Activación")
    thresholds = _extract_list_section(content, "Umbrales Específicos")
    action_text = _extract_section(content, "Acción Recomendada")

    action_recommended = _extract_action(action_text)
    severity = _extract_severity(content, action_recommended)

    return PolicyResponse(
        policy_id=policy_id,
        title=title,
        description=description,
        criteria=criteria,
        thresholds=thresholds,
        action_recommended=action_recommended,
        severity=severity,
        file_path=f"policies/{file_name}",
    )


def model_to_markdown(policy: PolicyCreate) -> str:
    """Convert PolicyCreate model to markdown format."""
    criteria_list = "\n".join(f"- {item}" for item in policy.criteria)
    thresholds_list = "\n".join(f"- {item}" for item in policy.thresholds)

    return f"""## {policy.policy_id}: {policy.title}

**Descripción:**
{policy.description}

**Criterios de Activación:**
{criteria_list}

**Umbrales Específicos:**
{thresholds_list}

**Acción Recomendada:**
{policy.action_recommended}

**Severidad:**
{policy.severity}
"""


def _extract_section(content: str, section_name: str) -> str:
    """Extract text content from a markdown section.

    Raises:
        InvalidPolicyFormatError: If section not found
    """
    pattern = rf"\*\*{re.escape(section_name)}:\*\*\s*\n(.+?)(?=\n\*\*|\n##|\Z)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        raise InvalidPolicyFormatError(f"section not found: {section_name}")

    return match.group(1).strip()


def _extract_list_section(content: str, section_name: str) -> list[str]:
    """Extract bullet list from a markdown section.

    Raises:
        InvalidPolicyFormatError: If section not found or has no items
    """
    section_text = _extract_section(content, section_name)

    items = [
        line.strip()[2:].strip()
        for line in section_text.split("\n")
        if line.strip().startswith("- ")
    ]

    if not items:
        raise InvalidPolicyFormatError(f"no list items in section: {section_name}")

    return items


def _extract_action(action_text: str) -> PolicyAction:
    """Extract action keyword from action text.

    Raises:
        InvalidPolicyFormatError: If no valid action found
    """
    if "ESCALATE_TO_HUMAN" in action_text or "ESCALATE" in action_text:
        return "ESCALATE_TO_HUMAN"
    elif "BLOCK" in action_text:
        return "BLOCK"
    elif "CHALLENGE" in action_text:
        return "CHALLENGE"
    elif "APPROVE" in action_text:
        return "APPROVE"
    else:
        raise InvalidPolicyFormatError(f"no valid action in text: {action_text[:50]}...")


def _extract_severity(content: str, action: PolicyAction) -> PolicySeverity:
    """Extract or infer severity level."""
    try:
        severity_text = _extract_section(content, "Severidad")
        severity_upper = severity_text.upper()

        if "CRITICAL" in severity_upper:
            return "CRITICAL"
        elif "HIGH" in severity_upper:
            return "HIGH"
        elif "MEDIUM" in severity_upper:
            return "MEDIUM"
        elif "LOW" in severity_upper:
            return "LOW"
    except InvalidPolicyFormatError:
        pass

    severity_map: dict[PolicyAction, PolicySeverity] = {
        "BLOCK": "HIGH",
        "CHALLENGE": "MEDIUM",
        "APPROVE": "LOW",
        "ESCALATE_TO_HUMAN": "CRITICAL",
    }

    return severity_map.get(action, "MEDIUM")

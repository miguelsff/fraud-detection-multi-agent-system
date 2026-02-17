"""Custom exception hierarchy for the fraud detection system.

Each exception type maps to a specific error category, enabling
precise error handling in routers and agents.
"""


class FraudDetectionError(Exception):
    """Base exception for all fraud detection system errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PolicyNotFoundError(FraudDetectionError):
    """Raised when a policy file or ID does not exist."""

    def __init__(self, policy_id: str):
        super().__init__(
            message=f"Policy {policy_id} not found",
            details={"policy_id": policy_id},
        )


class PolicyExistsError(FraudDetectionError):
    """Raised when attempting to create a policy that already exists."""

    def __init__(self, policy_id: str):
        super().__init__(
            message=f"Policy {policy_id} already exists",
            details={"policy_id": policy_id},
        )


class InvalidPolicyFormatError(FraudDetectionError):
    """Raised when a policy markdown file has invalid structure."""

    def __init__(self, detail: str):
        super().__init__(
            message=f"Invalid policy format: {detail}",
            details={"detail": detail},
        )


class LLMParsingError(FraudDetectionError):
    """Raised when an LLM response cannot be parsed to the expected format."""

    def __init__(self, agent_name: str, response_text: str = ""):
        super().__init__(
            message=f"No JSON found in LLM response from {agent_name}",
            details={
                "agent_name": agent_name,
                "response_preview": response_text[:200] if response_text else "",
            },
        )


class LLMTimeoutError(FraudDetectionError):
    """Raised when an LLM call exceeds the configured timeout."""

    def __init__(self, agent_name: str, timeout_seconds: float):
        super().__init__(
            message=f"LLM timeout in {agent_name} after {timeout_seconds}s",
            details={
                "agent_name": agent_name,
                "timeout_seconds": timeout_seconds,
            },
        )

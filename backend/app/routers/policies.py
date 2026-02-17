"""
API endpoints for fraud policy management (CRUD operations).

Endpoints:
    GET    /api/v1/policies           - List all policies
    GET    /api/v1/policies/{id}      - Get single policy
    POST   /api/v1/policies           - Create new policy
    PUT    /api/v1/policies/{id}      - Update existing policy
    DELETE /api/v1/policies/{id}      - Delete policy
    POST   /api/v1/policies/reingest  - Manual ChromaDB reingest
"""

from fastapi import APIRouter, HTTPException, status

from ..exceptions import (
    InvalidPolicyFormatError,
    PolicyExistsError,
    PolicyNotFoundError,
)
from ..models.policy import PolicyCreate, PolicyResponse, PolicyUpdate
from ..services.policy_service import PolicyService
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


@router.get("/", response_model=list[PolicyResponse])
async def list_policies() -> list[PolicyResponse]:
    """List all fraud detection policies.

    Returns:
        List of all policies sorted by policy_id

    Example:
        GET /api/v1/policies
        Response: [
            {
                "policy_id": "FP-01",
                "title": "Política de Montos Inusuales",
                "description": "...",
                "criteria": ["..."],
                "thresholds": ["..."],
                "action_recommended": "CHALLENGE",
                "severity": "MEDIUM",
                "file_path": "policies/FP-01.md"
            },
            ...
        ]
    """
    service = PolicyService()
    policies = service.list_policies()

    logger.info("api_list_policies", count=len(policies))
    return policies


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: str) -> PolicyResponse:
    """Get a single policy by ID.

    Args:
        policy_id: Policy identifier (e.g., "FP-01")

    Returns:
        Policy details

    Raises:
        404: Policy not found
        400: Invalid policy_id format

    Example:
        GET /api/v1/policies/FP-01
    """
    service = PolicyService()

    try:
        policy = service.get_policy(policy_id)
        logger.info("api_get_policy", policy_id=policy_id)
        return policy
    except PolicyNotFoundError as e:
        logger.warning("api_policy_not_found", policy_id=policy_id)
        raise HTTPException(status_code=404, detail=e.message)
    except InvalidPolicyFormatError as e:
        logger.warning("api_invalid_policy_format", policy_id=policy_id, error=e.message)
        raise HTTPException(status_code=422, detail=e.message)


@router.post("/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(policy: PolicyCreate) -> PolicyResponse:
    """Create a new fraud detection policy.

    Args:
        policy: Policy data (PolicyCreate model)

    Returns:
        Created policy with file_path

    Raises:
        400: Policy already exists or invalid data

    Example:
        POST /api/v1/policies
        Body: {
            "policy_id": "FP-16",
            "title": "New Policy",
            "description": "...",
            "criteria": ["criterion 1", "criterion 2"],
            "thresholds": ["threshold 1"],
            "action_recommended": "CHALLENGE",
            "severity": "MEDIUM"
        }
    """
    service = PolicyService()

    try:
        created = service.create_policy(policy)
        logger.info("api_create_policy", policy_id=policy.policy_id)
        return created
    except PolicyExistsError as e:
        logger.warning("api_create_policy_exists", policy_id=policy.policy_id)
        raise HTTPException(status_code=409, detail=e.message)


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(policy_id: str, updates: PolicyUpdate) -> PolicyResponse:
    """Update an existing policy.

    Args:
        policy_id: Policy identifier
        updates: Fields to update (all optional)

    Returns:
        Updated policy

    Raises:
        404: Policy not found
        400: Invalid update data

    Example:
        PUT /api/v1/policies/FP-01
        Body: {
            "title": "Updated Title",
            "severity": "HIGH"
        }
    """
    service = PolicyService()

    try:
        updated = service.update_policy(policy_id, updates)
        logger.info("api_update_policy", policy_id=policy_id)
        return updated
    except PolicyNotFoundError as e:
        logger.warning("api_policy_not_found", policy_id=policy_id)
        raise HTTPException(status_code=404, detail=e.message)
    except InvalidPolicyFormatError as e:
        logger.warning("api_update_policy_failed", policy_id=policy_id, error=e.message)
        raise HTTPException(status_code=422, detail=e.message)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(policy_id: str) -> None:
    """Delete a policy.

    Args:
        policy_id: Policy identifier

    Returns:
        204 No Content on success

    Raises:
        404: Policy not found

    Example:
        DELETE /api/v1/policies/FP-16
    """
    service = PolicyService()

    try:
        service.delete_policy(policy_id)
        logger.info("api_delete_policy", policy_id=policy_id)
    except PolicyNotFoundError as e:
        logger.warning("api_policy_not_found", policy_id=policy_id)
        raise HTTPException(status_code=404, detail=e.message)


@router.post("/reingest", status_code=status.HTTP_202_ACCEPTED)
async def manual_reingest() -> dict[str, str]:
    """Manually trigger ChromaDB reingest of all policies.

    This endpoint is provided for troubleshooting purposes.
    Normal CRUD operations automatically reingest.

    Returns:
        Message confirming reingest started

    Example:
        POST /api/v1/policies/reingest
        Response: {"message": "Reingest started"}
    """
    service = PolicyService()
    service._reingest_chromadb()

    logger.info("api_manual_reingest_triggered")
    return {"message": "Reingest started"}

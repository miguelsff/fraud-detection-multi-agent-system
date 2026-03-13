from pydantic import BaseModel

from app.domain.models import CustomerBehavior, Transaction


class AnalyzeRequest(BaseModel):
    """Request model for transaction analysis."""

    transaction: Transaction
    customer_behavior: CustomerBehavior

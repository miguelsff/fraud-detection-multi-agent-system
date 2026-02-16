from pydantic import BaseModel

from .transaction import CustomerBehavior, Transaction


class AnalyzeRequest(BaseModel):
    """Request model for transaction analysis."""

    transaction: Transaction
    customer_behavior: CustomerBehavior

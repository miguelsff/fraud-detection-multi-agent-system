from pydantic import BaseModel
from .transaction import Transaction, CustomerBehavior

class AnalyzeRequest(BaseModel):
    """Request model for transaction analysis."""
    transaction: Transaction
    customer_behavior: CustomerBehavior
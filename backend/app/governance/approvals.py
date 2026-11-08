from enum import Enum
from typing import Any, Dict


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONFIRMATION_REQUIRED = "confirmation_required"


class ApprovalManager:
    """
    Manages human-in-the-loop and explicit confirmation boundaries
    for sensitive commerce operations such as final checkout.
    """

    CONFIRMATION_REQUIRED_TOOLS = {
        "get_checkout_preview",
        "place_order",
    }

    @classmethod
    def requires_explicit_confirmation(cls, tool_name: str, params: Dict[str, Any]) -> bool:
        """
        Determines if an action requires customer explicit confirmation
        prior to final fulfillment or state commitment.
        """
        if tool_name in cls.CONFIRMATION_REQUIRED_TOOLS:
            return True
        return False

    @classmethod
    def has_explicit_confirmation(cls, params: Dict[str, Any]) -> bool:
        """
        Verifies whether an explicit confirmation flag was provided in the request.
        """
        return bool(params.get("explicit_confirmation", False))

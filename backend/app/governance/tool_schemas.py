import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictBaseToolInput(BaseModel):
    """Base schema that strictly forbids extra unmapped fields."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchProductsInput(StrictBaseToolInput):
    query: str = Field(..., min_length=1, max_length=200, description="Product search keyword")
    category: Optional[str] = Field(None, max_length=100, description="Optional category filter")

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        # Reject raw SQL injection keywords or dangerous control characters
        dangerous = ["drop table", "alter table", "delete from", "--", ";--", "exec(", "union select"]
        lower = v.lower()
        for token in dangerous:
            if token in lower:
                raise ValueError(f"Unsafe characters or SQL patterns detected in query: '{token}'")
        return v.strip()


class GetProductDetailsInput(StrictBaseToolInput):
    product_id: uuid.UUID = Field(..., description="UUID of the product")


class AddToCartItemInput(StrictBaseToolInput):
    product_id: uuid.UUID = Field(..., description="UUID of product to add")
    quantity: float = Field(default=1.0, gt=0, le=10000, description="Requested quantity")
    unit: Optional[str] = Field(None, max_length=30, description="Unit of measurement")
    name: Optional[str] = Field(None, max_length=100, description="Product name label")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantity must be > 0")
        return v


class AddToCartInput(StrictBaseToolInput):
    product_id: Optional[uuid.UUID] = Field(None, description="UUID of product to add")
    quantity: Optional[float] = Field(None, gt=0, le=10000, description="Requested quantity")
    unit: Optional[str] = Field(None, max_length=30, description="Unit of measurement")
    items: Optional[List[AddToCartItemInput]] = Field(None, description="Batch items list")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("quantity must be > 0")
        return v


class UpdateCartItemInput(StrictBaseToolInput):
    cart_item_id: uuid.UUID = Field(..., description="UUID of the cart item to modify")
    quantity: float = Field(..., gt=0, le=10000, description="New target quantity")


class RemoveFromCartInput(StrictBaseToolInput):
    cart_item_id: uuid.UUID = Field(..., description="UUID of the cart item to remove")


class GetCartInput(StrictBaseToolInput):
    pass


class GetCheckoutPreviewInput(StrictBaseToolInput):
    explicit_confirmation: Optional[bool] = Field(
        False,
        description="Explicit user acknowledgment that this is a non-binding preview",
    )


class SubmitOrderInput(StrictBaseToolInput):
    delivery_address: Optional[str] = Field(None, description="Customer delivery location")
    payment_method: Optional[str] = Field("Card", description="Payment method preview")


TOOL_INPUT_SCHEMAS: Dict[str, type[StrictBaseToolInput]] = {
    "search_products": SearchProductsInput,
    "get_product_details": GetProductDetailsInput,
    "add_to_cart": AddToCartInput,
    "update_cart_item": UpdateCartItemInput,
    "remove_from_cart": RemoveFromCartInput,
    "get_cart": GetCartInput,
    "get_checkout_preview": GetCheckoutPreviewInput,
    "submit_order": SubmitOrderInput,
}


def validate_tool_input(tool_name: str, params: Dict[str, Any]) -> StrictBaseToolInput:
    """
    Validates parameters against strict Pydantic schemas.
    Raises ValueError with a descriptive message if invalid or unknown fields are passed.
    """
    schema_cls = TOOL_INPUT_SCHEMAS.get(tool_name)
    if not schema_cls:
        raise ValueError(f"No validation schema defined for tool '{tool_name}'")

    # Filter out system context keys (user_id, session_id, trace_id) that are injected by the framework
    filtered_params = {
        k: v for k, v in params.items()
        if k not in ("user_id", "session_id", "trace_id", "db")
    }

    # Special handling for add_to_cart when single item parameters are passed
    if tool_name == "add_to_cart":
        if not filtered_params.get("items") and not filtered_params.get("product_id"):
            raise ValueError("add_to_cart requires either 'product_id' or 'items' list")
        if filtered_params.get("product_id") and filtered_params.get("quantity") is None:
            filtered_params["quantity"] = 1.0

    try:
        return schema_cls.model_validate(filtered_params)
    except Exception as exc:
        msg = str(exc)
        if "greater than 0" in msg and "quantity" in msg:
            msg = f"quantity must be > 0 ({msg})"
        raise ValueError(f"Tool input schema validation failed for '{tool_name}': {msg}")

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.product import ProductResponse


class CartItemResponse(BaseModel):
    id: uuid.UUID
    cart_id: uuid.UUID
    product_id: uuid.UUID
    quantity: float
    unit_price_aed: float
    subtotal_aed: float
    added_at: datetime
    product: Optional[ProductResponse] = None

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    session_id: str
    items: List[CartItemResponse] = Field(default_factory=list)
    subtotal_aed: float = 0.0
    vat_aed: float = 0.0
    grand_total_aed: float = 0.0
    item_count: int = 0
    created_at: datetime
    updated_at: datetime
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AddToCartRequest(BaseModel):
    product_id: uuid.UUID
    quantity: float = Field(default=1.0, gt=0, le=10000)
    unit: Optional[str] = None
    session_id: Optional[str] = None


class UpdateCartItemRequest(BaseModel):
    quantity: float = Field(..., gt=0, le=10000)


class RemoveFromCartRequest(BaseModel):
    cart_item_id: Optional[uuid.UUID] = None

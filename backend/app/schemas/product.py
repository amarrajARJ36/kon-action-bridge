import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductResponse(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    brand: str
    category: str
    variant: Optional[str] = None
    unit_of_measurement: str
    price_aed: float
    stock_quantity: float
    is_available: bool
    image_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductSearchRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ProductSearchResponse(BaseModel):
    products: List[ProductResponse]
    total_count: int

from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from app.schemas.cart import CartResponse
from app.schemas.product import ProductResponse


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_type: Literal["text", "product_options", "basket_update"] = "text"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    message: str
    action_taken: Optional[str] = None
    products_to_select: Optional[List[ProductResponse]] = None
    basket_updated: bool = False
    cart: Optional[CartResponse] = None
    audio_base64: Optional[str] = None


class ConversationHistory(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)

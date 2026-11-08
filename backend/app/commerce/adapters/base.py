import uuid
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.cart import CartResponse


class CommerceAdapter(ABC):
    """
    Abstract adapter interface decouples internal agent tool calls
    from specific commerce backends (e.g., local mock database, Careem MCP, Shopify, etc.).
    """

    @abstractmethod
    async def search_products(
        self,
        query: Optional[str],
        category: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[Product]:
        pass

    @abstractmethod
    async def get_product(
        self,
        product_id: Union[str, uuid.UUID],
        db: AsyncSession,
    ) -> Optional[Product]:
        pass

    @abstractmethod
    async def get_cart(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        pass

    @abstractmethod
    async def add_to_cart(
        self,
        product_id: Union[str, uuid.UUID],
        quantity: float,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        pass

    @abstractmethod
    async def update_cart_item(
        self,
        cart_item_id: Union[str, uuid.UUID],
        quantity: float,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        pass

    @abstractmethod
    async def remove_from_cart(
        self,
        cart_item_id: Union[str, uuid.UUID],
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        pass

    @abstractmethod
    async def get_checkout_preview(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        pass

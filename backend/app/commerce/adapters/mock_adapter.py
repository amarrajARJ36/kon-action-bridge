import uuid
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.commerce.adapters.base import CommerceAdapter
from app.commerce.catalog_service import catalog_service
from app.commerce.cart_service import cart_service
from app.models.product import Product
from app.schemas.cart import CartResponse


class MockAdapter(CommerceAdapter):
    """
    Default in-database mock adapter providing complete catalog and cart operations
    for local development and evaluation.
    """

    def __init__(self):
        self.catalog = catalog_service
        self.cart = cart_service

    async def search_products(
        self,
        query: Optional[str],
        category: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[Product]:
        return await self.catalog.search_products(query=query, category=category, db=db)

    async def get_product(
        self,
        product_id: Union[str, uuid.UUID],
        db: AsyncSession,
    ) -> Optional[Product]:
        return await self.catalog.get_product_by_id(product_id=product_id, db=db)

    async def get_cart(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart.get_cart(user_id=user_id, session_id=session_id, db=db)

    async def add_to_cart(
        self,
        product_id: Union[str, uuid.UUID],
        quantity: float,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart.add_item(
            user_id=user_id,
            session_id=session_id,
            product_id=product_id,
            quantity=quantity,
            db=db,
        )

    async def update_cart_item(
        self,
        cart_item_id: Union[str, uuid.UUID],
        quantity: float,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart.update_item(
            user_id=user_id,
            session_id=session_id,
            cart_item_id=cart_item_id,
            quantity=quantity,
            db=db,
        )

    async def remove_from_cart(
        self,
        cart_item_id: Union[str, uuid.UUID],
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart.remove_item(
            user_id=user_id,
            session_id=session_id,
            cart_item_id=cart_item_id,
            db=db,
        )

    async def get_checkout_preview(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart.get_checkout_preview(
            user_id=user_id,
            session_id=session_id,
            db=db,
        )


mock_adapter = MockAdapter()

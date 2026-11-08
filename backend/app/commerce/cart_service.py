import uuid
from typing import Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.cart import CartResponse
from app.tools.cart_tools import cart_tools


class CartService:
    """
    Commerce Cart domain service ensuring customer session isolation
    and atomic operations.
    """

    def __init__(self):
        self.cart_tools = cart_tools

    async def get_cart(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart_tools.get_cart(
            user_id=user_id,
            session_id=session_id,
            db=db,
        )

    async def add_item(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        product_id: Union[str, uuid.UUID],
        quantity: float,
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart_tools.add_to_cart(
            product_id=product_id,
            quantity=quantity,
            user_id=user_id,
            session_id=session_id,
            db=db,
        )

    async def update_item(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        cart_item_id: Union[str, uuid.UUID],
        quantity: float,
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart_tools.update_cart_item(
            cart_item_id=cart_item_id,
            quantity=quantity,
            user_id=user_id,
            session_id=session_id,
            db=db,
        )

    async def remove_item(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        cart_item_id: Union[str, uuid.UUID],
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart_tools.remove_from_cart(
            cart_item_id=cart_item_id,
            user_id=user_id,
            session_id=session_id,
            db=db,
        )

    async def clear_cart(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart_tools.clear_cart(
            user_id=user_id,
            session_id=session_id,
            db=db,
        )

    async def get_checkout_preview(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        return await self.cart_tools.get_checkout_preview(
            user_id=user_id,
            session_id=session_id,
            db=db,
        )


cart_service = CartService()

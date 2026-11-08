"""
Careem Model Context Protocol (MCP) Commerce Adapter (Placeholder)

This module provides the structural adapter for future integration with the
Careem SuperApp / Quik Grocery ecosystem via Model Context Protocol (MCP) or
Careem Partner Commerce APIs.

Production Integration Requirements:
-----------------------------------
1. API Credentials & Authentication:
   - CAREEM_CLIENT_ID: OAuth2 Client identifier issued by Careem Partner Portal.
   - CAREEM_CLIENT_SECRET: Secure secret for exchanging partner access tokens.
   - CAREEM_PARTNER_API_KEY: Gateway header token for endpoint authorization.
   - CAREEM_MERCHANT_ID: Target grocery merchant store ID (e.g., Careem Quik Dubai Marina).

2. Network Endpoints:
   - Identity: https://identity.careem.com/oauth/token (Bearer token lifecycle).
   - MCP Server Gateway: https://mcp.careem-partner.com/v1/sse or stdio bridge.
   - Catalog Search API: GET https://api.careem.com/commerce/v2/stores/{merchant_id}/catalog/search
   - Cart & Checkout API: POST https://api.careem.com/commerce/v2/stores/{merchant_id}/cart/items

3. Webhook / Realtime Callbacks:
   - Order status notifications and live driver courier dispatch updates.
"""

import uuid
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.commerce.adapters.base import CommerceAdapter
from app.models.product import Product
from app.schemas.cart import CartResponse


class CareemMCPAdapter(CommerceAdapter):
    """
    Careem MCP Adapter placeholder interface.
    Unconfigured placeholder for future external Careem MCP or partner API expansion.
    Currently raises NotImplementedError on all operations; active catalogue and cart
    services run via the governed internal database catalogue.
    """

    ERROR_MESSAGE = (
        "Careem MCP integration is an unconfigured placeholder. "
        "The application uses the governed database catalogue for all live commerce operations."
    )

    async def search_products(
        self,
        query: Optional[str],
        category: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[Product]:
        raise NotImplementedError(self.ERROR_MESSAGE)

    async def get_product(
        self,
        product_id: Union[str, uuid.UUID],
        db: AsyncSession,
    ) -> Optional[Product]:
        raise NotImplementedError(self.ERROR_MESSAGE)

    async def get_cart(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        raise NotImplementedError(self.ERROR_MESSAGE)

    async def add_to_cart(
        self,
        product_id: Union[str, uuid.UUID],
        quantity: float,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        raise NotImplementedError(self.ERROR_MESSAGE)

    async def update_cart_item(
        self,
        cart_item_id: Union[str, uuid.UUID],
        quantity: float,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        raise NotImplementedError(self.ERROR_MESSAGE)

    async def remove_from_cart(
        self,
        cart_item_id: Union[str, uuid.UUID],
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        raise NotImplementedError(self.ERROR_MESSAGE)

    async def get_checkout_preview(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        raise NotImplementedError(self.ERROR_MESSAGE)


careem_mcp_adapter = CareemMCPAdapter()

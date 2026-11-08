import uuid
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.tools.product_tools import product_tools


class CatalogService:
    """
    Catalog domain service offering high-level product search and retrieval.
    """

    def __init__(self):
        self.product_tools = product_tools

    async def search_products(
        self,
        query: Optional[str],
        category: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        return await self.product_tools.search_products(
            query=query,
            category=category,
            db=db,
            limit=limit,
            offset=offset,
        )

    async def get_product_by_id(
        self,
        product_id: Union[str, uuid.UUID],
        db: AsyncSession,
    ) -> Optional[Product]:
        return await self.product_tools.get_product_details(
            product_id=product_id,
            db=db,
        )


catalog_service = CatalogService()

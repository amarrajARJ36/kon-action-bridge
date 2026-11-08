import uuid
from typing import List, Optional, Union
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductTools:
    """
    Direct catalog inspection tools querying the persistent database.
    """

    async def search_products(
        self,
        query: Optional[str],
        category: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        if db is None:
            raise ValueError("Database session required for catalog search")

        stmt = select(Product)

        if query:
            search_term = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Product.name.ilike(search_term),
                    Product.brand.ilike(search_term),
                    Product.variant.ilike(search_term),
                    Product.category.ilike(search_term),
                    Product.sku.ilike(search_term),
                )
            )

        if category:
            stmt = stmt.where(Product.category.ilike(f"%{category.strip()}%"))

        stmt = stmt.order_by(Product.name).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_product_details(
        self,
        product_id: Union[str, uuid.UUID],
        db: AsyncSession,
    ) -> Optional[Product]:
        if isinstance(product_id, str):
            try:
                pid = uuid.UUID(product_id)
            except ValueError:
                return None
        else:
            pid = product_id

        stmt = select(Product).where(Product.id == pid)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


product_tools = ProductTools()

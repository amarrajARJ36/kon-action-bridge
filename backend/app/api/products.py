import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.product import Product
from app.schemas.product import ProductResponse, ProductSearchResponse

router = APIRouter()


@router.get("", response_model=ProductSearchResponse)
async def list_products(
    q: Optional[str] = Query(None, description="Search keyword query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query_stmt = select(Product)
    count_stmt = select(func.count(Product.id))

    if q:
        search_term = f"%{q.strip()}%"
        filter_clause = or_(
            Product.name.ilike(search_term),
            Product.brand.ilike(search_term),
            Product.variant.ilike(search_term),
            Product.category.ilike(search_term),
            Product.sku.ilike(search_term),
        )
        query_stmt = query_stmt.where(filter_clause)
        count_stmt = count_stmt.where(filter_clause)

    if category:
        cat_filter = Product.category.ilike(f"%{category.strip()}%")
        query_stmt = query_stmt.where(cat_filter)
        count_stmt = count_stmt.where(cat_filter)

    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar_one()

    query_stmt = query_stmt.order_by(Product.name).limit(limit).offset(offset)
    result = await db.execute(query_stmt)
    products = result.scalars().all()

    return ProductSearchResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        total_count=total_count,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Product).where(Product.id == product_id)
    res = await db.execute(stmt)
    product = res.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' was not found",
        )
    return ProductResponse.model_validate(product)

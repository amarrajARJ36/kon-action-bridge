import time
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.schemas.cart import CartItemResponse, CartResponse
from app.schemas.product import ProductResponse
from app.tools.product_tools import product_tools
from app.tools.unit_converter import convert_quantity_to_canonical


class CartTools:
    """
    Core commerce tools managing session-isolated shopping carts,
    server-side price integrity, and stock validation.
    """

    def _format_cart_response(self, cart: Cart, note: Optional[str] = None) -> CartResponse:
        """
        Derives verified item subtotals and grand total AED directly from database records.
        """
        items_response = []
        total_subtotal = Decimal("0.00")

        for item in cart.items:
            unit_price = Decimal(str(item.unit_price_aed))
            quantity = Decimal(str(item.quantity))
            line_subtotal = round(unit_price * quantity, 2)
            total_subtotal += line_subtotal

            prod_resp = None
            if item.product:
                prod_resp = ProductResponse(
                    id=item.product.id,
                    sku=item.product.sku,
                    name=item.product.name,
                    brand=item.product.brand,
                    category=item.product.category,
                    variant=item.product.variant,
                    unit_of_measurement=item.product.unit_of_measurement,
                    price_aed=float(item.product.price_aed),
                    stock_quantity=float(item.product.stock_quantity),
                    is_available=item.product.is_available,
                    image_url=item.product.image_url,
                    created_at=item.product.created_at,
                )

            items_response.append(
                CartItemResponse(
                    id=item.id,
                    cart_id=item.cart_id,
                    product_id=item.product_id,
                    quantity=float(item.quantity),
                    unit_price_aed=float(item.unit_price_aed),
                    subtotal_aed=float(line_subtotal),
                    added_at=item.added_at,
                    product=prod_resp,
                )
            )

        subtotal = round(total_subtotal, 2)
        vat = round(subtotal * Decimal("0.05"), 2)
        grand_total = round(subtotal + vat, 2)

        return CartResponse(
            id=cart.id,
            user_id=cart.user_id,
            session_id=cart.session_id,
            items=items_response,
            subtotal_aed=float(subtotal),
            vat_aed=float(vat),
            grand_total_aed=float(grand_total),
            item_count=len(items_response),
            created_at=cart.created_at,
            updated_at=cart.updated_at,
            note=note,
        )

    async def get_or_create_cart(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> Cart:
        uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id

        stmt = (
            select(Cart)
            .where(Cart.user_id == uid, Cart.session_id == session_id)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .execution_options(populate_existing=True)
        )
        result = await db.execute(stmt)
        cart = result.scalar_one_or_none()

        if not cart:
            cart = Cart(user_id=uid, session_id=session_id)
            db.add(cart)
            await db.commit()
            await db.refresh(cart)

            # Re-fetch with relationships loaded
            stmt = (
                select(Cart)
                .where(Cart.id == cart.id)
                .options(selectinload(Cart.items).selectinload(CartItem.product))
                .execution_options(populate_existing=True)
            )
            result = await db.execute(stmt)
            cart = result.scalar_one()

        return cart

    async def add_to_cart(
        self,
        product_id: Union[str, uuid.UUID],
        quantity: float,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
        unit: Optional[str] = None,
    ) -> CartResponse:
        pid = uuid.UUID(str(product_id)) if not isinstance(product_id, uuid.UUID) else product_id

        # Quantity validation
        if quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}. Must be greater than 0.")

        # 1. Fetch product and validate availability & stock
        prod_stmt = select(Product).where(Product.id == pid)
        prod_res = await db.execute(prod_stmt)
        product = prod_res.scalar_one_or_none()

        if not product:
            raise ValueError(f"Product with ID '{product_id}' not found in catalog.")

        if not product.is_available:
            raise ValueError(f"Product '{product.name}' is currently unavailable for order.")

        # Convert quantity using canonical unit model
        canonical_qty = convert_quantity_to_canonical(
            quantity=quantity,
            user_unit=unit,
            canonical_unit=product.unit_of_measurement,
            product_name=product.name,
        )

        if canonical_qty > 100:
            raise ValueError(f"Quantity exceeds single order limit (maximum 100 units).")

        if product.stock_quantity < canonical_qty:
            raise ValueError(
                f"Insufficient inventory for '{product.name}'. "
                f"Requested: {canonical_qty} {product.unit_of_measurement}, Available stock: {product.stock_quantity}"
            )

        # 2. Retrieve or initialize user cart
        cart = await self.get_or_create_cart(user_id, session_id, db)

        # 3. Check if line item already exists
        existing_item = next((item for item in cart.items if item.product_id == pid), None)
        if existing_item:
            new_qty = existing_item.quantity + canonical_qty
            if product.stock_quantity < new_qty:
                raise ValueError(
                    f"Adding {canonical_qty} {product.unit_of_measurement} exceeds available stock of {product.stock_quantity} "
                    f"(current in basket: {existing_item.quantity})."
                )
            existing_item.quantity = new_qty
            # Always ensure server-verified price from catalog is set
            existing_item.unit_price_aed = product.price_aed
        else:
            new_item = CartItem(
                cart_id=cart.id,
                product_id=product.id,
                quantity=canonical_qty,
                unit_price_aed=product.price_aed,  # Strict DB price assignment
            )
            db.add(new_item)

        await db.commit()

        # Reload updated cart with relations
        stmt = (
            select(Cart)
            .where(Cart.id == cart.id)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .execution_options(populate_existing=True)
        )
        res = await db.execute(stmt)
        updated_cart = res.scalar_one()

        return self._format_cart_response(updated_cart)

    async def add_batch_to_cart(
        self,
        items: list,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        """
        Atomically validates and adds multiple products in one single database transaction.
        Pre-validates product existence, unit conversions, and stock availability for ALL items.
        If any validation or stock check fails, the transaction is rolled back with 0 items committed.
        """
        if not items:
            cart = await self.get_or_create_cart(user_id, session_id, db)
            return self._format_cart_response(cart)

        # Phase 1: Pre-validation and canonical conversion of ALL items
        validated_items = []
        for it in items:
            raw_pid = it.get("product_id")
            if not raw_pid:
                raise ValueError("Each item must specify a valid product_id")
            try:
                pid = uuid.UUID(str(raw_pid))
            except (ValueError, TypeError):
                raise ValueError(f"Invalid UUID for product: {raw_pid}")

            raw_qty = float(it.get("quantity", 1.0))
            if raw_qty <= 0:
                raise ValueError(f"Quantity must be greater than 0, got {raw_qty}")

            unit = it.get("unit")

            # Fetch product from DB
            prod_stmt = select(Product).where(Product.id == pid)
            prod_res = await db.execute(prod_stmt)
            product = prod_res.scalar_one_or_none()

            if not product:
                raise ValueError(f"Product '{raw_pid}' not found in catalog.")
            if not product.is_available:
                raise ValueError(f"Product '{product.name}' is currently unavailable.")

            canonical_qty = convert_quantity_to_canonical(
                quantity=raw_qty,
                user_unit=unit,
                canonical_unit=product.unit_of_measurement,
                product_name=product.name,
            )

            if canonical_qty > 100:
                raise ValueError(f"Quantity for '{product.name}' exceeds single order limit (max 100).")

            validated_items.append({
                "product": product,
                "canonical_qty": canonical_qty,
            })

        # Phase 2: Retrieve cart and verify combined inventory
        cart = await self.get_or_create_cart(user_id, session_id, db)

        for v in validated_items:
            product = v["product"]
            canonical_qty = v["canonical_qty"]
            existing = next((ci for ci in cart.items if ci.product_id == product.id), None)
            current_qty = existing.quantity if existing else 0.0
            if product.stock_quantity < (current_qty + canonical_qty):
                raise ValueError(
                    f"Insufficient stock for '{product.name}'. "
                    f"Requested: {canonical_qty} {product.unit_of_measurement}, "
                    f"In cart: {current_qty}, Available: {product.stock_quantity}"
                )

        # Phase 3: Apply additions atomically in one transaction
        for v in validated_items:
            product = v["product"]
            canonical_qty = v["canonical_qty"]
            existing = next((ci for ci in cart.items if ci.product_id == product.id), None)
            if existing:
                existing.quantity += canonical_qty
                existing.unit_price_aed = product.price_aed
            else:
                new_item = CartItem(
                    cart_id=cart.id,
                    product_id=product.id,
                    quantity=canonical_qty,
                    unit_price_aed=product.price_aed,
                )
                db.add(new_item)

        await db.commit()

        # Reload updated cart with relations
        stmt = (
            select(Cart)
            .where(Cart.id == cart.id)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .execution_options(populate_existing=True)
        )
        res = await db.execute(stmt)
        refreshed = res.scalar_one()
        return self._format_cart_response(refreshed)

    async def update_cart_item(
        self,
        cart_item_id: Union[str, uuid.UUID],
        quantity: float,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        cid = uuid.UUID(str(cart_item_id)) if not isinstance(cart_item_id, uuid.UUID) else cart_item_id
        uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id

        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0. Use remove_from_cart to delete.")
        if quantity > 100:
            raise ValueError("Quantity cannot exceed 100 units.")

        stmt = (
            select(CartItem)
            .join(Cart)
            .where(CartItem.id == cid, Cart.user_id == uid)
            .options(selectinload(CartItem.product))
        )
        res = await db.execute(stmt)
        item = res.scalar_one_or_none()

        if not item:
            raise ValueError(f"Cart item '{cart_item_id}' not found or access denied.")

        if item.product and item.product.stock_quantity < quantity:
            raise ValueError(
                f"Requested quantity {quantity} exceeds available stock of {item.product.stock_quantity}."
            )

        item.quantity = quantity
        await db.commit()

        cart = await self.get_or_create_cart(uid, session_id, db)
        return self._format_cart_response(cart)

    async def remove_from_cart(
        self,
        cart_item_id: Union[str, uuid.UUID],
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        cid = uuid.UUID(str(cart_item_id)) if not isinstance(cart_item_id, uuid.UUID) else cart_item_id
        uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id

        stmt = select(CartItem).join(Cart).where(CartItem.id == cid, Cart.user_id == uid)
        res = await db.execute(stmt)
        item = res.scalar_one_or_none()

        if not item:
            raise ValueError(f"Cart item '{cart_item_id}' not found or unauthorized.")

        await db.delete(item)
        await db.commit()

        cart = await self.get_or_create_cart(uid, session_id, db)
        return self._format_cart_response(cart)

    async def clear_cart(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        cart = await self.get_or_create_cart(user_id, session_id, db)
        for item in cart.items:
            await db.delete(item)
        await db.commit()

        refreshed = await self.get_or_create_cart(user_id, session_id, db)
        return self._format_cart_response(refreshed)

    async def get_cart(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        cart = await self.get_or_create_cart(user_id, session_id, db)
        return self._format_cart_response(cart)

    async def get_checkout_preview(
        self,
        user_id: Union[str, uuid.UUID],
        session_id: str,
        db: AsyncSession,
    ) -> CartResponse:
        cart = await self.get_or_create_cart(user_id, session_id, db)
        note = (
            "NON-BINDING CHECKOUT PREVIEW: No payment has been processed and no order placed. "
            "Explicit customer confirmation is required to finalize order fulfillment."
        )
        return self._format_cart_response(cart, note=note)


cart_tools = CartTools()


class ToolExecutor:
    """
    Central dispatcher executing validated tools with error isolation.
    """

    def __init__(self):
        self.product_tools = product_tools
        self.cart_tools = cart_tools

    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        db: AsyncSession,
    ) -> Any:
        params = params or {}
        from app.governance.tool_schemas import validate_tool_input
        # Strictly validate input schema before execution
        validate_tool_input(tool_name, params)

        if tool_name == "search_products":
            query = params.get("query")
            category = params.get("category")
            return await self.product_tools.search_products(query=query, category=category, db=db)

        elif tool_name == "get_product_details":
            product_id = params.get("product_id")
            if not product_id:
                raise ValueError("Parameter 'product_id' is required")
            return await self.product_tools.get_product_details(product_id=product_id, db=db)

        elif tool_name == "add_to_cart":
            user_id = params.get("user_id")
            session_id = params.get("session_id")
            if not user_id or not session_id:
                raise ValueError("User ID and Session ID context are required for add_to_cart")

            items = params.get("items")
            if items and isinstance(items, list) and len(items) > 1:
                return await self.cart_tools.add_batch_to_cart(
                    items=items,
                    user_id=user_id,
                    session_id=session_id,
                    db=db,
                )

            product_id = params.get("product_id")
            quantity = float(params.get("quantity", 1.0))
            unit = params.get("unit")
            return await self.cart_tools.add_to_cart(
                product_id=product_id,
                quantity=quantity,
                unit=unit,
                user_id=user_id,
                session_id=session_id,
                db=db,
            )

        elif tool_name == "update_cart_item":
            cart_item_id = params.get("cart_item_id")
            quantity = float(params.get("quantity", 1.0))
            user_id = params.get("user_id")
            session_id = params.get("session_id")
            return await self.cart_tools.update_cart_item(
                cart_item_id=cart_item_id,
                quantity=quantity,
                user_id=user_id,
                session_id=session_id,
                db=db,
            )

        elif tool_name == "remove_from_cart":
            cart_item_id = params.get("cart_item_id")
            user_id = params.get("user_id")
            session_id = params.get("session_id")
            return await self.cart_tools.remove_from_cart(
                cart_item_id=cart_item_id,
                user_id=user_id,
                session_id=session_id,
                db=db,
            )

        elif tool_name == "get_cart":
            user_id = params.get("user_id")
            session_id = params.get("session_id")
            return await self.cart_tools.get_cart(user_id=user_id, session_id=session_id, db=db)

        elif tool_name == "get_checkout_preview":
            user_id = params.get("user_id")
            session_id = params.get("session_id")
            return await self.cart_tools.get_checkout_preview(
                user_id=user_id, session_id=session_id, db=db
            )

        elif tool_name == "submit_order":
            user_id = params.get("user_id")
            session_id = params.get("session_id")
            preview = await self.cart_tools.get_checkout_preview(
                user_id=user_id, session_id=session_id, db=db
            )
            return {
                "order_id": f"ORD-{uuid.uuid4().hex[:8].upper()}",
                "status": "submitted",
                "delivery_address": params.get("delivery_address", "Downtown Dubai, UAE"),
                "summary": preview,
                "note": "Simulated order execution under governance supervisor approval",
            }

        else:
            raise ValueError(f"Unknown or unsupported tool '{tool_name}'")


tool_executor = ToolExecutor()

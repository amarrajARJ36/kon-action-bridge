import time
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.observability.audit_logger import audit_logger
from app.observability.tracing import get_current_trace_id
from app.schemas.cart import (
    AddToCartRequest,
    CartResponse,
    UpdateCartItemRequest,
)
from app.tools.cart_tools import cart_tools

router = APIRouter()


def _resolve_session_id(
    current_user: User,
    session_id_query: Optional[str] = None,
    session_id_body: Optional[str] = None,
    x_session_id: Optional[str] = None,
) -> str:
    if session_id_query and session_id_query.strip():
        return session_id_query.strip()
    if session_id_body and session_id_body.strip():
        return session_id_body.strip()
    if x_session_id and x_session_id.strip():
        return x_session_id.strip()
    token_session = getattr(current_user, "current_session_id", None)
    if token_session:
        return str(token_session)
    return str(current_user.id)


@router.get("", response_model=CartResponse)
async def get_user_cart(
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active_session = _resolve_session_id(current_user, session_id_query=session_id, x_session_id=x_session_id)
    return await cart_tools.get_cart(
        user_id=current_user.id,
        session_id=active_session,
        db=db,
    )


@router.post("/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    request: AddToCartRequest,
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active_session = _resolve_session_id(
        current_user,
        session_id_query=session_id,
        session_id_body=request.session_id,
        x_session_id=x_session_id,
    )
    trace_id = get_current_trace_id()
    start_time = time.perf_counter()
    try:
        updated_cart = await cart_tools.add_to_cart(
            product_id=request.product_id,
            quantity=request.quantity,
            user_id=current_user.id,
            session_id=active_session,
            db=db,
            unit=request.unit,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Record customer manual action to audit trail
        await audit_logger.log(
            db=db,
            agent_id=None,
            user_id=str(current_user.id),
            session_id=active_session,
            tool_name="add_to_cart",
            action="customer_direct:add_to_cart",
            target_resource=str(request.product_id),
            governance_decision="allowed",
            execution_status="success",
            denial_reason=None,
            execution_duration_ms=round(duration_ms, 2),
            metadata={"product_id": str(request.product_id), "quantity": request.quantity, "unit": request.unit, "actor": "customer"},
            trace_id=trace_id,
        )
        return updated_cart
    except ValueError as err:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        await audit_logger.log(
            db=db,
            agent_id=None,
            user_id=str(current_user.id),
            session_id=active_session,
            tool_name="add_to_cart",
            action="customer_direct:add_to_cart",
            target_resource=str(request.product_id),
            governance_decision="allowed",
            execution_status="failed",
            denial_reason=str(err),
            execution_duration_ms=round(duration_ms, 2),
            metadata={"product_id": str(request.product_id), "quantity": request.quantity, "actor": "customer"},
            trace_id=trace_id,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.put("/items/{cart_item_id}", response_model=CartResponse)
async def update_cart_item(
    cart_item_id: uuid.UUID,
    request: UpdateCartItemRequest,
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active_session = _resolve_session_id(current_user, session_id, x_session_id)
    trace_id = get_current_trace_id()
    start_time = time.perf_counter()
    try:
        updated_cart = await cart_tools.update_cart_item(
            cart_item_id=cart_item_id,
            quantity=request.quantity,
            user_id=current_user.id,
            session_id=active_session,
            db=db,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        await audit_logger.log(
            db=db,
            agent_id=None,
            user_id=str(current_user.id),
            session_id=active_session,
            tool_name="update_cart_item",
            action="customer_direct:update_cart_item",
            target_resource=str(cart_item_id),
            governance_decision="allowed",
            execution_status="success",
            execution_duration_ms=round(duration_ms, 2),
            metadata={"cart_item_id": str(cart_item_id), "quantity": request.quantity, "actor": "customer"},
            trace_id=trace_id,
        )
        return updated_cart
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.delete("/items/{cart_item_id}", response_model=CartResponse)
async def remove_cart_item(
    cart_item_id: uuid.UUID,
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active_session = _resolve_session_id(current_user, session_id, x_session_id)
    trace_id = get_current_trace_id()
    start_time = time.perf_counter()
    try:
        updated_cart = await cart_tools.remove_from_cart(
            cart_item_id=cart_item_id,
            user_id=current_user.id,
            session_id=active_session,
            db=db,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        await audit_logger.log(
            db=db,
            agent_id=None,
            user_id=str(current_user.id),
            session_id=active_session,
            tool_name="remove_from_cart",
            action="customer_direct:remove_cart_item",
            target_resource=str(cart_item_id),
            governance_decision="allowed",
            execution_status="success",
            execution_duration_ms=round(duration_ms, 2),
            metadata={"cart_item_id": str(cart_item_id), "actor": "customer"},
            trace_id=trace_id,
        )
        return updated_cart
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.delete("", response_model=CartResponse)
async def clear_cart(
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active_session = _resolve_session_id(current_user, session_id, x_session_id)
    return await cart_tools.clear_cart(
        user_id=current_user.id,
        session_id=active_session,
        db=db,
    )


@router.get("/checkout-preview", response_model=CartResponse)
async def get_checkout_preview(
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active_session = _resolve_session_id(current_user, session_id, x_session_id)
    return await cart_tools.get_checkout_preview(
        user_id=current_user.id,
        session_id=active_session,
        db=db,
    )

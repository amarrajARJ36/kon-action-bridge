import time
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.conversation import conversation_engine
from app.agents.tts import generate_neural_audio
from app.api.auth import get_current_user
from app.database import get_db
from app.governance.policy_engine import policy_engine
from app.models.user import User
from app.observability.audit_logger import audit_logger
from app.observability.tracing import get_current_trace_id
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.tools.cart_tools import tool_executor

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-AvaMultilingualNeural"


class TTSResponse(BaseModel):
    audio_base64: Optional[str] = None


class ConfirmSelectionRequest(BaseModel):
    product_id: uuid.UUID
    quantity: float = Field(default=1.0, gt=0, le=100)
    session_id: str
    unit: Optional[str] = None


@router.post("/tts", response_model=TTSResponse)
async def get_speech_audio(
    request: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generates realistic neural voice audio (Gemini Live style).
    Protected by user authentication and character quota limits.
    """
    if not request.text or not request.text.strip():
        return TTSResponse(audio_base64=None)

    if len(request.text) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TTS text exceeds maximum length of 1,000 characters",
        )

    audio_b64 = await generate_neural_audio(
        request.text,
        voice=request.voice or "en-US-AvaMultilingualNeural",
    )
    return TTSResponse(audio_base64=audio_b64)


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Primary conversational endpoint. Passes customer utterance through
    governed AI pipeline, evaluates security policy, executes tools,
    and returns assistant response.
    """
    response = await conversation_engine.process_message(
        message=request.message,
        session_id=request.session_id,
        user_id=str(current_user.id),
        db=db,
    )
    return response


@router.post("/confirm-product-selection", response_model=ChatResponse)
async def confirm_product_selection(
    request: ConfirmSelectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Governed endpoint for customer confirmation of an assistant-suggested product.
    Routes the selection through PolicyEngine and records it in AuditLog under the
    AI agent's identity ('kon-shopping-agent').
    """
    trace_id = get_current_trace_id()
    agent_id = "kon-shopping-agent"
    tool_params = {
        "product_id": str(request.product_id),
        "quantity": request.quantity,
        "unit": request.unit,
        "user_id": str(current_user.id),
        "session_id": request.session_id,
    }

    # 1. Policy check
    policy_decision = await policy_engine.check(
        agent_id=agent_id,
        tool_name="add_to_cart",
        params=tool_params,
        session_context={
            "user_id": str(current_user.id),
            "session_id": request.session_id,
            "trace_id": trace_id,
        },
        db=db,
    )

    if not policy_decision.allowed:
        await audit_logger.log(
            db=db,
            agent_id=agent_id,
            user_id=str(current_user.id),
            session_id=request.session_id,
            tool_name="add_to_cart",
            action="assistant_confirmed_selection",
            target_resource=str(request.product_id),
            governance_decision="denied",
            execution_status="failed",
            denial_reason=policy_decision.reason,
            execution_duration_ms=0.0,
            metadata=tool_params,
            trace_id=trace_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action declined by governance security policy: {policy_decision.reason}",
        )

    # 2. Tool execution
    start_time = time.perf_counter()
    try:
        updated_cart = await tool_executor.execute(
            tool_name="add_to_cart",
            params=tool_params,
            db=db,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # 3. Audit log under agent_id
        await audit_logger.log(
            db=db,
            agent_id=agent_id,
            user_id=str(current_user.id),
            session_id=request.session_id,
            tool_name="add_to_cart",
            action="assistant_confirmed_selection",
            target_resource=str(request.product_id),
            governance_decision="allowed",
            execution_status="success",
            denial_reason=None,
            execution_duration_ms=round(duration_ms, 2),
            metadata=tool_params,
            trace_id=trace_id,
        )

        return ChatResponse(
            message=f"Added {request.quantity} of selected product to your basket.",
            action_taken="add_to_cart",
            basket_updated=True,
            cart=updated_cart,
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        await audit_logger.log(
            db=db,
            agent_id=agent_id,
            user_id=str(current_user.id),
            session_id=request.session_id,
            tool_name="add_to_cart",
            action="assistant_confirmed_selection",
            target_resource=str(request.product_id),
            governance_decision="allowed",
            execution_status="failed",
            denial_reason=str(exc),
            execution_duration_ms=round(duration_ms, 2),
            metadata=tool_params,
            trace_id=trace_id,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/history/{session_id}", response_model=List[ChatMessage])
async def get_chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves previous conversation message history for session.
    Returns empty list for MVP baseline.
    """
    return []

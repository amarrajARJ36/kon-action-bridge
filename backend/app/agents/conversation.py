import asyncio
import logging
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_provider import FallbackProvider, GeminiProvider, LLMProvider
from app.agents.tts import generate_neural_audio
from app.config import settings
from app.governance.permissions import AgentPermissions
from app.governance.policy_engine import policy_engine
from app.observability.audit_logger import audit_logger
from app.observability.evaluator import conversation_evaluator
from app.observability.tracing import get_current_trace_id, persist_trace_spans, trace_span
from app.schemas.chat import ChatResponse
from app.schemas.product import ProductResponse
from app.tools.cart_tools import tool_executor
from app.tools.registry import tool_registry_service

logger = logging.getLogger(__name__)


def _make_serializable(obj: Any) -> Any:
    """
    Recursively converts Pydantic models, SQLAlchemy objects, UUIDs, Decimals
    into JSON-serializable primitives for tool responses.
    """
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return _make_serializable(obj.model_dump())
    if isinstance(obj, list):
        return [_make_serializable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if hasattr(obj, "__table__"):
        return {c.name: _make_serializable(getattr(obj, c.name)) for c in obj.__table__.columns}
    return obj


class ConversationEngine:
    """
    Central orchestration engine for AI shopping dialogues.
    Coordinates between Gemini native function-calling reasoning,
    manual fail-closed policy checks, governed tool execution,
    persistent audit logging, and semantic conversation quality evaluation.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        if provider:
            self.provider = provider
        elif settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
            self.provider = GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model_name=settings.GEMINI_MODEL,
            )
        else:
            self.provider = FallbackProvider()

    def _extract_intent_items(self, session_id: str) -> Dict[str, Any]:
        """
        Read the per-turn intent classification stored by FallbackProvider
        (or GeminiProvider which wraps it) for use in the evaluator.
        """
        fb = self.provider.fallback if hasattr(self.provider, "fallback") else self.provider
        if not hasattr(fb, "sessions"):
            return {"requested": [], "unavailable": [], "ambiguous": [], "added": []}
        sess = fb.sessions.get(session_id, {})
        return {
            "requested": sess.get("last_items_requested", []),
            "unavailable": sess.get("last_items_unavailable", []),
            "ambiguous": sess.get("last_items_ambiguous", []),
            "added": sess.get("last_items_to_add", []),
        }

    async def _process_with_gemini_native_loop(
        self,
        message: str,
        session_id: str,
        user_id: str,
        agent_id: str,
        trace_id: uuid.UUID,
        db: AsyncSession,
    ) -> Optional[ChatResponse]:
        """
        Executes bounded, manual tool-calling loop using Google Gemini native function calling.
        Gemini proposes tools; backend governance authorizes and executes manually before returning results.
        """
        if not isinstance(self.provider, GeminiProvider) or not self.provider.is_available():
            return None

        from google.genai import types

        allowed_tools = AgentPermissions.ALLOWED_TOOLS_SHOPPING_AGENT
        decls = tool_registry_service.get_gemini_tool_declarations(allowed_tools)

        config = types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=decls)] if decls else None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            system_instruction=(
                "You are the official KON AI Grocery Shopping Assistant in Dubai. "
                "Your role is to understand customer grocery needs and autonomously select permitted commerce tools "
                "(search_products, get_product_details, add_to_cart, update_cart_item, remove_from_cart, "
                "get_cart, get_checkout_preview, submit_order). "
                "Speak concisely, warmly, and helpfully in 1-2 natural sentences. Do not invent product IDs or fake tools. "
                "Always query or manipulate the store catalog using the available tools."
            ),
        )

        contents: List[Any] = [types.Content(role="user", parts=[types.Part.from_text(text=message)])]
        final_text = ""
        action_taken = None
        basket_updated = False
        last_cart = None
        products_to_select: List[ProductResponse] = []
        total_calls_count = 0
        stop_loop = False

        MAX_TOOL_ROUNDS = 4
        MAX_TOTAL_TOOL_CALLS = 8

        for round_idx in range(MAX_TOOL_ROUNDS):
            with trace_span(
                "ai_inference",
                attributes={
                    "round": round_idx,
                    "provider": "GeminiProvider",
                    "model": self.provider.model_name,
                },
            ):
                model_res = await asyncio.wait_for(
                    self.provider._client.aio.models.generate_content(
                        model=self.provider.model_name,
                        contents=contents,
                        config=config,
                    ),
                    timeout=7.0,
                )

            func_calls = model_res.function_calls or []
            if not func_calls:
                final_text = model_res.text or "Here is your grocery assistance."
                break

            # Append model turn containing proposed function calls
            contents.append(model_res.candidates[0].content)
            response_parts = []

            for call in func_calls:
                total_calls_count += 1
                call_tool_name = call.name
                call_args = dict(call.args or {})
                action_taken = call_tool_name

                # Check max total tool calls safeguard
                if total_calls_count > MAX_TOTAL_TOOL_CALLS:
                    response_parts.append(
                        types.Part.from_function_response(
                            name=call_tool_name,
                            response={"status": "DENIED", "reason": "Maximum tool call limit exceeded per request"},
                        )
                    )
                    stop_loop = True
                    continue

                # 1. Tool registry existence check
                if call_tool_name not in allowed_tools:
                    with trace_span("audit_persistence", attributes={"denied": True}):
                        await audit_logger.log(
                            db=db,
                            agent_id=agent_id,
                            user_id=user_id,
                            session_id=session_id,
                            tool_name=call_tool_name,
                            action=f"tool_call:{call_tool_name}",
                            target_resource=call_tool_name,
                            governance_decision="denied",
                            execution_status="failed",
                            denial_reason=f"Tool '{call_tool_name}' is not in the permitted tool list for {agent_id}",
                            execution_duration_ms=0.0,
                            metadata=call_args,
                            trace_id=trace_id,
                        )
                    response_parts.append(
                        types.Part.from_function_response(
                            name=call_tool_name,
                            response={"status": "DENIED", "reason": f"Tool '{call_tool_name}' is unauthorized for agent."},
                        )
                    )
                    stop_loop = True
                    continue

                # 2. Policy evaluation (fail-closed)
                with trace_span("policy_evaluation", attributes={"tool_name": call_tool_name, "args": str(call_args)}):
                    policy_decision = await policy_engine.check(
                        agent_id=agent_id,
                        tool_name=call_tool_name,
                        params=call_args,
                        session_context={
                            "user_id": user_id,
                            "session_id": session_id,
                            "trace_id": trace_id,
                        },
                        db=db,
                    )

                # 3. Check Human-in-the-Loop (HITL) approval requirement
                if getattr(policy_decision, "requires_approval", False):
                    from app.models.governance import ApprovalRequest
                    from app.observability.event_stream import event_stream_broker

                    approval_req = ApprovalRequest(
                        trace_id=trace_id,
                        agent_id=agent_id,
                        user_id=user_id,
                        session_id=session_id,
                        tool_name=call_tool_name,
                        action=f"order:{call_tool_name}",
                        parameters=call_args,
                        status="pending",
                        risk_level="HIGH",
                        reason=policy_decision.reason,
                    )
                    db.add(approval_req)
                    await db.commit()
                    await db.refresh(approval_req)

                    event_stream_broker.publish(
                        "approval_request",
                        {
                            "id": str(approval_req.id),
                            "trace_id": str(trace_id),
                            "agent_id": agent_id,
                            "tool_name": call_tool_name,
                            "status": "pending",
                            "risk_level": "HIGH",
                        },
                    )

                    with trace_span("audit_persistence", attributes={"approval_required": True}):
                        await audit_logger.log(
                            db=db,
                            agent_id=agent_id,
                            user_id=user_id,
                            session_id=session_id,
                            tool_name=call_tool_name,
                            action=f"tool_call:{call_tool_name}",
                            target_resource=call_tool_name,
                            governance_decision="requires_approval",
                            execution_status="pending",
                            denial_reason=policy_decision.reason,
                            execution_duration_ms=0.0,
                            metadata=call_args,
                            trace_id=trace_id,
                        )

                    response_parts.append(
                        types.Part.from_function_response(
                            name=call_tool_name,
                            response={
                                "status": "REQUIRES_APPROVAL",
                                "message": f"Order submission intercepted: Human-in-the-Loop supervisor approval is required before execution. (Approval ID: {str(approval_req.id)[:8]}...).",
                                "approval_id": str(approval_req.id),
                            },
                        )
                    )
                    stop_loop = True
                    continue

                # 4. Check policy denial
                if not policy_decision.allowed:
                    with trace_span("audit_persistence", attributes={"denied": True}):
                        await audit_logger.log(
                            db=db,
                            agent_id=agent_id,
                            user_id=user_id,
                            session_id=session_id,
                            tool_name=call_tool_name,
                            action=f"tool_call:{call_tool_name}",
                            target_resource=call_tool_name,
                            governance_decision="denied",
                            execution_status="failed",
                            denial_reason=policy_decision.reason,
                            execution_duration_ms=0.0,
                            metadata=call_args,
                            trace_id=trace_id,
                        )
                    response_parts.append(
                        types.Part.from_function_response(
                            name=call_tool_name,
                            response={
                                "status": "DENIED",
                                "reason": f"Declined by governance security policy: {policy_decision.reason}",
                            },
                        )
                    )
                    stop_loop = True
                    continue

                # 5. Policy Allowed: Execute tool manually
                call_args["user_id"] = user_id
                call_args["session_id"] = session_id

                t0 = time.perf_counter()
                with trace_span("tool_execution", attributes={"tool_name": call_tool_name}):
                    tool_result = await tool_executor.execute(
                        tool_name=call_tool_name,
                        params=call_args,
                        db=db,
                    )
                # Accurately compute execution duration after context manager exits
                duration_ms = round((time.perf_counter() - t0) * 1000, 2)

                if call_tool_name in ("add_to_cart", "update_cart_item", "remove_from_cart"):
                    basket_updated = True
                    last_cart = tool_result
                elif call_tool_name in ("get_cart", "get_checkout_preview"):
                    last_cart = tool_result
                elif call_tool_name == "search_products" and isinstance(tool_result, list):
                    products_to_select = [ProductResponse.model_validate(p) for p in tool_result]

                with trace_span("audit_persistence", attributes={"status": "success"}):
                    await audit_logger.log(
                        db=db,
                        agent_id=agent_id,
                        user_id=user_id,
                        session_id=session_id,
                        tool_name=call_tool_name,
                        action=f"tool_call:{call_tool_name}",
                        target_resource=call_tool_name,
                        governance_decision="allowed",
                        execution_status="success",
                        denial_reason=None,
                        execution_duration_ms=duration_ms,
                        metadata=call_args,
                        trace_id=trace_id,
                    )

                response_parts.append(
                    types.Part.from_function_response(
                        name=call_tool_name,
                        response={"status": "SUCCESS", "result": _make_serializable(tool_result)},
                    )
                )

            contents.append(types.Content(role="user", parts=response_parts))

            if stop_loop:
                try:
                    synth_resp = await asyncio.wait_for(
                        self.provider._client.aio.models.generate_content(
                            model=self.provider.model_name,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                system_instruction=(
                                    "Explain the outcome to the customer in 1-2 clear, helpful sentences. "
                                    "State clearly if an action was declined by policy or if supervisor authorization is pending."
                                )
                            ),
                        ),
                        timeout=5.0,
                    )
                    final_text = synth_resp.text or ""
                except Exception:
                    final_text = "Your request was processed according to store governance policy."
                break

        # Assemble final ChatResponse
        chat_resp = ChatResponse(
            message=final_text or "Your request has been processed.",
            action_taken=action_taken,
            products_to_select=products_to_select,
            basket_updated=basket_updated,
            cart=last_cart,
        )

        # Stage 6: Avatar Response
        with trace_span("avatar_response", attributes={"text_length": len(chat_resp.message)}):
            try:
                chat_resp.audio_base64 = await generate_neural_audio(chat_resp.message)
            except Exception:
                pass

        return chat_resp

    async def process_message(
        self,
        message: str,
        session_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> ChatResponse:
        trace_id = get_current_trace_id()
        agent_id = "kon-shopping-agent"
        chat_resp: Optional[ChatResponse] = None

        try:
            # Root Span: Captures entire request lifecycle
            with trace_span(
                "agent.chat_turn",
                attributes={
                    "message": message,
                    "session_id": session_id,
                    "user_id": user_id,
                    "agent_id": agent_id,
                },
            ):
                # Stage 1: Request Received & Input Preprocessing
                with trace_span(
                    "request_received",
                    attributes={"message_length": len(message), "session_id": session_id},
                ):
                    pass

                # Try Gemini Native Tool-Calling Loop first if GeminiProvider is active
                if isinstance(self.provider, GeminiProvider) and self.provider.is_available():
                    try:
                        gemini_result = await self._process_with_gemini_native_loop(
                            message=message,
                            session_id=session_id,
                            user_id=user_id,
                            agent_id=agent_id,
                            trace_id=trace_id,
                            db=db,
                        )
                        if gemini_result is not None:
                            return gemini_result
                    except Exception as loop_err:
                        logger.warning(
                            f"Gemini native tool-calling loop encountered error, falling back to deterministic engine: {loop_err}"
                        )

                # Fallback / Deterministic Engine Path
                # Stage 2: AI Inference
                with trace_span(
                    "ai_inference",
                    attributes={"provider": self.provider.__class__.__name__},
                ):
                    llm_response = await self.provider.generate_response(
                        message=message,
                        session_id=session_id,
                    )

                # If no tool requested, handle conversational reply directly
                if not llm_response.tool_name:
                    chat_resp = ChatResponse(
                        message=llm_response.text_response,
                        action_taken=None,
                        basket_updated=False,
                    )

                    with trace_span(
                        "avatar_response",
                        attributes={"text_length": len(chat_resp.message)},
                    ):
                        try:
                            chat_resp.audio_base64 = await generate_neural_audio(chat_resp.message)
                        except Exception:
                            pass

                    with trace_span("audit_persistence", attributes={"action": "agent_conversation:reply"}):
                        try:
                            await audit_logger.log(
                                db=db,
                                agent_id=agent_id,
                                user_id=user_id,
                                session_id=session_id,
                                tool_name=None,
                                action="agent_conversation:reply",
                                target_resource="conversational_chat",
                                governance_decision="allowed",
                                execution_status="success",
                                denial_reason=None,
                                execution_duration_ms=0.0,
                                metadata={"user_message": message, "agent_response": chat_resp.message, "has_tool": False},
                                trace_id=trace_id,
                            )
                        except Exception:
                            pass

                    intent = self._extract_intent_items(session_id)
                    try:
                        await conversation_evaluator.evaluate(
                            db=db,
                            session_id=session_id,
                            user_id=user_id,
                            trace_id=trace_id,
                            user_message=message,
                            agent_response=chat_resp.message,
                            tool_name_called=None,
                            tool_params={},
                            items_requested=intent["requested"],
                            items_unavailable=intent["unavailable"],
                            items_ambiguous=intent["ambiguous"],
                            items_added=[],
                            basket_updated=False,
                        )
                    except Exception:
                        pass

                    return chat_resp

                tool_name = llm_response.tool_name
                tool_params = dict(llm_response.tool_params)

                is_multi_item = (
                    tool_name == "add_to_cart"
                    and "items" in tool_params
                    and isinstance(tool_params["items"], list)
                    and len(tool_params["items"]) > 1
                )

                # Stage 3: Policy Validation (fail-closed)
                with trace_span(
                    "policy_evaluation",
                    attributes={"tool_name": tool_name, "is_multi_item": is_multi_item},
                ) as policy_span:
                    if is_multi_item:
                        for sub_item in tool_params["items"]:
                            child_params = {
                                "product_id": str(sub_item["product_id"]),
                                "quantity": float(sub_item.get("quantity", 1.0)),
                                "unit": sub_item.get("unit"),
                            }
                            child_decision = await policy_engine.check(
                                agent_id=agent_id,
                                tool_name="add_to_cart",
                                params=child_params,
                                session_context={
                                    "user_id": user_id,
                                    "session_id": session_id,
                                    "trace_id": trace_id,
                                },
                                db=db,
                            )
                            if not child_decision.allowed:
                                policy_span.status = "error"
                                policy_span.attributes["denial_reason"] = child_decision.reason
                                with trace_span("audit_persistence", attributes={"denied": True}):
                                    await audit_logger.log(
                                        db=db,
                                        agent_id=agent_id,
                                        user_id=user_id,
                                        session_id=session_id,
                                        tool_name="add_to_cart",
                                        action="tool_call:add_to_cart:item",
                                        target_resource=str(sub_item["product_id"]),
                                        governance_decision="denied",
                                        execution_status="failed",
                                        denial_reason=f"Multi-item batch rejected: {child_decision.reason}",
                                        execution_duration_ms=0.0,
                                        metadata=child_params,
                                        trace_id=trace_id,
                                    )
                                chat_resp = ChatResponse(
                                    message=f"Action declined by governance security policy: {child_decision.reason}",
                                    action_taken=None,
                                    basket_updated=False,
                                )
                                return chat_resp
                    else:
                        policy_decision = await policy_engine.check(
                            agent_id=agent_id,
                            tool_name=tool_name,
                            params=tool_params,
                            session_context={
                                "user_id": user_id,
                                "session_id": session_id,
                                "trace_id": trace_id,
                            },
                            db=db,
                        )

                        if getattr(policy_decision, "requires_approval", False):
                            from app.models.governance import ApprovalRequest
                            from app.observability.event_stream import event_stream_broker

                            approval_req = ApprovalRequest(
                                trace_id=trace_id,
                                agent_id=agent_id,
                                user_id=user_id,
                                session_id=session_id,
                                tool_name=tool_name,
                                action="order:submit",
                                parameters=tool_params,
                                status="pending",
                                risk_level="HIGH",
                                reason=policy_decision.reason,
                            )
                            db.add(approval_req)
                            await db.commit()
                            await db.refresh(approval_req)

                            event_stream_broker.publish(
                                "approval_request",
                                {
                                    "id": str(approval_req.id),
                                    "trace_id": str(trace_id),
                                    "agent_id": agent_id,
                                    "tool_name": tool_name,
                                    "status": "pending",
                                    "risk_level": "HIGH",
                                },
                            )

                            with trace_span("audit_persistence", attributes={"approval_required": True}):
                                await audit_logger.log(
                                    db=db,
                                    agent_id=agent_id,
                                    user_id=user_id,
                                    session_id=session_id,
                                    tool_name=tool_name,
                                    action=f"tool_call:{tool_name}",
                                    target_resource=tool_name,
                                    governance_decision="requires_approval",
                                    execution_status="pending",
                                    denial_reason=policy_decision.reason,
                                    execution_duration_ms=0.0,
                                    metadata=tool_params,
                                    trace_id=trace_id,
                                )

                            chat_resp = ChatResponse(
                                message=f"Order submission requires Human-in-the-Loop supervisor approval (Approval ID: {str(approval_req.id)[:8]}...). An enterprise administrator has been notified to review and authorize the order in the Action Bridge Console.",
                                action_taken=tool_name,
                                basket_updated=False,
                            )
                            return chat_resp

                        if not policy_decision.allowed:
                            policy_span.status = "error"
                            policy_span.attributes["denial_reason"] = policy_decision.reason
                            with trace_span("audit_persistence", attributes={"denied": True}):
                                await audit_logger.log(
                                    db=db,
                                    agent_id=agent_id,
                                    user_id=user_id,
                                    session_id=session_id,
                                    tool_name=tool_name,
                                    action=f"tool_call:{tool_name}",
                                    target_resource=tool_name,
                                    governance_decision="denied",
                                    execution_status="failed",
                                    denial_reason=policy_decision.reason,
                                    execution_duration_ms=0.0,
                                    metadata=tool_params,
                                    trace_id=trace_id,
                                )
                            chat_resp = ChatResponse(
                                message=f"Action declined by governance security policy: {policy_decision.reason}",
                                action_taken=None,
                                basket_updated=False,
                            )
                            return chat_resp

                # Stage 4: Tool Execution
                tool_params["user_id"] = user_id
                tool_params["session_id"] = session_id

                try:
                    # Accurately compute execution duration using time.perf_counter after block exits
                    t0 = time.perf_counter()
                    with trace_span("tool_execution", attributes={"tool_name": tool_name}):
                        tool_result = await tool_executor.execute(
                            tool_name=tool_name,
                            params=tool_params,
                            db=db,
                        )
                    duration_ms = round((time.perf_counter() - t0) * 1000, 2)

                    # Stage 5: Audit Persistence
                    with trace_span("audit_persistence", attributes={"status": "success"}):
                        if is_multi_item:
                            await audit_logger.log(
                                db=db,
                                agent_id=agent_id,
                                user_id=user_id,
                                session_id=session_id,
                                tool_name=tool_name,
                                action="tool_call:add_to_cart:batch",
                                target_resource="cart:batch",
                                governance_decision="allowed",
                                execution_status="success",
                                denial_reason=None,
                                execution_duration_ms=duration_ms,
                                metadata={"item_count": len(tool_params["items"])},
                                trace_id=trace_id,
                            )
                            per_item_ms = round(duration_ms / len(tool_params["items"]), 2)
                            for sub_item in tool_params["items"]:
                                await audit_logger.log(
                                    db=db,
                                    agent_id=agent_id,
                                    user_id=user_id,
                                    session_id=session_id,
                                    tool_name="add_to_cart",
                                    action="tool_call:add_to_cart:item",
                                    target_resource=str(sub_item.get("product_id")),
                                    governance_decision="allowed",
                                    execution_status="success",
                                    denial_reason=None,
                                    execution_duration_ms=per_item_ms,
                                    metadata=sub_item,
                                    trace_id=trace_id,
                                )
                        else:
                            await audit_logger.log(
                                db=db,
                                agent_id=agent_id,
                                user_id=user_id,
                                session_id=session_id,
                                tool_name=tool_name,
                                action=f"tool_call:{tool_name}",
                                target_resource=tool_name,
                                governance_decision="allowed",
                                execution_status="success",
                                denial_reason=None,
                                execution_duration_ms=duration_ms,
                                metadata=tool_params,
                                trace_id=trace_id,
                            )

                    # Format response for customer
                    if tool_name == "search_products":
                        products_list = [ProductResponse.model_validate(p) for p in tool_result]
                        query = tool_params.get("query", "")

                        if not products_list:
                            truthful_msg = f"Sorry, we don't have '{query}' in our store catalogue right now. Would you like to check out our fresh fruits, vegetables, or atta instead?"
                            if hasattr(self.provider, "generate_truthful_response"):
                                ai_msg = await self.provider.generate_truthful_response(
                                    f"The user asked for '{query}', but our database catalog returned 0 results. State clearly and politely that '{query}' is not in stock right now, and suggest available items like fresh apples, bananas, or tomatoes in 1 short spoken sentence."
                                )
                                if ai_msg:
                                    truthful_msg = ai_msg

                            chat_resp = ChatResponse(
                                message=truthful_msg,
                                action_taken="search_products",
                                products_to_select=[],
                                basket_updated=False,
                            )
                        else:
                            first_prod = products_list[0]
                            uom = getattr(first_prod, "unit_of_measurement", "unit")
                            price = getattr(first_prod, "price_aed", 0)
                            truthful_msg = llm_response.text_response or f"Yes, we have {first_prod.name} for {price} AED per {uom}! Would you like me to add some to your basket?"
                            if not llm_response.text_response and hasattr(self.provider, "generate_truthful_response"):
                                ai_msg = await self.provider.generate_truthful_response(
                                    f"Database found: {first_prod.name} at {price} AED per {uom}. Tell customer we have it in stock and ask if they'd like to add it in 1 friendly spoken sentence."
                                )
                                if ai_msg:
                                    truthful_msg = ai_msg

                            chat_resp = ChatResponse(
                                message=truthful_msg,
                                action_taken="search_products",
                                products_to_select=products_list,
                                basket_updated=False,
                            )
                    elif tool_name in ("add_to_cart", "update_cart_item", "remove_from_cart"):
                        chat_resp = ChatResponse(
                            message=llm_response.text_response or "Your basket has been updated.",
                            action_taken=tool_name,
                            basket_updated=True,
                            cart=tool_result,
                        )
                    elif tool_name in ("get_cart", "get_checkout_preview"):
                        chat_resp = ChatResponse(
                            message=llm_response.text_response or "Here is your cart summary.",
                            action_taken=tool_name,
                            basket_updated=False,
                            cart=tool_result,
                        )
                    else:
                        chat_resp = ChatResponse(
                            message=llm_response.text_response,
                            action_taken=tool_name,
                            basket_updated=False,
                        )

                    with trace_span(
                        "avatar_response",
                        attributes={"text_length": len(chat_resp.message)},
                    ):
                        try:
                            chat_resp.audio_base64 = await generate_neural_audio(chat_resp.message)
                        except Exception:
                            pass

                    intent = self._extract_intent_items(session_id)
                    items_actually_added = intent["added"] if tool_name == "add_to_cart" else []
                    try:
                        await conversation_evaluator.evaluate(
                            db=db,
                            session_id=session_id,
                            user_id=user_id,
                            trace_id=trace_id,
                            user_message=message,
                            agent_response=chat_resp.message,
                            tool_name_called=tool_name,
                            tool_params=tool_params,
                            items_requested=intent["requested"],
                            items_unavailable=intent["unavailable"],
                            items_ambiguous=intent["ambiguous"],
                            items_added=items_actually_added,
                            basket_updated=chat_resp.basket_updated,
                        )
                    except Exception:
                        pass

                    return chat_resp

                except Exception as exc:
                    with trace_span("audit_persistence", attributes={"error": str(exc)}):
                        await audit_logger.log(
                            db=db,
                            agent_id=agent_id,
                            user_id=user_id,
                            session_id=session_id,
                            tool_name=tool_name,
                            action=f"tool_call:{tool_name}",
                            target_resource=tool_name,
                            governance_decision="allowed",
                            execution_status="failed",
                            denial_reason=str(exc),
                            execution_duration_ms=0.0,
                            metadata=tool_params,
                            trace_id=trace_id,
                        )

                    chat_resp = ChatResponse(
                        message=f"Tool execution failed: {str(exc)}",
                        action_taken=tool_name,
                        basket_updated=False,
                    )
                    return chat_resp

        finally:
            await persist_trace_spans(db=db, trace_id=trace_id)


conversation_engine = ConversationEngine()

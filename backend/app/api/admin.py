import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import agent_registry_service
from app.api.auth import get_current_admin
from app.config import settings
from app.database import get_db
from app.governance.permissions import TOOL_PERMISSIONS, AgentPermissions
from app.governance.policy_engine import policy_engine
from app.models.governance import ApprovalRequest, AuditLog, EvaluationLog, TraceSpan
from app.models.user import User
from app.observability.audit_logger import audit_logger
from app.observability.event_stream import event_stream_broker
from app.observability.metrics import metrics_service
from app.observability.tracing import get_cached_trace
from app.schemas.governance import (
    AgentCreateRequest,
    AgentResponse,
    AgentUpdateRequest,
    ApprovalRequestResponse,
    ApprovalResolutionRequest,
    AuditLogFilter,
    AuditLogResponse,
    DashboardMetrics,
    ToolResponse,
    TraceJourneyResponse,
    TraceSpanResponse,
    TraceSummary,
)
from app.tools.registry import tool_registry_service

router = APIRouter(dependencies=[Depends(get_current_admin)])


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Returns governance operational telemetry including total actions,
    allowed vs denied ratios, success rate, and tool breakdown.
    """
    return await metrics_service.get_dashboard_metrics(db=db)


@router.get("/events/stream")
async def stream_admin_events(
    request: Request,
    admin_user: User = Depends(get_current_admin),
):
    """
    Server-Sent Events (SSE) endpoint streaming real-time audit logs,
    governance decisions, and trace spans to connected admin dashboards.
    """
    return StreamingResponse(
        event_stream_broker.subscribe(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/traces", response_model=List[TraceSummary])
async def list_recent_traces(
    limit: int = Query(30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Lists recent traces with request journey summary, total duration, and status.
    """
    stmt = (
        select(
            TraceSpan.trace_id,
            func.min(TraceSpan.start_time).label("start_t"),
            func.count(TraceSpan.id).label("spans_cnt"),
        )
        .group_by(TraceSpan.trace_id)
        .order_by(desc("start_t"))
        .limit(limit)
    )
    res = await db.execute(stmt)
    trace_groups = res.fetchall()

    summaries = []
    for tid, st, cnt in trace_groups:
        spans_stmt = (
            select(TraceSpan)
            .where(TraceSpan.trace_id == tid)
            .order_by(TraceSpan.start_time)
        )
        s_res = await db.execute(spans_stmt)
        all_spans = s_res.scalars().all()
        if not all_spans:
            continue

        root_s = next(
            (s for s in all_spans if s.name in ("agent.chat_turn", "chat_turn") or s.parent_span_id is None),
            all_spans[0],
        )
        total_dur = (
            root_s.duration_ms
            if root_s.name in ("agent.chat_turn", "chat_turn")
            else sum(s.duration_ms for s in all_spans)
        )
        status_val = "error" if any(s.status == "error" for s in all_spans) else "ok"
        msg = None
        for s in all_spans:
            if s.attributes and "message" in s.attributes:
                msg = s.attributes["message"]
                break

        summaries.append(
            TraceSummary(
                trace_id=str(tid),
                start_time=st,
                total_duration_ms=round(total_dur, 1),
                status=status_val,
                root_action=root_s.name,
                user_message=msg,
                spans_count=cnt,
                jaeger_url=f"{settings.JAEGER_UI_URL}/trace/{tid.hex}",
            )
        )
    return summaries


@router.get("/traces/{trace_id}", response_model=TraceJourneyResponse)
async def get_trace_journey(
    trace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Fetches the full lifecycle journey and all spans for a specific trace.
    Returns parent/child relationships, real timestamps, stage durations,
    and OpenTelemetry attributes.
    """
    stmt = (
        select(TraceSpan)
        .where(TraceSpan.trace_id == trace_id)
        .order_by(TraceSpan.start_time)
    )
    res = await db.execute(stmt)
    spans = res.scalars().all()

    if not spans:
        cached = get_cached_trace(str(trace_id))
        if cached:
            spans_models = [
                TraceSpanResponse(
                    trace_id=trace_id,
                    span_id=s["span_id"],
                    parent_span_id=s.get("parent_span_id"),
                    name=s["name"],
                    service_name=s.get("service_name", "kon-action-bridge"),
                    start_time=datetime.fromisoformat(s["start_time"]) if s.get("start_time") else datetime.now(timezone.utc),
                    end_time=datetime.fromisoformat(s["end_time"]) if s.get("end_time") else datetime.now(timezone.utc),
                    duration_ms=s.get("duration_ms", 0.0),
                    status=s.get("status", "ok"),
                    attributes=s.get("attributes", {}),
                    events=s.get("events", []),
                )
                for s in cached
            ]
            root_s = next(
                (s for s in spans_models if s.parent_span_id is None or s.name == "agent.chat_turn"),
                spans_models[0],
            )
            return TraceJourneyResponse(
                trace_id=str(trace_id),
                start_time=root_s.start_time,
                total_duration_ms=root_s.duration_ms,
                status=root_s.status,
                user_message=root_s.attributes.get("message"),
                spans=spans_models,
                jaeger_url=f"{settings.JAEGER_UI_URL}/trace/{trace_id.hex}",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace journey for '{trace_id}' not found",
        )

    spans_models = [TraceSpanResponse.model_validate(s) for s in spans]
    root_s = next(
        (s for s in spans_models if s.parent_span_id is None or s.name == "agent.chat_turn"),
        spans_models[0],
    )
    return TraceJourneyResponse(
        trace_id=str(trace_id),
        start_time=root_s.start_time,
        total_duration_ms=root_s.duration_ms,
        status=root_s.status,
        user_message=root_s.attributes.get("message"),
        spans=spans_models,
        jaeger_url=f"{settings.JAEGER_UI_URL}/trace/{trace_id.hex}",
    )


@router.post("/traces/sync-jaeger")
async def sync_traces_to_jaeger(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Syncs recent trace spans from the database directly into the local Jaeger collector.
    """
    from app.observability.tracing import sync_database_spans_to_jaeger
    count = await sync_database_spans_to_jaeger(db)
    return {"status": "ok", "traces_synced": count, "service": settings.OTEL_SERVICE_NAME}


@router.get("/agents", response_model=List[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Lists all AI agents registered in the governance registry with
    department, model, tenant metadata, and real-time request/failure counts.
    """
    agents = await agent_registry_service.list_agents(db=db)
    agent_responses = []

    for a in agents:
        req_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.agent_id == a.agent_id)
        )
        r_res = await db.execute(req_stmt)
        total_reqs = r_res.scalar_one()

        fail_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.agent_id == a.agent_id,
                or_(
                    AuditLog.governance_decision == "denied",
                    AuditLog.execution_status == "failed",
                ),
            )
        )
        f_res = await db.execute(fail_stmt)
        fail_cnt = f_res.scalar_one()

        resp = AgentResponse(
            id=a.id,
            agent_id=a.agent_id,
            name=a.name,
            description=a.description,
            role=a.role,
            department=getattr(a, "department", "Retail Commerce"),
            model_provider=getattr(a, "model_provider", "Google Gemini"),
            model_version=getattr(a, "model_version", "gemini-1.5-pro"),
            owner_tenant=getattr(a, "owner_tenant", "KON Retail Org"),
            status=a.status,
            allowed_tools=a.allowed_tools or [],
            created_at=a.created_at,
            total_requests=total_reqs,
            failure_count=fail_cnt,
        )
        agent_responses.append(resp)

    return agent_responses


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Registers a new AI employee agent into the governance registry.
    """
    existing = await agent_registry_service.get_agent(payload.agent_id, db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with ID '{payload.agent_id}' already exists in registry",
        )

    agent = await agent_registry_service.register_agent(payload.model_dump(), db)
    event_stream_broker.publish("agent_updated", {"agent_id": agent.agent_id, "action": "created"})
    return AgentResponse.model_validate(agent)


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    payload: AgentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Updates an AI employee's status, role, department, model, or permitted tools.
    """
    agent = await agent_registry_service.update_agent(
        agent_id=agent_id,
        updates=payload.model_dump(exclude_unset=True),
        db=db,
    )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID '{agent_id}' not found",
        )
    event_stream_broker.publish("agent_updated", {"agent_id": agent.agent_id, "action": "updated"})
    return AgentResponse.model_validate(agent)


@router.post("/agents/{agent_id}/toggle-status", response_model=AgentResponse)
async def toggle_agent_status(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    1-click enable/disable toggle for an AI employee agent.
    Inactive agents are immediately blocked by the policy engine.
    """
    agent = await agent_registry_service.toggle_agent_status(agent_id=agent_id, db=db)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID '{agent_id}' not found",
        )
    event_stream_broker.publish(
        "agent_updated",
        {"agent_id": agent.agent_id, "status": agent.status, "action": "status_toggled"},
    )
    return AgentResponse.model_validate(agent)


# ── Human-in-the-Loop (HITL) Approvals ────────────────────────────────────────

@router.get("/approvals", response_model=List[ApprovalRequestResponse])
async def list_approvals(
    status_filter: Optional[str] = Query(None, description="pending, approved, or rejected"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Lists pending and historical Human-in-the-Loop (HITL) approval requests.
    """
    stmt = select(ApprovalRequest)
    if status_filter:
        stmt = stmt.where(ApprovalRequest.status == status_filter)
    stmt = stmt.order_by(desc(ApprovalRequest.created_at)).limit(limit)

    res = await db.execute(stmt)
    records = res.scalars().all()
    return [ApprovalRequestResponse.model_validate(r) for r in records]


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    approval_id: uuid.UUID,
    payload: Optional[ApprovalResolutionRequest] = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Supervisor approves a pending high-risk AI agent action (e.g. submit_order).
    Records approval in tamper-evident audit logs.
    """
    stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    res = await db.execute(stmt)
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' not found",
        )

    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval request '{approval_id}' has already been resolved with status '{req.status}'. Decisions are only accepted for pending requests.",
        )

    req.status = "approved"
    req.resolved_at = datetime.now(timezone.utc)
    req.resolved_by = admin_user.username
    req.resolution_notes = payload.notes if payload else "Approval decision recorded (Execution: Not performed in this MVP)"
    await db.commit()
    await db.refresh(req)

    # Log supervisor authorization into tamper-evident audit log
    await audit_logger.log(
        db=db,
        agent_id=req.agent_id,
        user_id=req.user_id,
        session_id=req.session_id,
        tool_name=req.tool_name,
        action=f"approval:{req.tool_name}:approved",
        target_resource=f"approval:{req.id}",
        governance_decision="approved",
        execution_status="success",
        denial_reason=None,
        execution_duration_ms=0.0,
        metadata={
            "approval_id": str(req.id),
            "approved_by": admin_user.username,
            "parameters": req.parameters,
        },
        trace_id=req.trace_id,
    )

    event_stream_broker.publish(
        "approval_resolved",
        {"id": str(req.id), "status": "approved", "resolved_by": admin_user.username},
    )
    return ApprovalRequestResponse.model_validate(req)


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    approval_id: uuid.UUID,
    payload: Optional[ApprovalResolutionRequest] = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Supervisor rejects a pending AI agent action.
    """
    stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    res = await db.execute(stmt)
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' not found",
        )

    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval request '{approval_id}' has already been resolved with status '{req.status}'. Decisions are only accepted for pending requests.",
        )

    reason = payload.notes if (payload and payload.notes) else "Action rejected by supervisor"
    req.status = "rejected"
    req.resolved_at = datetime.now(timezone.utc)
    req.resolved_by = admin_user.username
    req.resolution_notes = reason
    await db.commit()
    await db.refresh(req)

    # Log supervisor rejection into tamper-evident audit log
    await audit_logger.log(
        db=db,
        agent_id=req.agent_id,
        user_id=req.user_id,
        session_id=req.session_id,
        tool_name=req.tool_name,
        action=f"approval:{req.tool_name}:rejected",
        target_resource=f"approval:{req.id}",
        governance_decision="denied",
        execution_status="failed",
        denial_reason=reason,
        execution_duration_ms=0.0,
        metadata={
            "approval_id": str(req.id),
            "rejected_by": admin_user.username,
            "parameters": req.parameters,
        },
        trace_id=req.trace_id,
    )

    event_stream_broker.publish(
        "approval_resolved",
        {"id": str(req.id), "status": "rejected", "resolved_by": admin_user.username},
    )
    return ApprovalRequestResponse.model_validate(req)


@router.post("/approvals/simulate", response_model=ApprovalRequestResponse)
async def simulate_approval_request(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Simulates a high-value customer order submit_order request requiring Human-in-the-Loop
    supervisor approval for demonstration purposes.
    """
    sim_trace = uuid.uuid4()
    req = ApprovalRequest(
        trace_id=sim_trace,
        agent_id="kon-shopping-agent",
        user_id=str(admin_user.id),
        session_id="simulated-approval-session",
        tool_name="submit_order",
        action="order:submit",
        parameters={
            "order_value_aed": 348.50,
            "items_count": 4,
            "items": [
                {"name": "Al Baker Chakki Atta 2kg", "qty": 2, "price_aed": 17.00},
                {"name": "Organic Whole Chicken 1kg", "qty": 2, "price_aed": 48.00},
                {"name": "Al Rawabi Fresh Milk 2L", "qty": 2, "price_aed": 22.00},
                {"name": "Fresh Royal Gala Apples", "qty": 2, "price_aed": 15.00},
            ],
            "delivery_address": "Downtown Dubai, UAE",
            "payment_method": "Credit Card",
        },
        status="pending",
        risk_level="HIGH",
        reason="Governance Policy: Orders exceeding AED 200 or submit_order operations require Human-in-the-Loop supervisor authorization",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    event_stream_broker.publish(
        "approval_request",
        {
            "id": str(req.id),
            "trace_id": str(sim_trace),
            "agent_id": req.agent_id,
            "tool_name": req.tool_name,
            "status": "pending",
            "risk_level": "HIGH",
        },
    )
    return ApprovalRequestResponse.model_validate(req)


@router.get("/tools", response_model=List[ToolResponse])
async def list_tools(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Lists all registered commerce tools and their JSON schemas.
    """
    tools = await tool_registry_service.list_tools(db=db)
    return [ToolResponse.model_validate(t) for t in tools]


@router.get("/audit-logs")
async def list_audit_logs(
    agent_id: Optional[str] = Query(None),
    tool_name: Optional[str] = Query(None),
    decision: Optional[str] = Query(None, description="allowed or denied"),
    status: Optional[str] = Query(None, description="success, failed, or pending"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Query tamper-evident audit logs with flexible filtering.
    Returns {logs: [...], total: int} to support pagination in the dashboard.
    """
    from sqlalchemy import func

    # Count total matching records
    count_stmt = select(func.count()).select_from(AuditLog)
    if agent_id:
        count_stmt = count_stmt.where(AuditLog.agent_id == agent_id)
    if tool_name:
        count_stmt = count_stmt.where(AuditLog.tool_name == tool_name)
    if decision:
        count_stmt = count_stmt.where(AuditLog.governance_decision == decision)
    if status:
        count_stmt = count_stmt.where(AuditLog.execution_status == status)
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    stmt = select(AuditLog)
    if agent_id:
        stmt = stmt.where(AuditLog.agent_id == agent_id)
    if tool_name:
        stmt = stmt.where(AuditLog.tool_name == tool_name)
    if decision:
        stmt = stmt.where(AuditLog.governance_decision == decision)
    if status:
        stmt = stmt.where(AuditLog.execution_status == status)
    if start_date:
        stmt = stmt.where(AuditLog.timestamp >= start_date)
    if end_date:
        stmt = stmt.where(AuditLog.timestamp <= end_date)

    stmt = stmt.order_by(desc(AuditLog.timestamp)).limit(limit).offset(offset)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return {
        "logs": [AuditLogResponse.model_validate(log) for log in logs],
        "total": total,
    }


@router.get("/audit-logs-verify-chain")
async def verify_audit_chain(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Cryptographically verifies the SHA-256 hash chain of the audit trail.
    Ensures complete immutability and flags any tampered or deleted records.
    """
    return await audit_logger.verify_chain(db=db)


@router.get("/audit-logs/{event_id}", response_model=AuditLogResponse)
async def get_audit_log_entry(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Fetch granular details for a single governance audit log event.
    """
    stmt = select(AuditLog).where(AuditLog.event_id == event_id)
    res = await db.execute(stmt)
    log = res.scalar_one_or_none()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log event with ID '{event_id}' not found",
        )
    return AuditLogResponse.model_validate(log)


@router.get("/security-events", response_model=List[AuditLogResponse])
async def list_security_events(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Returns only security-relevant audit logs (governance denials or execution failures).
    """
    stmt = (
        select(AuditLog)
        .where(
            or_(
                AuditLog.governance_decision == "denied",
                AuditLog.execution_status == "failed",
            )
        )
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get("/policies", response_model=Dict[str, Any])
async def get_policies_configuration(
    admin_user: User = Depends(get_current_admin),
):
    """
    Returns live policy engine rules, permission matrices, and constraints
    in the PolicyConfig format expected by the frontend.
    """
    policies = [
        {
            "tool": "search_products",
            "action_name": "Search Product Catalog",
            "policy": "Allowed",
            "description": "Any registered active agent may search the catalog. No cart modification occurs.",
            "checks": ["agent_registered", "agent_active", "tool_registered", "tool_in_allowed_tools"],
        },
        {
            "tool": "get_product_details",
            "action_name": "View Product Details",
            "policy": "Allowed",
            "description": "Read-only product data lookup. No side effects.",
            "checks": ["agent_registered", "agent_active", "tool_registered"],
        },
        {
            "tool": "add_to_cart",
            "action_name": "Add Product to Basket",
            "policy": "Allowed",
            "description": "Allowed with strict parameter validation. Price fetched from DB only.",
            "checks": ["agent_registered", "agent_active", "valid_product_uuid", "quantity_0_to_100", "product_in_stock"],
        },
        {
            "tool": "update_cart_item",
            "action_name": "Update Basket Quantity",
            "policy": "Allowed",
            "description": "Quantity update permitted with same constraints as add_to_cart.",
            "checks": ["agent_registered", "agent_active", "valid_cart_item_uuid", "quantity_0_to_100", "session_ownership"],
        },
        {
            "tool": "remove_from_cart",
            "action_name": "Remove Item from Basket",
            "policy": "Allowed",
            "description": "Session-scoped removal. Cross-user removal is blocked.",
            "checks": ["agent_registered", "agent_active", "valid_cart_item_uuid", "session_ownership"],
        },
        {
            "tool": "get_cart",
            "action_name": "View Shopping Basket",
            "policy": "Allowed",
            "description": "Read basket state for authenticated session only.",
            "checks": ["agent_registered", "agent_active", "session_ownership"],
        },
        {
            "tool": "get_checkout_preview",
            "action_name": "Preview Checkout Breakdown (Non-Binding)",
            "policy": "Preview Only (No Order Placed)",
            "description": "Non-binding basket breakdown preview for customer review. No order execution, credit card processing, or courier dispatch is executed in this MVP. Full human approval workflows will bind when place_order is introduced.",
            "checks": ["agent_registered", "agent_active", "explicit_confirmation_flag", "no_payment_execution"],
        },
    ]

    security_principles = [
        "1. The LLM cannot directly access the database.",
        "2. The LLM cannot call arbitrary APIs.",
        "3. Only registered tools can be executed.",
        "4. Every tool execution passes through the governance engine.",
        "5. Validate inputs strictly on the backend via Pydantic schemas.",
        "6. Check authenticated user and session ownership before cart operations.",
        "7. Verify product IDs and live stock using server database data.",
        "8. Never trust frontend or LLM supplied prices.",
        "9. Every denied action is logged with reason and trace ID.",
        "10. Sensitive credentials stored in environment variables, never hardcoded.",
        "11. Use trace UUIDs to correlate agent requests with backend events.",
        "12. Redact passwords, tokens, and payment secrets from audit logs.",
        "13. Protect administrative routes using role-based JWT claims.",
        "14. Do not execute real payments or dispatch physical grocery orders.",
    ]

    return {
        "agent_id": AgentPermissions.SHOPPING_AGENT_ID,
        "agent_name": "KON Shopping Assistant",
        "status": "active",
        "fail_closed_mode": True,
        "policies": policies,
        "security_principles": security_principles,
        "tool_permissions": TOOL_PERMISSIONS,
        "agents": {
            AgentPermissions.SHOPPING_AGENT_ID: {
                "allowed_tools": AgentPermissions.ALLOWED_TOOLS_SHOPPING_AGENT,
                "role": "shopping_assistant",
            }
        },
    }


@router.post("/simulate-blocked-action")
async def simulate_blocked_action(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Admin-only endpoint that intentionally triggers a governance denial.
    Used for live dashboard demonstrations. Attempts to call an unregistered
    tool ('admin_drop_database') as the kon-shopping-agent and records the
    resulting denial in the audit log.
    """
    from app.governance.policy_engine import policy_engine
    from app.observability.audit_logger import audit_logger

    agent_id = AgentPermissions.SHOPPING_AGENT_ID
    tool_name = "admin_drop_database"
    action = "DROP TABLE users; DROP TABLE products;"
    session_id = "admin-simulation"
    trace_uuid = uuid.uuid4()

    session_context = {
        "user_id": str(admin_user.id),
        "session_id": session_id,
        "trace_id": trace_uuid,
    }

    # This call WILL be denied by the policy engine (tool not registered)
    decision = await policy_engine.check(
        agent_id=agent_id,
        tool_name=tool_name,
        params={"query": action},
        session_context=session_context,
        db=db,
    )

    governance_decision = "allowed" if decision.allowed else "denied"
    denial_reason = decision.reason if not decision.allowed else None

    # Persist the denial to the audit log
    await audit_logger.log(
        db=db,
        agent_id=agent_id,
        user_id=str(admin_user.id),
        session_id=session_id,
        tool_name=tool_name,
        action=action,
        target_resource="system.database",
        governance_decision=governance_decision,
        execution_status="failed",
        denial_reason=denial_reason,
        execution_duration_ms=0.0,
        trace_id=trace_uuid,
        metadata={"simulation": True, "triggered_by": str(admin_user.username)},
    )

    return {
        "simulated": True,
        "tool_attempted": tool_name,
        "governance_decision": governance_decision,
        "denial_reason": denial_reason,
        "trace_id": str(trace_uuid),
        "message": f"Action '{tool_name}' was {governance_decision} by the governance engine and recorded in the audit log.",
    }


# ── LLM-as-a-Judge Evaluation Endpoints ─────────────────────────────────────

@router.get("/evaluations")
async def list_evaluations(
    verdict: Optional[str] = Query(None, description="Filter by verdict: pass | warn | fail"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Returns LLM-as-a-Judge evaluation records with semantic quality scores
    including hallucination, omission, premature action, and intent coverage.
    """
    stmt = select(EvaluationLog).order_by(desc(EvaluationLog.timestamp))
    if verdict:
        stmt = stmt.where(EvaluationLog.evaluation_verdict == verdict)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "session_id": r.session_id,
            "user_message": r.user_message,
            "agent_response": r.agent_response,
            "tool_name_called": r.tool_name_called,
            "items_requested": r.items_requested or [],
            "items_unavailable": r.items_unavailable or [],
            "items_ambiguous": r.items_ambiguous or [],
            "items_added": r.items_added or [],
            "hallucination_detected": r.hallucination_detected,
            "omission_detected": r.omission_detected,
            "premature_action_detected": r.premature_action_detected,
            "intent_coverage_score": r.intent_coverage_score,
            "evaluation_notes": r.evaluation_notes,
            "evaluation_verdict": r.evaluation_verdict,
        }
        for r in rows
    ]


@router.get("/evaluations/summary")
async def evaluation_summary(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """Returns aggregate evaluation quality metrics for the observability dashboard."""
    from sqlalchemy import func
    total_stmt = select(func.count(EvaluationLog.id))
    pass_stmt = select(func.count(EvaluationLog.id)).where(EvaluationLog.evaluation_verdict == "pass")
    warn_stmt = select(func.count(EvaluationLog.id)).where(EvaluationLog.evaluation_verdict == "warn")
    fail_stmt = select(func.count(EvaluationLog.id)).where(EvaluationLog.evaluation_verdict == "fail")
    halluc_stmt = select(func.count(EvaluationLog.id)).where(EvaluationLog.hallucination_detected.is_(True))
    omit_stmt = select(func.count(EvaluationLog.id)).where(EvaluationLog.omission_detected.is_(True))
    premature_stmt = select(func.count(EvaluationLog.id)).where(EvaluationLog.premature_action_detected.is_(True))
    avg_cov_stmt = select(func.avg(EvaluationLog.intent_coverage_score))

    total = (await db.execute(total_stmt)).scalar() or 0
    passes = (await db.execute(pass_stmt)).scalar() or 0
    warns = (await db.execute(warn_stmt)).scalar() or 0
    fails = (await db.execute(fail_stmt)).scalar() or 0
    hallucinations = (await db.execute(halluc_stmt)).scalar() or 0
    omissions = (await db.execute(omit_stmt)).scalar() or 0
    premature = (await db.execute(premature_stmt)).scalar() or 0
    avg_cov = (await db.execute(avg_cov_stmt)).scalar()

    return {
        "total_turns_evaluated": total,
        "verdict_pass": passes,
        "verdict_warn": warns,
        "verdict_fail": fails,
        "quality_score_pct": round((passes / total * 100) if total > 0 else 100, 1),
        "hallucination_count": hallucinations,
        "omission_count": omissions,
        "premature_action_count": premature,
        "avg_intent_coverage_pct": round((avg_cov or 1.0) * 100, 1),
    }

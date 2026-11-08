import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.governance.tool_schemas import validate_tool_input
from app.models.governance import AgentRegistry, ToolRegistry


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    trace_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    requires_confirmation: bool = False
    requires_approval: bool = False  # Human-in-the-Loop supervisor approval required


class PolicyEngine:
    """
    Fail-closed policy governance engine that validates every tool request
    before tool dispatch. Enforces registry verification, authorization,
    and parameter constraints.
    """

    async def check(
        self,
        agent_id: str,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
    ) -> PolicyDecision:
        session_context = session_context or {}
        params = params or {}

        # Resolve or generate trace_id
        raw_trace = session_context.get("trace_id")
        if isinstance(raw_trace, uuid.UUID):
            trace_id = raw_trace
        elif isinstance(raw_trace, str):
            try:
                trace_id = uuid.UUID(raw_trace)
            except ValueError:
                trace_id = uuid.uuid4()
        else:
            trace_id = uuid.uuid4()

        # Database session is required for full validation
        if db is None:
            return PolicyDecision(
                allowed=False,
                reason="Governance engine error: Database session unavailable",
                trace_id=trace_id,
            )

        # 1. Is agent registered and active in AgentRegistry?
        agent_stmt = select(AgentRegistry).where(AgentRegistry.agent_id == agent_id)
        agent_result = await db.execute(agent_stmt)
        agent_entry = agent_result.scalar_one_or_none()

        if not agent_entry:
            return PolicyDecision(
                allowed=False,
                reason=f"Security rejection: Agent '{agent_id}' is not registered in AgentRegistry",
                trace_id=trace_id,
            )

        if agent_entry.status != "active":
            return PolicyDecision(
                allowed=False,
                reason=f"Security rejection: Agent '{agent_id}' is inactive (status: {agent_entry.status})",
                trace_id=trace_id,
            )

        # 2. Is tool registered and active in ToolRegistry?
        tool_stmt = select(ToolRegistry).where(ToolRegistry.tool_name == tool_name)
        tool_result = await db.execute(tool_stmt)
        tool_entry = tool_result.scalar_one_or_none()

        if not tool_entry:
            return PolicyDecision(
                allowed=False,
                reason=f"Security rejection: Tool '{tool_name}' is not registered in ToolRegistry",
                trace_id=trace_id,
            )

        if not tool_entry.is_active:
            return PolicyDecision(
                allowed=False,
                reason=f"Security rejection: Tool '{tool_name}' is marked as inactive",
                trace_id=trace_id,
            )

        # 3. Does agent's allowed_tools include this tool?
        allowed_tools = agent_entry.allowed_tools or []
        if tool_name not in allowed_tools:
            return PolicyDecision(
                allowed=False,
                reason=f"Authorization rejection: Agent '{agent_id}' is not permitted to execute tool '{tool_name}'",
                trace_id=trace_id,
            )

        # 4. Strict Pydantic Tool Input Schema Validation
        try:
            validate_tool_input(tool_name, params)
        except ValueError as val_err:
            return PolicyDecision(
                allowed=False,
                reason=f"Validation rejection: {val_err}",
                trace_id=trace_id,
            )

        # 5. Check confirmation and Human-in-the-Loop (HITL) approval boundaries
        if tool_name == "submit_order":
            return PolicyDecision(
                allowed=False,
                reason="Governance security requirement: 'submit_order' is a high-risk action requiring Human-in-the-Loop supervisor approval",
                trace_id=trace_id,
                requires_approval=True,
            )

        if tool_name == "get_checkout_preview":
            return PolicyDecision(
                allowed=True,
                reason="Tool allowed (preview only, requires explicit customer confirmation for order creation)",
                trace_id=trace_id,
                requires_confirmation=True,
            )

        # All policy checks successfully satisfied
        return PolicyDecision(
            allowed=True,
            reason="All governance policy and permission checks passed",
            trace_id=trace_id,
        )


policy_engine = PolicyEngine()

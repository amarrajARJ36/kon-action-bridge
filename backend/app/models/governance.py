import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from app.database import Base


class AgentRegistry(Base):
    __tablename__ = "agent_registry"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    role = Column(String(100), nullable=False)
    department = Column(String(100), default="Retail Commerce", nullable=False)
    model_provider = Column(String(100), default="Google Gemini", nullable=False)
    model_version = Column(String(100), default="gemini-1.5-pro", nullable=False)
    owner_tenant = Column(String(100), default="KON Retail Org", nullable=False)
    status = Column(String(50), default="active", nullable=False)  # "active" or "inactive"
    allowed_tools = Column(JSON, nullable=False, default=list)  # list of allowed tool names
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ToolRegistry(Base):
    __tablename__ = "tool_registry"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    input_schema = Column(JSON, nullable=False, default=dict)
    permission_level = Column(String(50), default="public", nullable=False)  # "public" or "restricted"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(
        Uuid(as_uuid=True),
        unique=True,
        index=True,
        default=uuid.uuid4,
        nullable=False,
    )
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    trace_id = Column(Uuid(as_uuid=True), index=True, nullable=False)
    agent_id = Column(String(100), index=True, nullable=True)
    user_id = Column(String(100), index=True, nullable=True)
    session_id = Column(String(100), index=True, nullable=True)
    tool_name = Column(String(100), index=True, nullable=True)
    action = Column(String(100), nullable=False)
    target_resource = Column(String(255), nullable=True)
    governance_decision = Column(String(50), nullable=False)  # "allowed" or "denied"
    execution_status = Column(String(50), nullable=False)  # "success", "failed", "pending"
    denial_reason = Column(Text, nullable=True)
    execution_duration_ms = Column(Float, nullable=True)
    entry_hash = Column(String(64), nullable=True, index=True)
    prev_hash = Column(String(64), nullable=True)
    # Stored under column name 'metadata' in the database
    metadata_payload = Column("metadata", JSON, nullable=True, default=dict)


class EvaluationLog(Base):
    """
    LLM-as-a-Judge evaluation record. Captures semantic quality scores
    per conversation turn: hallucination, omission, premature action, and
    intent vs. execution alignment. Used by the observability dashboard.
    """
    __tablename__ = "evaluation_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    session_id = Column(String(100), index=True, nullable=True)
    user_id = Column(String(100), index=True, nullable=True)
    trace_id = Column(Uuid(as_uuid=True), index=True, nullable=True)

    # Raw conversation turn
    user_message = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)
    tool_name_called = Column(String(100), nullable=True)
    tool_params = Column(JSON, nullable=True, default=dict)

    # Intent extraction
    items_requested = Column(JSON, nullable=True)   # e.g. [{"name": "apple", "qty": 1}, ...]
    items_unavailable = Column(JSON, nullable=True)  # items that returned 0 results
    items_ambiguous = Column(JSON, nullable=True)    # items needing disambiguation
    items_added = Column(JSON, nullable=True)        # items actually added to cart

    # Semantic quality flags (auto-computed)
    hallucination_detected = Column(Boolean, default=False, nullable=False)
    omission_detected = Column(Boolean, default=False, nullable=False)
    premature_action_detected = Column(Boolean, default=False, nullable=False)
    intent_coverage_score = Column(Float, nullable=True)  # 0.0 – 1.0: items addressed / items requested
    evaluation_notes = Column(Text, nullable=True)        # human-readable explanation

    # Overall pass/fail
    evaluation_verdict = Column(String(20), nullable=False, default="pass")  # "pass" | "warn" | "fail"


class TraceSpan(Base):
    """
    OpenTelemetry-compatible distributed trace span.
    Captures stage timings, parent/child relationships, metadata, and outcomes
    across the entire lifecycle of a conversational or API request.
    """
    __tablename__ = "trace_spans"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(Uuid(as_uuid=True), index=True, nullable=False)
    span_id = Column(String(36), index=True, nullable=False)
    parent_span_id = Column(String(36), index=True, nullable=True)
    name = Column(String(100), index=True, nullable=False)
    service_name = Column(String(100), default="kon-action-bridge", nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Float, nullable=False)
    status = Column(String(20), default="ok", nullable=False)  # "ok" or "error"
    attributes = Column(JSON, nullable=True, default=dict)
    events = Column(JSON, nullable=True, default=list)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ApprovalRequest(Base):
    """
    Human-in-the-Loop (HITL) approval record for high-risk or sensitive AI agent actions.
    When an agent triggers an action requiring human oversight (such as submit_order),
    an approval request is created for supervisor confirmation or rejection.
    """
    __tablename__ = "approval_requests"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(Uuid(as_uuid=True), index=True, nullable=False)
    agent_id = Column(String(100), index=True, nullable=False)
    user_id = Column(String(100), index=True, nullable=True)
    session_id = Column(String(100), index=True, nullable=True)
    tool_name = Column(String(100), index=True, nullable=False, default="submit_order")
    action = Column(String(100), nullable=False, default="order:submit")
    parameters = Column(JSON, nullable=True, default=dict)
    status = Column(String(20), default="pending", nullable=False)  # "pending", "approved", "rejected"
    risk_level = Column(String(20), default="HIGH", nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)



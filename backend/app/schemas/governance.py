import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AgentResponse(BaseModel):
    id: uuid.UUID
    agent_id: str
    name: str
    description: Optional[str] = None
    role: str
    department: str = "Retail Commerce"
    model_provider: str = "Google Gemini"
    model_version: str = "gemini-1.5-pro"
    owner_tenant: str = "KON Retail Org"
    status: str
    allowed_tools: List[str] = Field(default_factory=list)
    created_at: datetime
    total_requests: int = 0
    failure_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AgentCreateRequest(BaseModel):
    agent_id: str
    name: str
    description: Optional[str] = None
    role: str
    department: str = "Retail Commerce"
    model_provider: str = "Google Gemini"
    model_version: str = "gemini-1.5-pro"
    owner_tenant: str = "KON Retail Org"
    status: str = "active"
    allowed_tools: List[str] = Field(default_factory=list)


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    model_provider: Optional[str] = None
    model_version: Optional[str] = None
    owner_tenant: Optional[str] = None
    status: Optional[str] = None
    allowed_tools: Optional[List[str]] = None


class ApprovalRequestResponse(BaseModel):
    id: uuid.UUID
    trace_id: uuid.UUID
    agent_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tool_name: str
    action: str
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    status: str
    risk_level: str
    reason: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalResolutionRequest(BaseModel):
    notes: Optional[str] = None


class ToolResponse(BaseModel):
    id: uuid.UUID
    tool_name: str
    description: str
    input_schema: Dict[str, Any]
    permission_level: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    timestamp: datetime
    trace_id: uuid.UUID
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tool_name: Optional[str] = None
    action: str
    target_resource: Optional[str] = None
    governance_decision: str
    execution_status: str
    denial_reason: Optional[str] = None
    execution_duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata_payload")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AuditLogFilter(BaseModel):
    agent_id: Optional[str] = None
    tool_name: Optional[str] = None
    decision: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class DashboardMetrics(BaseModel):
    # Core summary metrics (backward compatible)
    total_actions: int
    allowed_actions: int
    denied_actions: int
    failed_actions: int
    success_rate: float  # Percentage (0.0 to 100.0)
    avg_duration_ms: float

    # Separated & Precise Observability Metrics
    total_agent_requests: int = 0
    total_tool_calls: int = 0
    policy_allow_rate: float = 100.0
    policy_denial_rate: float = 0.0
    approval_required_actions: int = 0
    tool_execution_success_rate: float = 100.0
    tool_execution_failure_rate: float = 0.0
    avg_ai_inference_ms: float = 0.0
    avg_tool_execution_ms: float = 0.0
    avg_e2e_latency_ms: float = 0.0

    recent_logs: List[AuditLogResponse] = Field(default_factory=list)
    tool_usage_breakdown: Dict[str, int] = Field(default_factory=dict)
    agent_activity: Dict[str, int] = Field(default_factory=dict)
    jaeger_ui_url: Optional[str] = None


class TraceSpanResponse(BaseModel):
    id: Optional[uuid.UUID] = None
    trace_id: uuid.UUID
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    service_name: str = "kon-action-bridge"
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status: str = "ok"
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TraceSummary(BaseModel):
    trace_id: str
    start_time: datetime
    total_duration_ms: float
    status: str
    root_action: str
    user_message: Optional[str] = None
    spans_count: int
    jaeger_url: Optional[str] = None


class TraceJourneyResponse(BaseModel):
    trace_id: str
    start_time: datetime
    total_duration_ms: float
    status: str
    user_message: Optional[str] = None
    agent_response: Optional[str] = None
    spans: List[TraceSpanResponse] = Field(default_factory=list)
    jaeger_url: Optional[str] = None

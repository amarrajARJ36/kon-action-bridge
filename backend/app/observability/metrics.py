from typing import Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog
from app.schemas.governance import AuditLogFilter, AuditLogResponse, DashboardMetrics


from typing import Optional, Set
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.governance import AuditLog, TraceSpan
from app.schemas.governance import AuditLogFilter, AuditLogResponse, DashboardMetrics


class MetricsService:
    """
    Computes real-time telemetry, operational metrics, and security statistics
    from governance audit logs and distributed trace spans.
    """

    async def get_dashboard_metrics(
        self,
        db: AsyncSession,
        filters: Optional[AuditLogFilter] = None,
    ) -> DashboardMetrics:
        # Base query with optional filtering
        query = select(AuditLog)
        if filters:
            if filters.agent_id:
                query = query.where(AuditLog.agent_id == filters.agent_id)
            if filters.tool_name:
                query = query.where(AuditLog.tool_name == filters.tool_name)
            if filters.decision:
                query = query.where(AuditLog.governance_decision == filters.decision)
            if filters.status:
                query = query.where(AuditLog.execution_status == filters.status)
            if filters.start_date:
                query = query.where(AuditLog.timestamp >= filters.start_date)
            if filters.end_date:
                query = query.where(AuditLog.timestamp <= filters.end_date)

        # Retrieve all matching logs to compute metrics accurately
        result = await db.execute(query.order_by(desc(AuditLog.timestamp)))
        all_logs = result.scalars().all()

        total_actions = len(all_logs)
        allowed_actions = 0
        denied_actions = 0
        failed_actions = 0
        successful_executions = 0
        duration_sum = 0.0
        duration_count = 0
        tool_usage_breakdown = {}
        agent_activity = {}

        # Distinct tracking for separated observability metrics
        agent_requests_traces: Set[str] = set()
        total_tool_calls = 0
        tool_allowed_count = 0
        tool_denied_count = 0
        tool_success_count = 0
        tool_failure_count = 0
        approval_required_count = 0

        for log in all_logs:
            if log.trace_id:
                agent_requests_traces.add(str(log.trace_id))

            # Check if this log record represents an actual tool invocation
            # Distinguish primary tool invocations from individual batch child items (:item)
            is_item_record = bool(log.action and log.action.endswith(":item"))
            is_tool_call = bool(log.tool_name) and (log.action or "").startswith("tool_call:") and not is_item_record

            if is_tool_call:
                total_tool_calls += 1
                if log.governance_decision == "allowed":
                    tool_allowed_count += 1
                    if log.execution_status == "success":
                        tool_success_count += 1
                    elif log.execution_status == "failed":
                        tool_failure_count += 1
                elif log.governance_decision in ("denied", "requires_approval"):
                    tool_denied_count += 1

                if log.governance_decision == "requires_approval" or log.tool_name in (
                    "submit_order",
                    "get_checkout_preview",
                    "place_order",
                ):
                    approval_required_count += 1

            # Legacy counts
            if log.governance_decision == "allowed":
                allowed_actions += 1
            elif log.governance_decision == "denied":
                denied_actions += 1

            if log.execution_status == "failed":
                failed_actions += 1
            elif log.execution_status == "success":
                successful_executions += 1

            if log.execution_duration_ms is not None:
                duration_sum += log.execution_duration_ms
                duration_count += 1

            t_name = log.tool_name or "conversational_reply"
            tool_usage_breakdown[t_name] = tool_usage_breakdown.get(t_name, 0) + 1

            a_id = log.agent_id or "unknown_agent"
            agent_activity[a_id] = agent_activity.get(a_id, 0) + 1

        total_agent_requests = len(agent_requests_traces) if agent_requests_traces else total_actions

        # Policy allow / denial rate against attempted tool calls
        policy_allow_rate = (
            (tool_allowed_count / total_tool_calls) * 100.0 if total_tool_calls > 0 else 100.0
        )
        policy_denial_rate = (
            (tool_denied_count / total_tool_calls) * 100.0 if total_tool_calls > 0 else 0.0
        )

        # Tool execution success rate calculated strictly against allowed actions (excluding security denials)
        tool_exec_success_rate = (
            (tool_success_count / tool_allowed_count) * 100.0 if tool_allowed_count > 0 else 100.0
        )
        tool_exec_failure_rate = (
            (tool_failure_count / tool_allowed_count) * 100.0 if tool_allowed_count > 0 else 0.0
        )

        # Legacy success rate and average duration
        success_rate = (
            (successful_executions / total_actions) * 100.0 if total_actions > 0 else 100.0
        )
        avg_duration_ms = (
            (duration_sum / duration_count) if duration_count > 0 else 0.0
        )

        # Query stage latencies from TraceSpan table
        avg_ai_inference_ms = 0.0
        avg_tool_execution_ms = 0.0
        avg_e2e_latency_ms = 0.0

        try:
            span_stats_stmt = (
                select(TraceSpan.name, func.avg(TraceSpan.duration_ms))
                .group_by(TraceSpan.name)
            )
            span_res = await db.execute(span_stats_stmt)
            for s_name, s_avg in span_res.fetchall():
                if s_name == "ai_inference":
                    avg_ai_inference_ms = round(float(s_avg or 0.0), 2)
                elif s_name == "tool_execution":
                    avg_tool_execution_ms = round(float(s_avg or 0.0), 2)
                elif s_name in ("agent.chat_turn", "chat_turn"):
                    avg_e2e_latency_ms = round(float(s_avg or 0.0), 2)
        except Exception:
            pass

        # If no trace spans stored yet, approximate tool execution latency from audit logs
        if avg_tool_execution_ms == 0.0:
            avg_tool_execution_ms = round(avg_duration_ms, 2)
        if avg_e2e_latency_ms == 0.0:
            avg_e2e_latency_ms = round(avg_duration_ms + avg_ai_inference_ms, 2)

        # Recent 20 logs for dashboard view
        recent_logs_models = all_logs[:20]
        recent_logs = [
            AuditLogResponse.model_validate(log) for log in recent_logs_models
        ]

        return DashboardMetrics(
            total_actions=total_actions,
            allowed_actions=allowed_actions,
            denied_actions=denied_actions,
            failed_actions=failed_actions,
            success_rate=round(success_rate, 2),
            avg_duration_ms=round(avg_duration_ms, 2),
            total_agent_requests=total_agent_requests,
            total_tool_calls=total_tool_calls,
            policy_allow_rate=round(policy_allow_rate, 2),
            policy_denial_rate=round(policy_denial_rate, 2),
            approval_required_actions=approval_required_count,
            tool_execution_success_rate=round(tool_exec_success_rate, 2),
            tool_execution_failure_rate=round(tool_exec_failure_rate, 2),
            avg_ai_inference_ms=avg_ai_inference_ms,
            avg_tool_execution_ms=avg_tool_execution_ms,
            avg_e2e_latency_ms=avg_e2e_latency_ms,
            recent_logs=recent_logs,
            tool_usage_breakdown=tool_usage_breakdown,
            agent_activity=agent_activity,
            jaeger_ui_url=settings.JAEGER_UI_URL,
        )


metrics_service = MetricsService()

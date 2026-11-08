import hashlib
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog
from app.observability.event_stream import event_stream_broker
from app.observability.tracing import get_current_trace_id


class AuditLogger:
    """
    Central audit logging service that records all governance evaluations,
    tool invocations, authorizations, and executions to persistent storage.
    Enforces automatic redaction of sensitive credentials.
    """

    REDACTED_KEYS = {
        "password",
        "hashed_password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
        "authorization",
        "credit_card",
        "card_number",
        "cvv",
    }

    def sanitize_metadata(self, data: Any) -> Any:
        """
        Recursively scrubs sensitive keys from metadata payloads.
        """
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                if any(secret_term in str(k).lower() for secret_term in self.REDACTED_KEYS):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = self.sanitize_metadata(v)
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_metadata(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self.sanitize_metadata(item) for item in data)
        return data

    async def log(
        self,
        db: AsyncSession,
        agent_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str],
        tool_name: Optional[str],
        action: str,
        target_resource: Optional[str],
        governance_decision: str,
        execution_status: str,
        denial_reason: Optional[str] = None,
        execution_duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[uuid.UUID] = None,
    ) -> AuditLog:
        """
        Writes an immutable audit log record to the database.
        """
        # Ensure trace ID is established
        resolved_trace = trace_id or get_current_trace_id()
        event_id = uuid.uuid4()

        # Sanitize metadata to prevent security leaks
        cleaned_metadata = self.sanitize_metadata(metadata or {})

        # Cryptographic Hash Chaining for Tamper-Evidence
        stmt = select(AuditLog.entry_hash).order_by(desc(AuditLog.timestamp), desc(AuditLog.id)).limit(1)
        res = await db.execute(stmt)
        latest_hash = res.scalar_one_or_none()
        prev_hash = latest_hash or "GENESIS_ROOT_HASH_00000000000000000000000000000000000000000000"

        hash_payload = f"{prev_hash}:{event_id}:{resolved_trace}:{action}:{governance_decision}:{execution_status}:{target_resource or ''}"
        entry_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        audit_entry = AuditLog(
            event_id=event_id,
            trace_id=resolved_trace,
            agent_id=str(agent_id) if agent_id else None,
            user_id=str(user_id) if user_id else None,
            session_id=str(session_id) if session_id else None,
            tool_name=str(tool_name) if tool_name else None,
            action=action,
            target_resource=target_resource,
            governance_decision=governance_decision,  # "allowed" or "denied"
            execution_status=execution_status,        # "success", "failed", "pending"
            denial_reason=denial_reason,
            execution_duration_ms=execution_duration_ms,
            entry_hash=entry_hash,
            prev_hash=prev_hash,
            metadata_payload=cleaned_metadata,
        )

        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)

        try:
            event_stream_broker.publish("audit_log", {
                "event_id": str(audit_entry.event_id),
                "trace_id": str(audit_entry.trace_id),
                "timestamp": audit_entry.timestamp.isoformat() if audit_entry.timestamp else None,
                "agent_id": audit_entry.agent_id,
                "tool_name": audit_entry.tool_name,
                "action": audit_entry.action,
                "governance_decision": audit_entry.governance_decision,
                "execution_status": audit_entry.execution_status,
                "execution_duration_ms": audit_entry.execution_duration_ms,
            })
        except Exception:
            pass

        return audit_entry

    async def verify_chain(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Cryptographically validates the hash chain of all audit log records.
        Detects unauthorized deletions, insertions, or in-place modifications.
        """
        stmt = select(AuditLog).order_by(AuditLog.timestamp, AuditLog.id)
        res = await db.execute(stmt)
        records = list(res.scalars().all())

        if not records:
            return {"valid": True, "total_records": 0, "message": "Audit chain empty."}

        expected_prev = "GENESIS_ROOT_HASH_00000000000000000000000000000000000000000000"
        for idx, rec in enumerate(records):
            if rec.prev_hash != expected_prev:
                return {
                    "valid": False,
                    "tampered_at_index": idx,
                    "event_id": str(rec.event_id),
                    "reason": f"Previous hash mismatch at record {idx}. Expected {expected_prev}, got {rec.prev_hash}",
                }
            recomputed = hashlib.sha256(
                f"{rec.prev_hash}:{rec.event_id}:{rec.trace_id}:{rec.action}:{rec.governance_decision}:{rec.execution_status}:{rec.target_resource or ''}".encode("utf-8")
            ).hexdigest()
            if rec.entry_hash != recomputed:
                return {
                    "valid": False,
                    "tampered_at_index": idx,
                    "event_id": str(rec.event_id),
                    "reason": f"Cryptographic entry hash violation at record {idx}. Data has been modified.",
                }
            expected_prev = rec.entry_hash

        return {
            "valid": True,
            "total_records": len(records),
            "latest_hash": records[-1].entry_hash if records else None,
            "message": "Cryptographic audit trail integrity fully verified.",
        }


audit_logger = AuditLogger()

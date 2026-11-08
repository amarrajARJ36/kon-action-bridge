import asyncio
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.observability.event_stream import event_stream_broker

# Context variable maintaining active trace ID and current parent span across async tasks
_trace_id_ctx: ContextVar[Optional[uuid.UUID]] = ContextVar("trace_id", default=None)
_parent_span_id_ctx: ContextVar[Optional[str]] = ContextVar("parent_span_id", default=None)
_spans_ctx: ContextVar[List[Dict[str, Any]]] = ContextVar("active_spans", default=[])

# In-memory LRU-like ring buffer for instant retrieval of recent traces
_recent_traces_cache: Dict[str, List[Dict[str, Any]]] = {}
_MAX_CACHE_TRACES = 200


def get_current_trace_id() -> uuid.UUID:
    """
    Returns the current active trace ID, or generates a new UUID.
    """
    current = _trace_id_ctx.get()
    if current is None:
        new_trace = uuid.uuid4()
        _trace_id_ctx.set(new_trace)
        _spans_ctx.set([])
        _parent_span_id_ctx.set(None)
        return new_trace
    return current


def set_current_trace_id(trace_id: uuid.UUID) -> None:
    """
    Binds an explicit trace ID into the async context.
    """
    _trace_id_ctx.set(trace_id)
    _spans_ctx.set([])
    _parent_span_id_ctx.set(None)


def clear_current_trace_id() -> None:
    """
    Clears the trace context variables.
    """
    _trace_id_ctx.set(None)
    _spans_ctx.set([])
    _parent_span_id_ctx.set(None)


def get_current_spans() -> List[Dict[str, Any]]:
    return list(_spans_ctx.get() or [])


class Span:
    """
    OpenTelemetry-standard distributed tracing span.
    Measures duration, start/end timestamps, parent-child relationships,
    attributes, and execution outcomes.
    """

    def __init__(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        trace_id: Optional[uuid.UUID] = None,
        parent_span_id: Optional[str] = None,
        service_name: str = "kon-action-bridge",
    ):
        self.name = name
        self.trace_id = trace_id or get_current_trace_id()
        self.span_id = uuid.uuid4().hex[:16]
        self.parent_span_id = parent_span_id or _parent_span_id_ctx.get()
        self.service_name = service_name
        self.attributes = attributes or {}
        self.events: List[Dict[str, Any]] = []
        self.start_perf: float = 0.0
        self.end_perf: float = 0.0
        self.duration_ms: float = 0.0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.status: str = "ok"
        self._prev_parent: Optional[str] = None

    def __enter__(self):
        self.start_perf = time.perf_counter()
        self.start_time = datetime.now(timezone.utc)
        self._prev_parent = _parent_span_id_ctx.get()
        _parent_span_id_ctx.set(self.span_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_perf = time.perf_counter()
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = round((self.end_perf - self.start_perf) * 1000.0, 2)
        if exc_val is not None:
            self.status = "error"
            self.attributes["error"] = str(exc_val)
            self.attributes["error.type"] = exc_type.__name__ if exc_type else "Exception"
        else:
            self.status = "ok"

        _parent_span_id_ctx.set(self._prev_parent)

        span_data = {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_id": str(self.trace_id),
            "name": self.name,
            "service_name": self.service_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
        }

        # Append to active context spans
        active = list(_spans_ctx.get() or [])
        active.append(span_data)
        _spans_ctx.set(active)

        # Store in cache
        tid_str = str(self.trace_id)
        if tid_str not in _recent_traces_cache:
            if len(_recent_traces_cache) >= _MAX_CACHE_TRACES:
                # Discard oldest key
                oldest_key = next(iter(_recent_traces_cache))
                _recent_traces_cache.pop(oldest_key, None)
            _recent_traces_cache[tid_str] = []
        _recent_traces_cache[tid_str].append(span_data)

        # Broadcast via SSE
        event_stream_broker.publish("trace_span", span_data)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)


def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    parent_span_id: Optional[str] = None,
) -> Span:
    """
    Syntactic sugar for creating and entering a distributed trace span.
    """
    return Span(name=name, attributes=attributes, parent_span_id=parent_span_id)


async def persist_trace_spans(db: AsyncSession, trace_id: uuid.UUID) -> None:
    """
    Persists all spans collected for the given trace into the database table,
    and dispatches OTLP payload asynchronously to Jaeger if available.
    """
    from app.models.governance import TraceSpan

    spans = get_current_spans()
    if not spans:
        tid_str = str(trace_id)
        spans = _recent_traces_cache.get(tid_str, [])

    if not spans:
        return

    try:
        for s in spans:
            st = (
                datetime.fromisoformat(s["start_time"])
                if s.get("start_time")
                else datetime.now(timezone.utc)
            )
            et = (
                datetime.fromisoformat(s["end_time"])
                if s.get("end_time")
                else datetime.now(timezone.utc)
            )
            db_span = TraceSpan(
                trace_id=uuid.UUID(s["trace_id"]),
                span_id=s["span_id"],
                parent_span_id=s.get("parent_span_id"),
                name=s["name"],
                service_name=s.get("service_name", "kon-action-bridge"),
                start_time=st,
                end_time=et,
                duration_ms=float(s.get("duration_ms", 0.0)),
                status=s.get("status", "ok"),
                attributes=s.get("attributes", {}),
                events=s.get("events", []),
            )
            db.add(db_span)
        await db.commit()
    except Exception:
        # Non-fatal persistence catch
        pass

    # Dispatch to Jaeger OTLP receiver in the background without blocking the request
    asyncio.create_task(_export_spans_to_jaeger(trace_id, spans))


async def _export_spans_to_jaeger(trace_id: uuid.UUID, spans: List[Dict[str, Any]]) -> None:
    """
    Converts collected spans to standard OpenTelemetry (OTLP/HTTP v1/traces JSON) format
    and delivers them to the local Jaeger collector.
    Fails silently if Jaeger is not running locally.
    """
    otlp_endpoint = f"{settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip('/')}/v1/traces"
    trace_hex = trace_id.hex

    otlp_spans = []
    for s in spans:
        st_ns = int(
            (
                datetime.fromisoformat(s["start_time"]).timestamp()
                if s.get("start_time")
                else time.time()
            )
            * 1e9
        )
        et_ns = int(
            (
                datetime.fromisoformat(s["end_time"]).timestamp()
                if s.get("end_time")
                else time.time()
            )
            * 1e9
        )

        otlp_attrs = []
        for k, v in (s.get("attributes") or {}).items():
            val_obj = {}
            if isinstance(v, bool):
                val_obj = {"boolValue": v}
            elif isinstance(v, int):
                val_obj = {"intValue": v}
            elif isinstance(v, float):
                val_obj = {"doubleValue": v}
            else:
                val_obj = {"stringValue": str(v)}
            otlp_attrs.append({"key": k, "value": val_obj})

        span_obj = {
            "traceId": trace_hex,
            "spanId": s["span_id"][:16],
            "name": s["name"],
            "kind": 1,  # SPAN_KIND_INTERNAL
            "startTimeUnixNano": str(st_ns),
            "endTimeUnixNano": str(et_ns),
            "attributes": otlp_attrs,
            "status": {
                "code": 1 if s.get("status") == "ok" else 2,  # 1=STATUS_CODE_OK, 2=STATUS_CODE_ERROR
                "message": s.get("attributes", {}).get("error", ""),
            },
        }
        if s.get("parent_span_id"):
            span_obj["parentSpanId"] = s["parent_span_id"][:16]
        otlp_spans.append(span_obj)

    otlp_payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {"stringValue": settings.OTEL_SERVICE_NAME},
                        }
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "kon.action_bridge"},
                        "spans": otlp_spans,
                    }
                ],
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            await client.post(otlp_endpoint, json=otlp_payload)
    except Exception:
        # Expected if Jaeger container is not running
        pass


def get_cached_trace(trace_id_str: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve trace spans from memory cache."""
    return _recent_traces_cache.get(trace_id_str)

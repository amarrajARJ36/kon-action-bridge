import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Set
from fastapi import Request


class EventStreamBroker:
    """
    Lightweight, in-memory Server-Sent Events (SSE) pub/sub broker.
    Streams real-time audit logs, governance decisions, trace spans,
    and telemetry metrics to connected admin dashboards without polling delays.
    """

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()

    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Broadcasts an event payload to all active SSE subscribers.
        Non-blocking and safe against full or closed queues.
        """
        payload = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        dead_queues = set()
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead_queues.add(q)
            except Exception:
                dead_queues.add(q)

        for dq in dead_queues:
            self._subscribers.discard(dq)

    async def subscribe(self, request: Request) -> AsyncGenerator[str, None]:
        """
        Async generator yielding SSE data frames to an HTTP client.
        Automatically unregisters on client disconnection.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)

        try:
            # Send initial connection acknowledgment
            yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'subscribers': len(self._subscribers)})}\n\n"
            await asyncio.sleep(0.01)

            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    # Wait for next event or send keep-alive ping after 15s
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: {payload['type']}\ndata: {json.dumps(payload['data'])}\n\n"
                    await asyncio.sleep(0.01)
                except asyncio.TimeoutError:
                    # Keep-alive comment
                    yield ": ping\n\n"
                    await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            pass
        finally:
            self._subscribers.discard(queue)


event_stream_broker = EventStreamBroker()

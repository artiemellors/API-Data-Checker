"""Server-Sent Events endpoint — streams live scan progress to the browser."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stream"])

# How long to wait (seconds) before giving up if the scan never emits "done"
SSE_TIMEOUT_S = 600


@router.get("/scans/{scan_id}/events")
async def scan_events(scan_id: str) -> EventSourceResponse:
    """
    Stream scan progress events via Server-Sent Events.

    The Celery worker publishes JSON objects to the Redis channel
    ``scan:{scan_id}``. This endpoint subscribes and forwards them.

    The stream closes automatically when the worker emits
    ``{"event": "done"}`` or after SSE_TIMEOUT_S seconds.
    """
    import redis.asyncio as aioredis

    async def generator():
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"scan:{scan_id}")
        try:
            deadline = asyncio.get_event_loop().time() + SSE_TIMEOUT_S
            async for raw in pubsub.listen():
                if asyncio.get_event_loop().time() > deadline:
                    yield {"data": json.dumps({"event": "error", "message": "Scan timed out"})}
                    break
                if raw["type"] != "message":
                    continue
                data = raw["data"]
                yield {"data": data}
                try:
                    parsed = json.loads(data)
                    if parsed.get("event") == "done":
                        break
                except json.JSONDecodeError:
                    pass
        except Exception as exc:
            logger.warning("SSE stream error for scan %s: %s", scan_id, exc)
            yield {"data": json.dumps({"event": "error", "message": str(exc)})}
        finally:
            try:
                await pubsub.unsubscribe(f"scan:{scan_id}")
                await r.aclose()
            except Exception:
                pass

    return EventSourceResponse(generator())

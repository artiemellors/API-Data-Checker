"""
Celery application and scan task.

The scan pipeline runs inside an asyncio event loop driven by asyncio.run().
Progress events are published to the Redis channel  scan:{scan_id}
and consumed by the SSE endpoint in routers/stream.py.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import redis as sync_redis
from celery import Celery

from .config import settings

logger = logging.getLogger(__name__)

# ─── Celery app ───────────────────────────────────────────────────────────────

celery_app = Celery(
    "api_checker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,  # one task at a time per worker process
    task_acks_late=True,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _publish(scan_id: str, event: dict) -> None:
    """Synchronously publish a progress event to Redis pub/sub."""
    try:
        r = sync_redis.from_url(settings.redis_url, decode_responses=True)
        r.publish(f"scan:{scan_id}", json.dumps(event))
        r.close()
    except Exception as exc:
        logger.warning("Failed to publish event for scan %s: %s", scan_id, exc)


def _extract_domain(url: str) -> str:
    try:
        import tldextract

        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
    except Exception:
        from urllib.parse import urlparse

        return urlparse(url).netloc


# ─── Task ─────────────────────────────────────────────────────────────────────


@celery_app.task(bind=True, name="api_checker.tasks.scan_retailer", max_retries=0)
def scan_retailer(
    self,
    scan_id: str,
    url: str,
    max_pages: int = 10,
    probe: bool = True,
) -> dict:
    """Entry point: Celery calls this synchronously; we bridge to async internally."""
    return asyncio.run(_run_scan(scan_id, url, max_pages, probe))


async def _run_scan(
    scan_id: str,
    url: str,
    max_pages: int,
    probe: bool,
) -> dict:
    """Full async scan pipeline."""
    from .storage.db import DatabaseManager, RetailerRepository

    db = DatabaseManager()
    await db.initialize()

    errors: list[str] = []
    endpoints = []
    services = []
    probes = []

    def emit(event: dict) -> None:
        _publish(scan_id, event)

    async with db.session() as session:
        repo = RetailerRepository(session)

        # ── Mark running ──────────────────────────────────────────────────────
        await repo.update_scan_status(scan_id, "running", started_at=datetime.utcnow())

    emit({"event": "progress", "message": "Starting scan…", "step": 0, "total": 4})

    try:
        # ── Phase 1: Browser traffic capture ─────────────────────────────────
        emit({"event": "progress", "message": "Capturing browser traffic…", "step": 1, "total": 4})
        try:
            from .discovery.browser import SiteCrawler, BrowserManager

            async with BrowserManager() as bm:
                crawler = SiteCrawler(url, bm, scan_id=scan_id, max_pages=max_pages)
                endpoints = await crawler.crawl()

            emit(
                {
                    "event": "progress",
                    "message": f"Captured {len(endpoints)} API endpoints",
                    "step": 1,
                    "total": 4,
                }
            )
        except Exception as exc:
            logger.warning("Browser capture failed: %s", exc)
            errors.append(f"Browser capture: {exc}")

        # ── Phase 2: Static JS analysis ───────────────────────────────────────
        emit({"event": "progress", "message": "Analysing JavaScript bundles…", "step": 2, "total": 4})
        js_extractions: dict[str, list[str]] = {}
        try:
            from .discovery.static_analysis import download_js_bundles, extract_from_js
            import httpx

            async with httpx.AsyncClient(
                timeout=settings.http_timeout_s,
                follow_redirects=True,
                headers={"User-Agent": settings.user_agent},
            ) as client:
                bundles = await download_js_bundles(url, client)

            for _script_url, content in bundles:
                for key, values in extract_from_js(content).items():
                    js_extractions.setdefault(key, []).extend(values)
        except Exception as exc:
            logger.warning("Static analysis failed: %s", exc)
            errors.append(f"Static analysis: {exc}")

        # ── Phase 3: Fingerprint matching ─────────────────────────────────────
        emit({"event": "progress", "message": "Fingerprinting third-party services…", "step": 3, "total": 4})
        try:
            from .discovery.fingerprints import FingerprintMatcher, GenericApiRecognizer

            matcher = FingerprintMatcher()
            services = matcher.match(endpoints, js_extractions)

            recognizer = GenericApiRecognizer()
            known_urls = {svc.service_name for svc in services}
            for ep in endpoints:
                result = recognizer.classify(ep)
                if result and result.service_name not in known_urls:
                    services.append(result)

            for svc in services:
                emit(
                    {
                        "event": "service_found",
                        "service_name": svc.service_name,
                        "category": svc.category,
                        "message": f"Found {svc.service_name} ({svc.category})",
                    }
                )
        except Exception as exc:
            logger.warning("Fingerprinting failed: %s", exc)
            errors.append(f"Fingerprinting: {exc}")

        # ── Phase 4: API probing ───────────────────────────────────────────────
        if probe and services:
            emit({"event": "progress", "message": "Probing discovered APIs…", "step": 4, "total": 4})
            try:
                from .probing.prober import ProbingOrchestrator

                orchestrator = ProbingOrchestrator()
                probe_results, probe_errors = await orchestrator.run(services)
                probes.extend(probe_results)
                errors.extend(probe_errors)

                for pr in probe_results:
                    emit(
                        {
                            "event": "probe_complete",
                            "service_name": pr.service_name,
                            "fields_found": len(pr.data_fields_found),
                            "message": (
                                f"Probed {pr.service_name}: "
                                f"{len(pr.data_fields_found)} fields found"
                            ),
                        }
                    )
            except Exception as exc:
                logger.warning("Probing failed: %s", exc)
                errors.append(f"Probing: {exc}")

        # ── Persist results ───────────────────────────────────────────────────
        async with db.session() as session:
            repo = RetailerRepository(session)

            if endpoints:
                await repo.save_endpoints(endpoints)

            service_id_map: dict[str, int] = {}
            if services:
                saved_services = await repo.save_services(services)
                service_id_map = {s.service_name: s.id for s in saved_services}

            if probes:
                await repo.save_probe_results(probes, service_id_map)

            await repo.update_scan_completed(
                scan_id,
                endpoints_discovered=len(endpoints),
                services_found=len(services),
                probes_completed=len(probes),
                errors=errors,
            )

    except Exception as exc:
        logger.exception("Scan %s failed: %s", scan_id, exc)
        errors.append(str(exc))
        async with db.session() as session:
            repo = RetailerRepository(session)
            await repo.mark_scan_failed(scan_id, errors)
        emit({"event": "error", "message": str(exc)})
    finally:
        await db.close()

    emit({"event": "done", "services_found": len(services), "message": "Scan complete"})
    return {"scan_id": scan_id, "services_found": len(services)}

"""Scan submission and listing endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

import tldextract
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models import BatchScanRequest, ScanRequest, ScanResponse
from ..storage.db import db_manager
from ..tasks import celery_app

router = APIRouter(tags=["scans"])


def _domain(url: str) -> str:
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain


# ── Single scan ───────────────────────────────────────────────────────────────


@router.post("/scans", response_model=ScanResponse, status_code=201)
async def create_scan(body: ScanRequest) -> ScanResponse:
    """Submit a URL for scanning. Returns immediately with a scan_id."""
    scan_id = str(uuid.uuid4())
    domain = _domain(body.url)

    async with db_manager.session() as session:
        from ..storage.db import RetailerRepository

        repo = RetailerRepository(session)
        scan = await repo.create_scan(
            scan_id=scan_id,
            url=body.url,
            domain=domain,
            max_pages=body.max_pages,
            probe=body.probe,
        )

    # Dispatch to Celery worker
    celery_app.send_task(
        "api_checker.tasks.scan_retailer",
        args=[scan_id, body.url, body.max_pages, body.probe],
    )

    return ScanResponse(
        scan_id=scan_id,
        url=body.url,
        domain=domain,
        status="pending",
        max_pages=body.max_pages,
        probe=body.probe,
    )


# ── Batch scan ────────────────────────────────────────────────────────────────


class BatchScanResponse(BaseModel):
    scan_ids: list[str]
    submitted: int


@router.post("/scans/batch", response_model=BatchScanResponse, status_code=201)
async def create_batch_scan(body: BatchScanRequest) -> BatchScanResponse:
    """Submit multiple URLs for scanning in one request."""
    scan_ids: list[str] = []

    async with db_manager.session() as session:
        from ..storage.db import RetailerRepository

        repo = RetailerRepository(session)
        for url in body.urls:
            scan_id = str(uuid.uuid4())
            domain = _domain(url)
            await repo.create_scan(
                scan_id=scan_id,
                url=url,
                domain=domain,
                max_pages=body.max_pages,
                probe=body.probe,
            )
            scan_ids.append(scan_id)

    for scan_id, url in zip(scan_ids, body.urls):
        celery_app.send_task(
            "api_checker.tasks.scan_retailer",
            args=[scan_id, url, body.max_pages, body.probe],
        )

    return BatchScanResponse(scan_ids=scan_ids, submitted=len(scan_ids))


# ── List & detail ─────────────────────────────────────────────────────────────


@router.get("/scans", response_model=list[ScanResponse])
async def list_scans() -> list[ScanResponse]:
    """Return all scans ordered by start time (newest first)."""
    async with db_manager.session() as session:
        from ..storage.db import RetailerRepository

        repo = RetailerRepository(session)
        scans = await repo.list_scans()
    return [ScanResponse.model_validate(s) for s in scans]


@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str) -> ScanResponse:
    """Return the current state of a single scan."""
    async with db_manager.session() as session:
        from ..storage.db import RetailerRepository

        repo = RetailerRepository(session)
        scan = await repo.get_scan(scan_id)

    if scan is None:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id!r} not found")

    return ScanResponse.model_validate(scan)

"""Endpoints that return discovered services and probe results for a scan."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import ProbeResponse, ServiceResponse
from ..storage.db import db_manager

router = APIRouter(tags=["results"])


@router.get("/scans/{scan_id}/services", response_model=list[ServiceResponse])
async def get_services(scan_id: str) -> list[ServiceResponse]:
    """Return all third-party services discovered in this scan."""
    async with db_manager.session() as session:
        from ..storage.db import RetailerRepository

        repo = RetailerRepository(session)
        scan = await repo.get_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id!r} not found")
        services = await repo.get_services(scan_id)

    return [ServiceResponse.model_validate(s) for s in services]


@router.get("/scans/{scan_id}/probes", response_model=list[ProbeResponse])
async def get_probes(scan_id: str) -> list[ProbeResponse]:
    """Return all API probe results for this scan."""
    async with db_manager.session() as session:
        from ..storage.db import RetailerRepository

        repo = RetailerRepository(session)
        scan = await repo.get_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id!r} not found")
        probes = await repo.get_probes(scan_id)

    return [ProbeResponse.model_validate(p) for p in probes]

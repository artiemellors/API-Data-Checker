"""Export endpoints — download scan results as JSON or CSV."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..reporting.exporter import CsvExporter, JsonExporter
from ..storage.db import db_manager

router = APIRouter(tags=["export"])


@router.get("/scans/{scan_id}/export.json")
async def export_json(scan_id: str) -> Response:
    """Download full scan results as a JSON file."""
    async with db_manager.session() as session:
        from ..storage.db import RetailerRepository

        repo = RetailerRepository(session)
        scan = await repo.get_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id!r} not found")
        services = await repo.get_services(scan_id)
        probes = await repo.get_probes(scan_id)

    content = JsonExporter.export(scan, services, probes)
    filename = f"{scan.domain}_{scan_id[:8]}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/scans/{scan_id}/export.csv")
async def export_csv(scan_id: str) -> Response:
    """Download flat scan results as a CSV file (Excel-compatible UTF-8 BOM)."""
    async with db_manager.session() as session:
        from ..storage.db import RetailerRepository

        repo = RetailerRepository(session)
        scan = await repo.get_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id!r} not found")
        services = await repo.get_services(scan_id)
        probes = await repo.get_probes(scan_id)

    content = CsvExporter.export(scan, services, probes)
    filename = f"{scan.domain}_{scan_id[:8]}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

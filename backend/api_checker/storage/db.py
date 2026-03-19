"""Database manager and repository pattern for all persistence operations."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings
from ..models import DiscoveredEndpoint, ProbedResult, ThirdPartyService
from .models import Base, DiscoveredEndpointORM, ProbedResultORM, ScanORM, ThirdPartyServiceORM


class DatabaseManager:
    def __init__(self, db_path: str | None = None) -> None:
        path = db_path or settings.db_path
        abs_path = os.path.abspath(path)
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{abs_path}", echo=False, future=True
        )
        self._session_factory = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def initialize(self) -> None:
        """Create all tables and enable WAL mode."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("PRAGMA journal_mode=WAL"))

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        await self.engine.dispose()


class RetailerRepository:
    """All DB operations for a single async session."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Scans ─────────────────────────────────────────────────────────────────

    async def create_scan(
        self, scan_id: str, url: str, domain: str, max_pages: int, probe: bool
    ) -> ScanORM:
        scan = ScanORM(
            id=scan_id, url=url, domain=domain, max_pages=max_pages, probe=probe
        )
        self.session.add(scan)
        await self.session.flush()
        return scan

    async def get_scan(self, scan_id: str) -> ScanORM | None:
        result = await self.session.get(ScanORM, scan_id)
        return result

    async def list_scans(self) -> list[ScanORM]:
        result = await self.session.execute(
            select(ScanORM).order_by(ScanORM.started_at.desc().nullslast())
        )
        return list(result.scalars().all())

    async def update_scan_status(
        self,
        scan_id: str,
        status: str,
        started_at: datetime | None = None,
        errors: list[str] | None = None,
    ) -> None:
        scan = await self.get_scan(scan_id)
        if scan is None:
            return
        scan.status = status
        if started_at is not None:
            scan.started_at = started_at
        if errors is not None:
            scan.errors = errors

    async def update_scan_completed(
        self,
        scan_id: str,
        endpoints_discovered: int,
        services_found: int,
        probes_completed: int,
        errors: list[str],
    ) -> None:
        scan = await self.get_scan(scan_id)
        if scan is None:
            return
        scan.status = "completed"
        scan.completed_at = datetime.utcnow()
        scan.endpoints_discovered = endpoints_discovered
        scan.services_found = services_found
        scan.probes_completed = probes_completed
        scan.errors = errors

    async def mark_scan_failed(self, scan_id: str, errors: list[str]) -> None:
        scan = await self.get_scan(scan_id)
        if scan is None:
            return
        scan.status = "failed"
        scan.completed_at = datetime.utcnow()
        scan.errors = errors

    # ── Endpoints ─────────────────────────────────────────────────────────────

    async def save_endpoints(self, endpoints: list[DiscoveredEndpoint]) -> None:
        for ep in endpoints:
            orm = DiscoveredEndpointORM(
                scan_id=ep.scan_id,
                url=ep.url,
                method=ep.method,
                request_headers=ep.request_headers,
                request_body=ep.request_body,
                response_status=ep.response_status,
                response_body_sample=ep.response_body_sample,
                source=ep.source,
            )
            self.session.add(orm)

    # ── Services ──────────────────────────────────────────────────────────────

    async def save_services(
        self, services: list[ThirdPartyService]
    ) -> list[ThirdPartyServiceORM]:
        saved = []
        for svc in services:
            orm = ThirdPartyServiceORM(
                scan_id=svc.scan_id,
                service_name=svc.service_name,
                category=svc.category,
                confidence=svc.confidence,
                evidence=svc.evidence,
                extracted_keys=svc.extracted_keys,
            )
            self.session.add(orm)
            await self.session.flush()
            saved.append(orm)
        return saved

    async def get_services(self, scan_id: str) -> list[ThirdPartyServiceORM]:
        result = await self.session.execute(
            select(ThirdPartyServiceORM).where(ThirdPartyServiceORM.scan_id == scan_id)
        )
        return list(result.scalars().all())

    # ── Probes ────────────────────────────────────────────────────────────────

    async def save_probe_results(
        self,
        probes: list[ProbedResult],
        service_id_map: dict[str, int],
    ) -> None:
        for pr in probes:
            orm = ProbedResultORM(
                scan_id=pr.scan_id,
                service_id=service_id_map.get(pr.service_name),
                service_name=pr.service_name,
                probe_url=pr.probe_url,
                probe_method=pr.probe_method,
                probe_payload=pr.probe_payload,
                response_status=pr.response_status,
                response_body=pr.response_body,
                data_fields_found=pr.data_fields_found,
                sample_records=pr.sample_records,
                error=pr.error,
            )
            self.session.add(orm)

    async def get_probes(self, scan_id: str) -> list[ProbedResultORM]:
        result = await self.session.execute(
            select(ProbedResultORM).where(ProbedResultORM.scan_id == scan_id)
        )
        return list(result.scalars().all())

    async def has_recent_scan(self, domain: str, hours: int = 24) -> bool:
        """Return True if a completed scan for this domain exists within `hours`."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = await self.session.execute(
            select(ScanORM).where(
                ScanORM.domain == domain,
                ScanORM.status == "completed",
                ScanORM.completed_at >= cutoff,
            )
        )
        return result.scalar_one_or_none() is not None


# Module-level singleton — initialised in the FastAPI lifespan hook
db_manager = DatabaseManager()

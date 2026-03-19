"""SQLAlchemy ORM models — one table per domain entity."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ScanORM(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    max_pages: Mapped[int] = mapped_column(Integer, default=10)
    probe: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    endpoints_discovered: Mapped[int] = mapped_column(Integer, default=0)
    services_found: Mapped[int] = mapped_column(Integer, default=0)
    probes_completed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSON, default=list)

    services: Mapped[List["ThirdPartyServiceORM"]] = relationship(
        "ThirdPartyServiceORM", back_populates="scan", cascade="all, delete-orphan"
    )
    probes: Mapped[List["ProbedResultORM"]] = relationship(
        "ProbedResultORM", back_populates="scan", cascade="all, delete-orphan"
    )
    endpoints: Mapped[List["DiscoveredEndpointORM"]] = relationship(
        "DiscoveredEndpointORM", back_populates="scan", cascade="all, delete-orphan"
    )


class DiscoveredEndpointORM(Base):
    __tablename__ = "discovered_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(String, ForeignKey("scans.id"), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String, default="GET")
    request_headers: Mapped[dict] = mapped_column(JSON, default=dict)
    request_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body_sample: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String, default="browser")

    scan: Mapped["ScanORM"] = relationship("ScanORM", back_populates="endpoints")


class ThirdPartyServiceORM(Base):
    __tablename__ = "third_party_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(String, ForeignKey("scans.id"), nullable=False)
    service_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    extracted_keys: Mapped[dict] = mapped_column(JSON, default=dict)

    scan: Mapped["ScanORM"] = relationship("ScanORM", back_populates="services")
    probes: Mapped[List["ProbedResultORM"]] = relationship(
        "ProbedResultORM", back_populates="service"
    )


class ProbedResultORM(Base):
    __tablename__ = "probed_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(String, ForeignKey("scans.id"), nullable=False)
    service_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("third_party_services.id"), nullable=True
    )
    service_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    probe_url: Mapped[str] = mapped_column(String, nullable=False)
    probe_method: Mapped[str] = mapped_column(String, default="GET")
    probe_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_fields_found: Mapped[list] = mapped_column(JSON, default=list)
    sample_records: Mapped[list] = mapped_column(JSON, default=list)
    probed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    scan: Mapped["ScanORM"] = relationship("ScanORM", back_populates="probes")
    service: Mapped[Optional["ThirdPartyServiceORM"]] = relationship(
        "ThirdPartyServiceORM", back_populates="probes"
    )

"""
Pydantic models used throughout the application.

Two groups:
  1. API request/response models  — used by FastAPI routers
  2. Internal data contract models — used by the discovery/probing pipeline
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


# ─── API Request / Response Models ───────────────────────────────────────────


class ScanRequest(BaseModel):
    url: str
    max_pages: int = Field(default=10, ge=1, le=50)
    probe: bool = True

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class BatchScanRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=50)
    max_pages: int = Field(default=10, ge=1, le=50)
    probe: bool = True


class ScanResponse(BaseModel):
    scan_id: str
    url: str
    domain: str
    status: Literal["pending", "running", "completed", "failed"]
    max_pages: int
    probe: bool
    started_at: datetime | None = None
    completed_at: datetime | None = None
    endpoints_discovered: int = 0
    services_found: int = 0
    probes_completed: int = 0
    errors: list[str] = []

    model_config = {"from_attributes": True}


class ServiceResponse(BaseModel):
    id: int
    scan_id: str
    service_name: str
    category: str
    confidence: float
    evidence: list[str]
    extracted_keys: dict[str, str]

    model_config = {"from_attributes": True}


class ProbeResponse(BaseModel):
    id: int
    scan_id: str
    service_id: int | None = None
    service_name: str | None = None
    probe_url: str
    probe_method: str
    probe_payload: dict | None = None
    response_status: int | None = None
    data_fields_found: list[str] = []
    sample_records: list[dict] = []
    probed_at: datetime
    error: str | None = None

    model_config = {"from_attributes": True}


# ─── Internal Data Contract Models ───────────────────────────────────────────


class DiscoveredEndpoint(BaseModel):
    """A single XHR/fetch API call observed during browser traffic capture."""

    scan_id: str
    url: str
    method: str = "GET"
    request_headers: dict[str, str] = {}
    request_body: str | None = None
    response_status: int | None = None
    response_body_sample: str | None = None  # capped at 4 KB
    source: Literal["browser", "static", "sitemap"] = "browser"

    @field_validator("response_body_sample")
    @classmethod
    def cap_sample(cls, v: str | None) -> str | None:
        if v and len(v) > 4096:
            return v[:4096]
        return v


class ThirdPartyService(BaseModel):
    """A third-party service identified on a retailer website."""

    scan_id: str
    service_name: str
    category: str  # search | reviews | recommendations | analytics | chat | loyalty | …
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    evidence: list[str] = []
    extracted_keys: dict[str, str] = {}  # api_key, app_id, index_name, …


class ProbedResult(BaseModel):
    """Result of probing a discovered third-party API."""

    scan_id: str
    service_name: str
    probe_url: str
    probe_method: str = "GET"
    probe_payload: dict | None = None
    response_status: int | None = None
    response_body: str | None = None
    data_fields_found: list[str] = []
    sample_records: list[dict] = []  # up to 3 example records
    error: str | None = None


class ScanProgressEvent(BaseModel):
    """A progress event emitted during a scan (used for SSE streaming)."""

    event: Literal["progress", "service_found", "probe_complete", "error", "done"]
    message: str = ""
    service_name: str | None = None
    category: str | None = None
    fields_found: int | None = None
    services_found: int | None = None
    step: int | None = None
    total: int | None = None

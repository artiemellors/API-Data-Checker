"""
Generic API prober and probing orchestrator.

GenericProber      — fires GET/POST requests and extracts data summaries
ProbingOrchestrator — dispatches to service-specific adapters (or GenericProber)
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import settings
from ..models import ProbedResult, ThirdPartyService

logger = logging.getLogger(__name__)


# ─── GenericProber ────────────────────────────────────────────────────────────


class GenericProber:
    """Probes any URL and returns a structured ProbedResult."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def probe(
        self,
        service: ThirdPartyService,
        endpoint_url: str,
        method: str = "GET",
        params: dict | None = None,
        payload: dict | None = None,
        extra_headers: dict | None = None,
    ) -> ProbedResult:
        headers = {"User-Agent": settings.user_agent}
        if extra_headers:
            headers.update(extra_headers)

        try:
            response = await self._send(
                method=method,
                url=endpoint_url,
                params=params,
                json_body=payload,
                headers=headers,
            )
            body = response.text
            data_fields, samples = self._extract_summary(body)
            return ProbedResult(
                scan_id=service.scan_id,
                service_name=service.service_name,
                probe_url=endpoint_url,
                probe_method=method,
                probe_payload=payload,
                response_status=response.status_code,
                response_body=body[:16_384],  # cap at 16 KB
                data_fields_found=data_fields,
                sample_records=samples,
            )
        except Exception as exc:
            logger.warning("Probe failed for %s @ %s: %s", service.service_name, endpoint_url, exc)
            return ProbedResult(
                scan_id=service.scan_id,
                service_name=service.service_name,
                probe_url=endpoint_url,
                probe_method=method,
                probe_payload=payload,
                error=str(exc),
            )

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(settings.http_max_retries),
        reraise=True,
    )
    async def _send(
        self,
        method: str,
        url: str,
        params: dict | None,
        json_body: dict | None,
        headers: dict,
    ) -> httpx.Response:
        resp = await self.client.request(
            method,
            url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=settings.http_timeout_s,
        )
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            await asyncio.sleep(retry_after)
            resp.raise_for_status()
        return resp

    @staticmethod
    def _extract_summary(body: str) -> tuple[list[str], list[dict]]:
        """Return (top-level keys, up to 3 sample records)."""
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return [], []

        if isinstance(data, dict):
            fields = list(data.keys())
            # Look for a nested array to extract samples from
            samples = []
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    samples = v[:3]
                    break
            return fields, samples

        if isinstance(data, list) and data:
            if isinstance(data[0], dict):
                return list(data[0].keys()), data[:3]
            return [], []

        return [], []


# ─── ProbingOrchestrator ──────────────────────────────────────────────────────


class ProbingOrchestrator:
    """
    Dispatches each ThirdPartyService to the correct adapter (or GenericProber)
    and runs probes concurrently, bounded by settings.http_concurrency.
    """

    async def run(
        self, services: list[ThirdPartyService]
    ) -> tuple[list[ProbedResult], list[str]]:
        from .adapters import ADAPTER_REGISTRY

        results: list[ProbedResult] = []
        errors: list[str] = []
        sem = asyncio.Semaphore(settings.http_concurrency)

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.http_timeout_s,
            headers={"User-Agent": settings.user_agent},
        ) as client:
            prober = GenericProber(client)

            async def probe_one(svc: ThirdPartyService) -> None:
                async with sem:
                    try:
                        adapter_cls = ADAPTER_REGISTRY.get(svc.service_name)
                        if adapter_cls:
                            adapter = adapter_cls(prober)
                            probe_results = await adapter.probe(svc)
                        else:
                            # Generic probe: re-use the endpoint URL from evidence
                            evidence_urls = [
                                e.removeprefix("URL: ")
                                for e in svc.evidence
                                if e.startswith("URL: ")
                            ]
                            if evidence_urls:
                                pr = await prober.probe(svc, evidence_urls[0])
                                probe_results = [pr]
                            else:
                                probe_results = []

                        results.extend(probe_results)
                    except Exception as exc:
                        msg = f"{svc.service_name}: {exc}"
                        logger.warning("Probe error: %s", msg)
                        errors.append(msg)

            await asyncio.gather(*[probe_one(svc) for svc in services])

        return results, errors

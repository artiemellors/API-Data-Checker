"""Yotpo reviews adapter."""

from __future__ import annotations

from ..prober import GenericProber
from ...models import ProbedResult, ThirdPartyService

YOTPO_BASE = "https://api.yotpo.com"


class YotpoAdapter:
    def __init__(self, prober: GenericProber) -> None:
        self.prober = prober

    async def probe(self, service: ThirdPartyService) -> list[ProbedResult]:
        app_key = service.extracted_keys.get("app_key", "")
        if not app_key:
            return []

        results: list[ProbedResult] = []

        pr = await self.prober.probe(
            service,
            f"{YOTPO_BASE}/v1/apps/{app_key}/reviews",
            params={"count": 3, "page": 1},
        )
        results.append(pr)
        return results

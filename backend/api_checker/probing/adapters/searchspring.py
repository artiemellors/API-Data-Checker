"""Searchspring adapter."""

from __future__ import annotations

from ..prober import GenericProber
from ...models import ProbedResult, ThirdPartyService

SS_BASE = "https://{site_id}.a.searchspring.io/api/search/search.json"


class SearchspringAdapter:
    def __init__(self, prober: GenericProber) -> None:
        self.prober = prober

    async def probe(self, service: ThirdPartyService) -> list[ProbedResult]:
        site_id = service.extracted_keys.get("site_id", "")
        if not site_id:
            return []

        url = f"https://{site_id}.a.searchspring.io/api/search/search.json"
        pr = await self.prober.probe(
            service,
            url,
            params={"q": "shirt", "siteId": site_id, "resultsFormat": "native"},
        )
        return [pr]

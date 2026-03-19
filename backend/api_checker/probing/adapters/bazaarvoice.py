"""Bazaarvoice reviews adapter."""

from __future__ import annotations

from ..prober import GenericProber
from ...models import ProbedResult, ThirdPartyService

BV_API_BASE = "https://api.bazaarvoice.com/data"
BV_API_VERSION = "5.4"


class BazaarvoiceAdapter:
    def __init__(self, prober: GenericProber) -> None:
        self.prober = prober

    async def probe(self, service: ThirdPartyService) -> list[ProbedResult]:
        passkey = service.extracted_keys.get("passkey", "")
        if not passkey:
            return []

        results: list[ProbedResult] = []

        # Reviews
        reviews_pr = await self.prober.probe(
            service,
            f"{BV_API_BASE}/reviews.json",
            params={
                "passkey": passkey,
                "apiversion": BV_API_VERSION,
                "Filter": "contentlocale:en_US",
                "Limit": "3",
            },
        )
        results.append(reviews_pr)

        # Statistics
        stats_pr = await self.prober.probe(
            service,
            f"{BV_API_BASE}/statistics.json",
            params={
                "passkey": passkey,
                "apiversion": BV_API_VERSION,
                "Filter": "contentlocale:en_US",
            },
        )
        results.append(stats_pr)

        return results

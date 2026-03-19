"""PowerReviews adapter."""

from __future__ import annotations

from ..prober import GenericProber
from ...models import ProbedResult, ThirdPartyService

PR_BASE = "https://readservices-b2c.powerreviews.com"


class PowerReviewsAdapter:
    def __init__(self, prober: GenericProber) -> None:
        self.prober = prober

    async def probe(self, service: ThirdPartyService) -> list[ProbedResult]:
        api_key = service.extracted_keys.get("api_key", "")
        merchant_id = service.extracted_keys.get("merchant_id", "")
        if not api_key:
            return []

        results: list[ProbedResult] = []
        params: dict = {"apikey": api_key}
        if merchant_id:
            params["merchant_id"] = merchant_id

        pr = await self.prober.probe(
            service,
            f"{PR_BASE}/m/{merchant_id or '0'}/reviews",
            params=params,
        )
        results.append(pr)
        return results

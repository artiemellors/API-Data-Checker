"""constructor.io search and recommendations adapter."""

from __future__ import annotations

from ..prober import GenericProber
from ...models import ProbedResult, ThirdPartyService

BASE_URL = "https://ac.cnstrc.com"
CLIENT_VERSION = "ciojs-client-2.30.0"
PROBE_TERMS = ["shirt", "shoes", "pants"]


class ConstructorIOAdapter:
    def __init__(self, prober: GenericProber) -> None:
        self.prober = prober

    async def probe(self, service: ThirdPartyService) -> list[ProbedResult]:
        api_key = service.extracted_keys.get("api_key", "")
        if not api_key:
            return []

        results: list[ProbedResult] = []

        # Search probe
        for term in PROBE_TERMS:
            url = f"{BASE_URL}/search/{term}"
            pr = await self.prober.probe(
                service,
                url,
                params={"key": api_key, "c": CLIENT_VERSION, "num_results_per_page": 3},
            )
            results.append(pr)
            if pr.response_status and pr.response_status < 400:
                break  # one successful search is enough

        # Recommendations probe (best-sellers / featured)
        rec_url = f"{BASE_URL}/recommendations/v1/pods"
        pr = await self.prober.probe(
            service,
            rec_url,
            params={"key": api_key, "c": CLIENT_VERSION},
        )
        results.append(pr)

        return results

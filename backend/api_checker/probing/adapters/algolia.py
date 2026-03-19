"""Algolia search adapter."""

from __future__ import annotations

from ..prober import GenericProber
from ...models import ProbedResult, ThirdPartyService


class AlgoliaAdapter:
    def __init__(self, prober: GenericProber) -> None:
        self.prober = prober

    async def probe(self, service: ThirdPartyService) -> list[ProbedResult]:
        app_id = service.extracted_keys.get("app_id", "")
        api_key = service.extracted_keys.get("api_key", "")
        index_name = service.extracted_keys.get("index_name", "")

        if not app_id or not api_key:
            return []

        results: list[ProbedResult] = []
        headers = {
            "X-Algolia-Application-Id": app_id,
            "X-Algolia-API-Key": api_key,
        }

        if index_name:
            # Query a specific index
            url = f"https://{app_id}-dsn.algolia.net/1/indexes/{index_name}/query"
            pr = await self.prober.probe(
                service,
                url,
                method="POST",
                payload={"query": "", "hitsPerPage": 3},
                extra_headers=headers,
            )
            results.append(pr)
        else:
            # List available indexes
            url = f"https://{app_id}-dsn.algolia.net/1/indexes"
            pr = await self.prober.probe(
                service,
                url,
                extra_headers=headers,
            )
            results.append(pr)

        return results

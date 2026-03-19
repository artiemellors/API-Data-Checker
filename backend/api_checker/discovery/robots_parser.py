"""
Robots.txt and sitemap.xml parser.

Provides
--------
RobotsAndSitemapParser  — fetches robots.txt + sitemaps for a domain
RobotsResult            — structured output (Pydantic)
"""

from __future__ import annotations

import logging
import re
import urllib.robotparser
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel

from ..config import settings

logger = logging.getLogger(__name__)

_PRODUCT_RE = re.compile(
    r"/(?:p|product|pdp|item|dp|sku|pid)/", re.IGNORECASE
)
_CATEGORY_RE = re.compile(
    r"/(?:category|cat|c|collection|department|dept)/", re.IGNORECASE
)
_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class RobotsResult(BaseModel):
    crawl_delay_s: float = 1.0
    disallowed_paths: list[str] = []
    sitemap_urls: list[str] = []
    product_urls: list[str] = []
    category_urls: list[str] = []


class RobotsAndSitemapParser:
    def __init__(self, base_url: str, client: httpx.AsyncClient) -> None:
        parsed = urlparse(base_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.client = client

    async def parse(self) -> RobotsResult:
        result = RobotsResult()

        # ── robots.txt ────────────────────────────────────────────────────────
        robots_url = f"{self.base_url}/robots.txt"
        try:
            resp = await self.client.get(robots_url, timeout=10.0)
            if resp.status_code == 200:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(resp.text.splitlines())

                delay = rp.crawl_delay("*")
                if delay:
                    result.crawl_delay_s = float(delay)

                result.disallowed_paths = [
                    entry.path
                    for entry in rp.entries
                    for rule in entry.rulelines
                    if not rule.allowance
                ]

                result.sitemap_urls = list(rp.site_maps() or [])
        except Exception as exc:
            logger.debug("robots.txt fetch failed for %s: %s", self.base_url, exc)

        # Fallback: try /sitemap.xml directly
        if not result.sitemap_urls:
            result.sitemap_urls = [f"{self.base_url}/sitemap.xml"]

        # ── Sitemaps ──────────────────────────────────────────────────────────
        all_page_urls: list[str] = []
        await self._fetch_sitemap_urls(result.sitemap_urls, all_page_urls, depth=0)

        for url in all_page_urls:
            if _PRODUCT_RE.search(url) and len(result.product_urls) < 50:
                result.product_urls.append(url)
            elif _CATEGORY_RE.search(url) and len(result.category_urls) < 20:
                result.category_urls.append(url)

        return result

    async def _fetch_sitemap_urls(
        self,
        sitemap_urls: list[str],
        out: list[str],
        depth: int,
    ) -> None:
        if depth > 2:
            return
        for sitemap_url in sitemap_urls[:5]:
            try:
                resp = await self.client.get(sitemap_url, timeout=15.0)
                if resp.status_code != 200:
                    continue
                root = ET.fromstring(_strip_ns(resp.text))
                # sitemapindex → recurse
                nested = [loc.text for loc in root.findall(".//sitemap/loc") if loc.text]
                if nested:
                    await self._fetch_sitemap_urls(nested, out, depth + 1)
                # urlset → collect locs
                for loc in root.findall(".//url/loc"):
                    if loc.text:
                        out.append(loc.text)
            except Exception as exc:
                logger.debug("Sitemap fetch failed %s: %s", sitemap_url, exc)


def _strip_ns(xml_text: str) -> str:
    """Remove XML namespace prefixes so ElementTree selectors work uniformly."""
    return re.sub(r'\sxmlns(?::[^=]+)?="[^"]+"', "", xml_text)

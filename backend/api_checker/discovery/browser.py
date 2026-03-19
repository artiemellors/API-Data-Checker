"""
Playwright-based browser automation for live network traffic capture.

Classes
-------
BrowserManager  — async context manager wrapping a Playwright Chromium instance
SiteCrawler     — crawls several page types on a domain and collects XHR/fetch calls
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse

from playwright.async_api import (
    BrowserContext,
    Page,
    Request,
    Response,
    async_playwright,
)

from ..config import settings
from ..models import DiscoveredEndpoint

logger = logging.getLogger(__name__)

# JS patched into every page before any site code runs
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = {runtime: {}};
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
"""

# Resource types that carry API traffic
_API_TYPES = {"xhr", "fetch"}

# Skip analytics/tag-manager domains — they're noise
_SKIP_DOMAINS = {
    "googletagmanager.com",
    "google-analytics.com",
    "facebook.net",
    "doubleclick.net",
    "hotjar.com",
    "newrelic.com",
    "nr-data.net",
}


def _is_api_domain(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return not any(skip in host for skip in _SKIP_DOMAINS)


# ─── BrowserManager ───────────────────────────────────────────────────────────


class BrowserManager:
    """
    Async context manager that owns a single Playwright Chromium browser.

    Usage::

        async with BrowserManager() as bm:
            page = await bm.new_page()
    """

    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> "BrowserManager":
        self._pw = await async_playwright().start()
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        proxy = {"server": settings.http_proxy} if settings.http_proxy else None
        self._browser = await self._pw.chromium.launch(
            headless=settings.headless,
            args=launch_args,
            proxy=proxy,
        )
        self._context = await self._browser.new_context(
            user_agent=settings.user_agent,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="America/New_York",
            ignore_https_errors=True,
            accept_downloads=False,
        )
        return self

    async def new_page(self) -> Page:
        assert self._context, "BrowserManager not started"
        page = await self._context.new_page()
        await page.add_init_script(_STEALTH_SCRIPT)
        return page

    async def __aexit__(self, *_) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()


# ─── Network capture ──────────────────────────────────────────────────────────


async def capture_network_traffic(
    page: Page,
    url: str,
    wait_ms: int | None = None,
) -> list[DiscoveredEndpoint]:
    """
    Navigate to *url* and return all XHR/fetch requests made during page load.

    Scrolls the page 3× to trigger lazy-loaded API calls.
    """
    wait_ms = wait_ms or settings.page_load_wait_ms
    pending: dict[str, Request] = {}
    captured: list[DiscoveredEndpoint] = []

    def on_request(req: Request) -> None:
        if req.resource_type in _API_TYPES and _is_api_domain(req.url):
            pending[req.url] = req

    async def on_response(resp: Response) -> None:
        req = pending.pop(resp.request.url, None)
        if req is None:
            return
        try:
            body_bytes = await resp.body()
            body_sample = body_bytes[:4096].decode("utf-8", errors="replace")
        except Exception:
            body_sample = None

        captured.append(
            DiscoveredEndpoint(
                scan_id="",  # filled in by SiteCrawler
                url=req.url,
                method=req.method,
                request_headers=dict(req.headers),
                request_body=req.post_data,
                response_status=resp.status,
                response_body_sample=body_sample,
                source="browser",
            )
        )

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        await page.goto(url, timeout=settings.browser_timeout_ms, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception as exc:
        logger.debug("Page load issue for %s: %s", url, exc)

    # Scroll to trigger lazy-loaded API calls
    for _ in range(3):
        try:
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(1000)
        except Exception:
            break

    await page.wait_for_timeout(wait_ms)
    return captured


# ─── SiteCrawler ─────────────────────────────────────────────────────────────


# Path fragments that suggest a product detail page
_PRODUCT_PATTERNS = re.compile(
    r"/(?:p|product|pdp|item|dp|sku|pid)/", re.IGNORECASE
)
# Path fragments that suggest a category listing page
_CATEGORY_PATTERNS = re.compile(
    r"/(?:category|cat|c|collection|department|dept)/", re.IGNORECASE
)


class SiteCrawler:
    """
    Crawls a retailer domain across multiple representative page types
    (homepage, search, category, product, cart) and returns the union of
    all captured XHR/fetch endpoints.
    """

    def __init__(
        self,
        url: str,
        browser_manager: BrowserManager,
        scan_id: str = "",
        max_pages: int = 10,
    ) -> None:
        self.url = url
        self.bm = browser_manager
        self.scan_id = scan_id
        self.max_pages = max_pages

        parsed = urlparse(url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

    async def crawl(self) -> list[DiscoveredEndpoint]:
        """Return deduplicated endpoints from all crawled pages."""
        page_urls = await self._discover_page_urls()
        all_endpoints: list[DiscoveredEndpoint] = []
        seen_patterns: set[str] = set()

        for page_url in page_urls[: self.max_pages]:
            try:
                await asyncio.sleep(settings.rate_limit_delay_s)
                page = await self.bm.new_page()
                try:
                    endpoints = await capture_network_traffic(page, page_url)
                finally:
                    await page.close()

                for ep in endpoints:
                    pattern = _normalise_url_pattern(ep.url)
                    if pattern not in seen_patterns:
                        seen_patterns.add(pattern)
                        ep.scan_id = self.scan_id
                        all_endpoints.append(ep)

                logger.debug("Crawled %s → %d endpoints", page_url, len(endpoints))
            except Exception as exc:
                logger.warning("Failed to crawl %s: %s", page_url, exc)

        return all_endpoints

    async def _discover_page_urls(self) -> list[str]:
        """Return a list of page URLs covering the main page types."""
        urls: list[str] = [self.base_url + "/"]

        # Search results
        for search_path in ["/?q=shirt", "/search?q=shirt", "/search?query=shirt"]:
            urls.append(self.base_url + search_path)

        # Cart / bag
        for cart_path in ["/cart", "/bag", "/basket", "/checkout/cart"]:
            urls.append(self.base_url + cart_path)

        # Discover category + product links from the homepage
        try:
            page = await self.bm.new_page()
            try:
                await page.goto(
                    self.base_url + "/",
                    timeout=settings.browser_timeout_ms,
                    wait_until="domcontentloaded",
                )
                links = await page.eval_on_selector_all(
                    "a[href]", "els => els.map(e => e.href)"
                )
            finally:
                await page.close()

            same_domain_links = [
                lnk for lnk in links if lnk.startswith(self.base_url)
            ]

            category_url = next(
                (lnk for lnk in same_domain_links if _CATEGORY_PATTERNS.search(lnk)),
                None,
            )
            if category_url:
                urls.insert(1, category_url)

            product_url = next(
                (lnk for lnk in same_domain_links if _PRODUCT_PATTERNS.search(lnk)),
                None,
            )
            if product_url:
                urls.insert(2, product_url)

        except Exception as exc:
            logger.warning("Homepage link discovery failed: %s", exc)

        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                deduped.append(u)
        return deduped


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _normalise_url_pattern(url: str) -> str:
    """
    Strip query-param *values* but keep param *names* so that the same API
    endpoint called with different search terms is deduplicated.

    e.g.  https://ac.cnstrc.com/search/shirt?key=abc&page=2
       →  https://ac.cnstrc.com/search/*?key=*&page=*
    """
    from urllib.parse import parse_qs, urlencode, urlunparse

    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    masked = {k: ["*"] for k in qs}
    new_qs = urlencode(masked, doseq=True)
    # Also mask the last path segment (often a search term)
    path_parts = parsed.path.rsplit("/", 1)
    masked_path = path_parts[0] + "/*" if len(path_parts) == 2 and path_parts[1] else parsed.path
    return urlunparse(parsed._replace(path=masked_path, query=new_qs))

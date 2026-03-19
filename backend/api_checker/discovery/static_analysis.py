"""
Static analysis of JavaScript bundles to extract embedded API keys and endpoints.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ..config import settings

logger = logging.getLogger(__name__)

# Domains whose scripts we can skip (noise / no useful API keys)
_SKIP_SCRIPT_DOMAINS = {
    "googletagmanager.com",
    "google-analytics.com",
    "facebook.net",
    "doubleclick.net",
    "connect.facebook.net",
    "cdn.segment.com",    # Segment loader — key is in inline init, not the CDN bundle
    "hotjar.com",
    "clarity.ms",
}

# ─── Regex patterns ────────────────────────────────────────────────────────────

EXTRACTION_PATTERNS: dict[str, re.Pattern] = {
    # constructor.io
    "constructor_io_key": re.compile(r"\bkey_[A-Za-z0-9]{24}\b"),
    # Algolia
    "algolia_app_id": re.compile(r'"appId"\s*:\s*"([A-Z0-9]{6,12})"'),
    "algolia_api_key": re.compile(r'"apiKey"\s*:\s*"([a-f0-9]{20,40})"'),
    "algolia_index": re.compile(r'"indexName"\s*:\s*"([^"]{4,60})"'),
    # Bazaarvoice
    "bazaarvoice_passkey": re.compile(
        r'(?:passkey|apikey)["\s:=\']+([A-Za-z0-9_\-]{20,80})', re.IGNORECASE
    ),
    "bazaarvoice_client": re.compile(
        r'bvConfig\.client\s*[=:]\s*["\']([^"\']+)["\']', re.IGNORECASE
    ),
    # Searchspring
    "searchspring_site_id": re.compile(
        r'(?:siteId|site_id)["\s:=\']+([a-z0-9]{6,20})', re.IGNORECASE
    ),
    # Klevu
    "klevu_api_key": re.compile(r'"klevu_apiKey"\s*:\s*"([^"]{10,80})"'),
    # Yotpo
    "yotpo_app_key": re.compile(
        r'(?:yotpoAppKey|appKey|app_key)["\s:=\']+([A-Za-z0-9_\-]{10,60})',
        re.IGNORECASE,
    ),
    # PowerReviews
    "powerreviews_api_key": re.compile(
        r'(?:powerreviews|pr_).*?apikey["\s:=\']+([A-Za-z0-9\-]{30,50})',
        re.IGNORECASE,
    ),
    "powerreviews_merchant_id": re.compile(
        r'merchant_id["\s:=\']+([0-9]{4,10})', re.IGNORECASE
    ),
    # Segment
    "segment_write_key": re.compile(
        r'analytics\.load\s*\(\s*["\']([A-Za-z0-9]{20,40})["\']'
    ),
    # Intercom
    "intercom_app_id": re.compile(
        r'"app_id"\s*:\s*"([a-z0-9]{6,12})"', re.IGNORECASE
    ),
    # Klaviyo
    "klaviyo_public_key": re.compile(
        r'klaviyo[^;]{0,100}["\']([A-Za-z0-9]{6,12})["\']', re.IGNORECASE
    ),
    # Stripe
    "stripe_publishable_key": re.compile(r'\bpk_(?:live|test)_[A-Za-z0-9]{24,}\b'),
    # Braze
    "braze_api_key": re.compile(
        r'(?:appboy|braze)[^;]{0,100}api[_-]?key["\s:=\']+([A-Za-z0-9\-]{20,50})',
        re.IGNORECASE,
    ),
    # Generic API base URL
    "generic_api_base": re.compile(
        r'https://[a-zA-Z0-9][a-zA-Z0-9.\-]+\.[a-z]{2,6}'
        r'/(?:api|v\d|graphql)[/"\'\s]',
        re.IGNORECASE,
    ),
    # JWT / Bearer (low confidence — may be sample tokens)
    "jwt_token": re.compile(
        r'eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}'
    ),
}

# Compile patterns once at import time
_COMPILED: dict[str, re.Pattern] = {k: v for k, v in EXTRACTION_PATTERNS.items()}


# ─── Bundle downloader ────────────────────────────────────────────────────────


async def download_js_bundles(
    page_url: str,
    client: httpx.AsyncClient,
) -> list[tuple[str, str]]:
    """
    Fetch the HTML of *page_url* and return ``(script_url, content)`` for:

    * all external ``<script src="…">`` tags (excluding noise domains)
    * all inline ``<script>`` blocks (keyed as ``"inline:{index}"``)
    """
    results: list[tuple[str, str]] = []

    try:
        resp = await client.get(page_url, timeout=settings.http_timeout_s)
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        logger.warning("Failed to fetch %s for JS analysis: %s", page_url, exc)
        return results

    soup = BeautifulSoup(html, "html.parser")
    inline_idx = 0

    for tag in soup.find_all("script"):
        src = tag.get("src")
        if src:
            script_url = urljoin(page_url, src)
            host = script_url.split("/")[2] if "//" in script_url else ""
            if any(skip in host for skip in _SKIP_SCRIPT_DOMAINS):
                continue
            try:
                r = await client.get(script_url, timeout=settings.http_timeout_s)
                if r.status_code == 200:
                    results.append((script_url, r.text))
            except Exception as exc:
                logger.debug("Skipping %s: %s", script_url, exc)
        else:
            content = tag.get_text()
            if content and len(content.strip()) > 20:
                results.append((f"inline:{inline_idx}", content))
                inline_idx += 1

    return results


# ─── Extractor ────────────────────────────────────────────────────────────────


def extract_from_js(content: str) -> dict[str, list[str]]:
    """
    Apply all ``EXTRACTION_PATTERNS`` to *content* and return a dict of
    ``{pattern_name: [unique_matched_value, …]}``.
    """
    results: dict[str, list[str]] = {}
    for name, pattern in _COMPILED.items():
        matches = pattern.findall(content)
        if matches:
            # findall returns strings or tuples depending on group count
            flat = [m if isinstance(m, str) else m[0] for m in matches]
            unique = list(dict.fromkeys(flat))  # deduplicate, preserve order
            if unique:
                results[name] = unique
    return results

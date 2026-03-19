"""
Third-party service fingerprint registry and matching engine.

Classes
-------
Fingerprint          — declarative rule for one third-party service
FingerprintMatcher   — matches endpoints + JS extractions against the registry
GenericApiRecognizer — classifies unknown JSON/GraphQL APIs by URL path keywords
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field

from ..models import DiscoveredEndpoint, ThirdPartyService

logger = logging.getLogger(__name__)


# ─── Fingerprint dataclass ────────────────────────────────────────────────────


@dataclass
class Fingerprint:
    service_name: str
    category: str
    url_patterns: list[str] = field(default_factory=list)
    js_patterns: list[str] = field(default_factory=list)
    response_indicators: list[str] = field(default_factory=list)
    key_extraction_map: dict[str, str] = field(default_factory=dict)
    """Maps JS extraction pattern names → semantic key names stored in extracted_keys."""
    default_confidence: float = 0.8

    # Compiled patterns — populated at module load time
    _url_re: list[re.Pattern] = field(default_factory=list, repr=False)
    _js_re: list[re.Pattern] = field(default_factory=list, repr=False)

    def compile(self) -> "Fingerprint":
        self._url_re = [re.compile(p, re.IGNORECASE) for p in self.url_patterns]
        self._js_re = [re.compile(p, re.IGNORECASE) for p in self.js_patterns]
        return self

    def matches_url(self, url: str) -> bool:
        return any(r.search(url) for r in self._url_re)

    def matches_js(self, content: str) -> bool:
        return any(r.search(content) for r in self._js_re)

    def matches_response(self, body: str) -> bool:
        return any(ind in body for ind in self.response_indicators)


# ─── Registry ─────────────────────────────────────────────────────────────────

FINGERPRINTS: list[Fingerprint] = [
    # ── Search ────────────────────────────────────────────────────────────────
    Fingerprint(
        service_name="constructor.io",
        category="search",
        url_patterns=[r"\.cnstrc\.com/", r"ac\.cnstrc\.com"],
        js_patterns=[r"key_[A-Za-z0-9]{24}", r"constructor\.io", r"cnstrc"],
        response_indicators=["result_sources", "facets", "total_results_count"],
        key_extraction_map={"constructor_io_key": "api_key"},
        default_confidence=0.95,
    ),
    Fingerprint(
        service_name="algolia",
        category="search",
        url_patterns=[r"-dsn\.algolia\.net/", r"algolia\.net/1/indexes", r"algolia\.net/1/query"],
        js_patterns=[r'"appId"\s*:\s*"[A-Z0-9]{6,12}"', r"algoliasearch", r"instantsearch"],
        response_indicators=["hits", "nbHits", "processingTimeMS", "facets"],
        key_extraction_map={
            "algolia_app_id": "app_id",
            "algolia_api_key": "api_key",
            "algolia_index": "index_name",
        },
        default_confidence=0.95,
    ),
    Fingerprint(
        service_name="searchspring",
        category="search",
        url_patterns=[r"\.a\.searchspring\.io/", r"searchspring\.io/api"],
        js_patterns=[r"searchspring", r"siteId.*?[a-z0-9]{6,}"],
        response_indicators=["results", "pagination", "filterSummary"],
        key_extraction_map={"searchspring_site_id": "site_id"},
        default_confidence=0.9,
    ),
    Fingerprint(
        service_name="klevu",
        category="search",
        url_patterns=[r"klevu\.com/cloud-search", r"api\.klevu\.com"],
        js_patterns=[r"klevu_apiKey", r"klevu\.com", r"KlevuConfig"],
        response_indicators=["queryResults", "metaInfo", "klevu_uc_userOptions"],
        key_extraction_map={"klevu_api_key": "api_key"},
        default_confidence=0.9,
    ),
    Fingerprint(
        service_name="lucidworks-fusion",
        category="search",
        url_patterns=[r"lucidworks\.com", r"/api/apps/.*?/query"],
        js_patterns=[r"lucidworks", r"Fusion\."],
        response_indicators=["response", "fusion"],
        default_confidence=0.75,
    ),
    Fingerprint(
        service_name="elasticsearch",
        category="search",
        url_patterns=[
            r"\.es\.io/",
            r"elastic\.co/",
            r"/_search\b",
            r"/_msearch\b",
        ],
        js_patterns=[r"elasticsearch", r"elastic\.co"],
        response_indicators=["hits", "_shards", "took", "_index"],
        default_confidence=0.8,
    ),
    # ── Reviews ───────────────────────────────────────────────────────────────
    Fingerprint(
        service_name="bazaarvoice",
        category="reviews",
        url_patterns=[
            r"bazaarvoice\.com/data/",
            r"api\.bazaarvoice\.com",
            r"display\.ugc\.bazaarvoice\.com",
        ],
        js_patterns=[r"bazaarvoice", r"BVRRContainer", r"passkey"],
        response_indicators=["BatchedResults", "Results", "TotalResults"],
        key_extraction_map={
            "bazaarvoice_passkey": "passkey",
            "bazaarvoice_client": "client_name",
        },
        default_confidence=0.92,
    ),
    Fingerprint(
        service_name="powerreviews",
        category="reviews",
        url_patterns=[r"powerreviews\.com", r"readservices\.powerreviews"],
        js_patterns=[r"powerreviews", r"POWERREVIEWS", r"pwr-review"],
        response_indicators=["results", "rollup", "reviews"],
        key_extraction_map={
            "powerreviews_api_key": "api_key",
            "powerreviews_merchant_id": "merchant_id",
        },
        default_confidence=0.9,
    ),
    Fingerprint(
        service_name="yotpo",
        category="reviews",
        url_patterns=[r"api\.yotpo\.com", r"staticw2\.yotpo\.com"],
        js_patterns=[r"yotpo", r"yotpoAppKey", r"Yotpo\."],
        response_indicators=["reviews", "bottomline", "total_review"],
        key_extraction_map={"yotpo_app_key": "app_key"},
        default_confidence=0.9,
    ),
    Fingerprint(
        service_name="trustpilot",
        category="reviews",
        url_patterns=[r"api\.trustpilot\.com", r"widget\.trustpilot\.com"],
        js_patterns=[r"trustpilot", r"Trustpilot"],
        response_indicators=["trustScore", "numberOfReviews", "stars"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="okendo",
        category="reviews",
        url_patterns=[r"api\.okendo\.io", r"d3g0gat4468usu\.cloudfront\.net"],
        js_patterns=[r"okendo", r"oke-"],
        response_indicators=["reviewAggregate", "ratingBreakdown"],
        default_confidence=0.85,
    ),
    # ── Recommendations ───────────────────────────────────────────────────────
    Fingerprint(
        service_name="nosto",
        category="recommendations",
        url_patterns=[r"api\.nosto\.com", r"\.nosto\.com/"],
        js_patterns=[r"nosto", r"Nosto\.", r"nostojs"],
        response_indicators=["products", "primaryProducts", "resultType"],
        default_confidence=0.88,
    ),
    Fingerprint(
        service_name="dynamic-yield",
        category="recommendations",
        url_patterns=[r"dynamic-yield\.com", r"dy-api\.com"],
        js_patterns=[r"dynamicYield", r"DY\.API", r"dynamic-yield"],
        response_indicators=["choices", "decisionId", "variations"],
        default_confidence=0.88,
    ),
    Fingerprint(
        service_name="certona",
        category="recommendations",
        url_patterns=[r"certona\.net", r"resonance\.certona\.com"],
        js_patterns=[r"certona", r"Certona"],
        response_indicators=["resonanceResponse", "schemes"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="barilliance",
        category="recommendations",
        url_patterns=[r"barilliance\.com", r"barilliance\.net"],
        js_patterns=[r"barilliance", r"brl_"],
        response_indicators=["items", "barilliance"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="richrelevance",
        category="recommendations",
        url_patterns=[r"richrelevance\.com", r"recs\.richrelevance\.com"],
        js_patterns=[r"richrelevance", r"RR\.jsonCallback"],
        response_indicators=["placements", "recommendedProducts"],
        default_confidence=0.85,
    ),
    # ── Analytics / CDP ───────────────────────────────────────────────────────
    Fingerprint(
        service_name="segment",
        category="analytics",
        url_patterns=[r"api\.segment\.io", r"cdn\.segment\.com/analytics"],
        js_patterns=[r"analytics\.load\s*\(", r"segment\.com", r"Segment"],
        response_indicators=["success"],
        key_extraction_map={"segment_write_key": "write_key"},
        default_confidence=0.88,
    ),
    Fingerprint(
        service_name="mparticle",
        category="analytics",
        url_patterns=[r"inbound\.mparticle\.com", r"jssdks\.mparticle\.com"],
        js_patterns=[r"mParticle", r"mparticle"],
        response_indicators=["dt", "id", "ct"],
        default_confidence=0.85,
    ),
    # ── Chat / Support ────────────────────────────────────────────────────────
    Fingerprint(
        service_name="intercom",
        category="chat",
        url_patterns=[r"api\.intercom\.io", r"widget\.intercom\.io", r"js\.intercomcdn\.com"],
        js_patterns=[r"intercom", r"Intercom\(", r'"app_id"'],
        response_indicators=["session_token", "app_id"],
        key_extraction_map={"intercom_app_id": "app_id"},
        default_confidence=0.88,
    ),
    Fingerprint(
        service_name="zendesk",
        category="chat",
        url_patterns=[r"zendesk\.com", r"zopim\.com", r"zdassets\.com"],
        js_patterns=[r"zendesk", r"Zendesk", r"zE\("],
        response_indicators=["account", "token"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="freshdesk",
        category="chat",
        url_patterns=[r"freshchat\.com", r"freshdesk\.com", r"freshworks\.com"],
        js_patterns=[r"freshchat", r"Freshchat", r"freshdesk"],
        response_indicators=["widget", "token"],
        default_confidence=0.82,
    ),
    Fingerprint(
        service_name="livechat",
        category="chat",
        url_patterns=[r"livechatinc\.com", r"cdn\.livechatinc\.com"],
        js_patterns=[r"livechatinc", r"LiveChat", r"__lc\.license"],
        response_indicators=["status", "license"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="gorgias",
        category="chat",
        url_patterns=[r"config\.gorgias\.chat", r"gorgias\.chat"],
        js_patterns=[r"gorgias", r"Gorgias"],
        response_indicators=["application_id"],
        default_confidence=0.85,
    ),
    # ── A/B Testing / Personalisation ─────────────────────────────────────────
    Fingerprint(
        service_name="optimizely",
        category="ab-testing",
        url_patterns=[r"optimizely\.com", r"cdn\.optimizely\.com"],
        js_patterns=[r"optimizely", r"window\.optimizely"],
        response_indicators=["experiments", "variations"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="vwo",
        category="ab-testing",
        url_patterns=[r"dev\.visualwebsiteoptimizer\.com", r"vwo\.com"],
        js_patterns=[r"vwo", r"VWO\b", r"_vis_opt_"],
        response_indicators=["goals", "combinations"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="ab-tasty",
        category="ab-testing",
        url_patterns=[r"api\.abtasty\.com", r"try\.abtasty\.com"],
        js_patterns=[r"ABTasty", r"abtasty"],
        response_indicators=["tests", "campaigns"],
        default_confidence=0.82,
    ),
    Fingerprint(
        service_name="monetate",
        category="personalization",
        url_patterns=[r"monetate\.net", r"api\.monetate\.net"],
        js_patterns=[r"monetate", r"Monetate"],
        response_indicators=["actions", "context"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="qubit",
        category="personalization",
        url_patterns=[r"qubit\.com", r"api\.qubit\.com"],
        js_patterns=[r"qubit", r"Qubit\b"],
        response_indicators=["experiences", "payload"],
        default_confidence=0.82,
    ),
    # ── Loyalty ───────────────────────────────────────────────────────────────
    Fingerprint(
        service_name="yotpo-loyalty",
        category="loyalty",
        url_patterns=[r"api\.yotpo\.com/v3", r"loyalty\.yotpo\.com"],
        js_patterns=[r"swell\.init", r"yotpo.*loyalty", r"SwellAPI"],
        response_indicators=["points", "balance", "rewards"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="loyaltylion",
        category="loyalty",
        url_patterns=[r"api\.loyaltylion\.com", r"loyaltylion\.com"],
        js_patterns=[r"loyaltylion", r"LoyaltyLion", r"ll\.init"],
        response_indicators=["approved_points", "pending_points"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="smile-io",
        category="loyalty",
        url_patterns=[r"api\.smile\.io", r"app\.smile\.io"],
        js_patterns=[r"smile\.io", r"SmileUI", r"bitabo"],
        response_indicators=["points_balance", "rewards_available"],
        default_confidence=0.85,
    ),
    # ── CDN / Image processing ─────────────────────────────────────────────────
    Fingerprint(
        service_name="cloudinary",
        category="cdn",
        url_patterns=[r"res\.cloudinary\.com", r"api\.cloudinary\.com"],
        js_patterns=[r"cloudinary", r"Cloudinary\b"],
        response_indicators=["public_id", "secure_url", "format"],
        default_confidence=0.9,
    ),
    Fingerprint(
        service_name="scene7",
        category="cdn",
        url_patterns=[r"scene7\.com", r"\.scene7\.com/is/image"],
        js_patterns=[r"scene7", r"Scene7", r"s7sdk"],
        response_indicators=["items", "scene7"],
        default_confidence=0.88,
    ),
    Fingerprint(
        service_name="imgix",
        category="cdn",
        url_patterns=[r"\.imgix\.net/"],
        js_patterns=[r"imgix", r"Imgix"],
        response_indicators=[],
        default_confidence=0.85,
    ),
    # ── Customer Data / Email ──────────────────────────────────────────────────
    Fingerprint(
        service_name="klaviyo",
        category="customer-data",
        url_patterns=[r"a\.klaviyo\.com", r"static\.klaviyo\.com"],
        js_patterns=[r"klaviyo", r"_learnq", r"klaviyoPublicApiKey"],
        response_indicators=["success", "data"],
        key_extraction_map={"klaviyo_public_key": "public_key"},
        default_confidence=0.88,
    ),
    Fingerprint(
        service_name="attentive",
        category="customer-data",
        url_patterns=[r"cdn\.attn\.tv", r"api\.attentivemobile\.com"],
        js_patterns=[r"attentive", r"attn\.tv"],
        response_indicators=["success"],
        default_confidence=0.85,
    ),
    Fingerprint(
        service_name="postscript",
        category="customer-data",
        url_patterns=[r"api\.postscript\.io", r"postscript\.io"],
        js_patterns=[r"postscript", r"PSSubscribe"],
        response_indicators=["success"],
        default_confidence=0.82,
    ),
    # ── Payments ──────────────────────────────────────────────────────────────
    Fingerprint(
        service_name="stripe",
        category="payments",
        url_patterns=[r"api\.stripe\.com", r"js\.stripe\.com"],
        js_patterns=[r"pk_(?:live|test)_[A-Za-z0-9]{24,}", r"Stripe\("],
        response_indicators=["object", "livemode"],
        key_extraction_map={"stripe_publishable_key": "publishable_key"},
        default_confidence=0.92,
    ),
    Fingerprint(
        service_name="braintree",
        category="payments",
        url_patterns=[r"braintreegateway\.com", r"api\.braintreegateway\.com"],
        js_patterns=[r"braintree", r"Braintree"],
        response_indicators=["clientToken", "paymentMethods"],
        default_confidence=0.88,
    ),
    Fingerprint(
        service_name="afterpay",
        category="payments",
        url_patterns=[r"api\.afterpay\.com", r"static\.afterpay\.com"],
        js_patterns=[r"afterpay", r"Afterpay"],
        response_indicators=["configuration", "minimumAmount"],
        default_confidence=0.88,
    ),
    Fingerprint(
        service_name="klarna",
        category="payments",
        url_patterns=[r"api\.klarna\.com", r"x\.klarnacdn\.net"],
        js_patterns=[r"klarna", r"Klarna", r"klarnaCheckoutReady"],
        response_indicators=["session_id", "client_token"],
        default_confidence=0.88,
    ),
    # ── Customer Engagement ────────────────────────────────────────────────────
    Fingerprint(
        service_name="braze",
        category="customer-engagement",
        url_patterns=[r"appboycdn\.com", r"braze\.com/api"],
        js_patterns=[r"appboy", r"braze\.initialize", r"js\.appboycdn\.com", r"Braze\."],
        response_indicators=["device_id", "api_key"],
        key_extraction_map={"braze_api_key": "api_key"},
        default_confidence=0.88,
    ),
    # ── CDN / Performance ─────────────────────────────────────────────────────
    Fingerprint(
        service_name="yottaa",
        category="cdn",
        url_patterns=[r"yottaa\.com", r"yottaa\.net"],
        js_patterns=[r"yottaa", r"rapid\.yottaa", r"YottaaConfig"],
        default_confidence=0.80,
    ),
    # ── Surveys ───────────────────────────────────────────────────────────────
    Fingerprint(
        service_name="survicate",
        category="surveys",
        url_patterns=[r"survicate\.com"],
        js_patterns=[r"survicate", r"Survicate\.load", r"survicate-cdn"],
        default_confidence=0.85,
    ),
    # ── Monitoring ────────────────────────────────────────────────────────────
    Fingerprint(
        service_name="new-relic",
        category="monitoring",
        url_patterns=[r"nr-data\.net", r"js-agent\.newrelic\.com"],
        js_patterns=[r"NREUM", r"newrelic\.agent", r"nr-spa"],
        default_confidence=0.85,
    ),
]

# Compile all patterns at module load
for _fp in FINGERPRINTS:
    _fp.compile()


# ─── FingerprintMatcher ───────────────────────────────────────────────────────


class FingerprintMatcher:
    """
    Matches discovered endpoints and JS extractions against FINGERPRINTS
    and returns a deduplicated list of ThirdPartyService objects.
    """

    def match(
        self,
        endpoints: list[DiscoveredEndpoint],
        js_extractions: dict[str, list[str]],
    ) -> list[ThirdPartyService]:
        # {service_name: {url_hit, js_hit, evidence[], extracted_keys{}}}
        hits: dict[str, dict] = defaultdict(
            lambda: {"url_hit": False, "js_hit": False, "evidence": [], "extracted_keys": {}}
        )
        fp_by_name = {fp.service_name: fp for fp in FINGERPRINTS}

        # URL matching
        for ep in endpoints:
            for fp in FINGERPRINTS:
                if fp.matches_url(ep.url):
                    hits[fp.service_name]["url_hit"] = True
                    hits[fp.service_name]["evidence"].append(f"URL: {ep.url[:120]}")

        # JS matching (applied to all extracted values flattened)
        combined_js = "\n".join(
            v for values in js_extractions.values() for v in values
        )
        for fp in FINGERPRINTS:
            if fp.matches_js(combined_js):
                hits[fp.service_name]["js_hit"] = True
                hits[fp.service_name]["evidence"].append("JavaScript bundle")

        # Populate extracted_keys from js_extractions map
        for fp in FINGERPRINTS:
            for pattern_name, semantic_name in fp.key_extraction_map.items():
                values = js_extractions.get(pattern_name, [])
                if values:
                    hits[fp.service_name]["extracted_keys"][semantic_name] = values[0]

        # Build ThirdPartyService objects
        services: list[ThirdPartyService] = []
        for service_name, data in hits.items():
            fp = fp_by_name[service_name]
            url_hit = data["url_hit"]
            js_hit = data["js_hit"]

            if url_hit and js_hit:
                confidence = fp.default_confidence
            elif url_hit:
                confidence = fp.default_confidence * 0.85
            else:
                confidence = fp.default_confidence * 0.75

            # Bonus for response indicator match
            for ep in endpoints:
                if ep.response_body_sample and fp.matches_response(ep.response_body_sample):
                    confidence = min(1.0, confidence + 0.05)
                    break

            services.append(
                ThirdPartyService(
                    scan_id="",  # filled in by caller
                    service_name=service_name,
                    category=fp.category,
                    confidence=round(confidence, 3),
                    evidence=list(dict.fromkeys(data["evidence"]))[:10],
                    extracted_keys=data["extracted_keys"],
                )
            )

        return services


# ─── GenericApiRecognizer ─────────────────────────────────────────────────────

_PATH_CATEGORIES = [
    (re.compile(r"/(?:product|item|pdp|sku|pid|dp)/", re.I), "product-api"),
    (re.compile(r"/(?:search|find|query|suggest)/", re.I), "search-api"),
    (re.compile(r"/(?:cart|bag|basket)/", re.I), "cart-api"),
    (re.compile(r"/(?:review|rating|feedback)/", re.I), "reviews-api"),
    (re.compile(r"/(?:recommend|recs|suggestion)/", re.I), "recommendations-api"),
    (re.compile(r"/(?:price|pricing|inventory|stock)/", re.I), "inventory-api"),
    (re.compile(r"/(?:account|user|customer|profile)/", re.I), "account-api"),
    (re.compile(r"/(?:order|orders|checkout)/", re.I), "orders-api"),
    (re.compile(r"/graphql\b", re.I), "graphql-api"),
]

_API_PATH_RE = re.compile(r"/(?:api|v\d+|graphql)\b", re.I)
_JSON_START_RE = re.compile(r"^\s*[\[{]")


class GenericApiRecognizer:
    """
    Classifies endpoints that didn't match any known fingerprint.
    Returns low-confidence ThirdPartyService objects for JSON/GraphQL APIs.
    """

    def classify(self, endpoint: DiscoveredEndpoint) -> ThirdPartyService | None:
        sample = endpoint.response_body_sample or ""
        if not _JSON_START_RE.match(sample):
            return None
        if not _API_PATH_RE.search(endpoint.url):
            return None

        category = "unknown-api"
        for pattern, cat in _PATH_CATEGORIES:
            if pattern.search(endpoint.url):
                category = cat
                break

        # Detect GraphQL via request body
        if endpoint.request_body:
            try:
                body = json.loads(endpoint.request_body)
                if "query" in body and "operationName" in body:
                    category = "graphql-api"
            except (json.JSONDecodeError, TypeError):
                pass

        from urllib.parse import urlparse

        host = urlparse(endpoint.url).netloc
        return ThirdPartyService(
            scan_id="",
            service_name=f"retailer-api ({host})",
            category=category,
            confidence=0.3,
            evidence=[f"URL: {endpoint.url[:120]}", "Returns JSON"],
            extracted_keys={},
        )

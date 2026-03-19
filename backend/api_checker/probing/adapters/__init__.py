"""
Adapter registry — maps service_name → adapter class.

Any ThirdPartyService whose service_name is NOT in this dict
falls back to GenericProber using the raw captured endpoint URL.
"""

from .algolia import AlgoliaAdapter
from .bazaarvoice import BazaarvoiceAdapter
from .constructor_io import ConstructorIOAdapter
from .powerreviews import PowerReviewsAdapter
from .searchspring import SearchspringAdapter
from .yotpo import YotpoAdapter

ADAPTER_REGISTRY: dict[str, type] = {
    "constructor.io": ConstructorIOAdapter,
    "algolia": AlgoliaAdapter,
    "bazaarvoice": BazaarvoiceAdapter,
    "powerreviews": PowerReviewsAdapter,
    "yotpo": YotpoAdapter,
    "searchspring": SearchspringAdapter,
}

__all__ = ["ADAPTER_REGISTRY"]

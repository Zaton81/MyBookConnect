"""
Transitional re-exports for backwards compatibility.
Marketplace service and constants now reside in `backend/marketplace/services.py`.
"""
from marketplace.services import (
    ETHICAL_DISCLOSURE,
    MarketplaceService,
)

__all__ = [
    'ETHICAL_DISCLOSURE',
    'MarketplaceService',
]

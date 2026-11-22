"""Community wishlist for the next Grand Theft Auto, grounded in GTA 6 evidence."""

from gta7_wishlist.model import (
    CATEGORIES,
    STATUSES,
    Evidence,
    Proposal,
    load_all,
    load_proposal,
)
from gta7_wishlist.validate import validate

__version__ = "0.1.0"

__all__ = [
    "CATEGORIES",
    "STATUSES",
    "Evidence",
    "Proposal",
    "load_all",
    "load_proposal",
    "validate",
    "__version__",
]

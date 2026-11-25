"""Community wishlist for the next Grand Theft Auto, grounded in GTA 6 evidence."""

from gta7_wishlist.mine import (
    MAX_PICKS,
    Pick,
    Wishlist,
    WishlistError,
    load_wishlist,
    render_markdown,
    save_wishlist,
)
from gta7_wishlist.model import (
    CATEGORIES,
    STATUSES,
    Evidence,
    Proposal,
    load_all,
    load_proposal,
)
from gta7_wishlist.similar import find_duplicates, similarity
from gta7_wishlist.tally import (
    BALLOT_LENGTH,
    IgnoredPick,
    RejectedBallot,
    Report,
    Standing,
    tally,
)
from gta7_wishlist.validate import validate

__version__ = "0.1.0"

__all__ = [
    "BALLOT_LENGTH",
    "CATEGORIES",
    "MAX_PICKS",
    "STATUSES",
    "Evidence",
    "IgnoredPick",
    "Pick",
    "Proposal",
    "RejectedBallot",
    "Report",
    "Standing",
    "Wishlist",
    "WishlistError",
    "find_duplicates",
    "load_all",
    "load_proposal",
    "load_wishlist",
    "render_markdown",
    "save_wishlist",
    "similarity",
    "tally",
    "validate",
    "__version__",
]

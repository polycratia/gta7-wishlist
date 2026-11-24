"""Personal wishlists: pick proposals, rank them and share the card."""

from __future__ import annotations

import tomllib
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

from gta7_wishlist.model import CATEGORIES, Proposal

MAX_PICKS = 25
CARD_TITLE = "My GTA 7 wishlist"

UNKNOWN_PROPOSAL = "UNKNOWN_PROPOSAL"
ALREADY_PICKED = "ALREADY_PICKED"
NOT_PICKED = "NOT_PICKED"
BAD_RANK = "BAD_RANK"
TOO_MANY = "TOO_MANY"

_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


class WishlistError(Exception):
    """A refused change, with a code callers can branch on."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Pick:
    id: str
    rank: int
    note: str | None = None


@dataclass(frozen=True)
class Wishlist:
    handle: str = ""
    updated_on: str = ""
    picks: tuple[Pick, ...] = ()


def pick(
    wishlist: Wishlist,
    proposal_id: str,
    proposals: Iterable[Proposal],
    note: str | None = None,
) -> Wishlist:
    """Add a proposal at the next rank."""
    if proposal_id not in {str(proposal.id) for proposal in proposals}:
        raise WishlistError(UNKNOWN_PROPOSAL, f"unknown proposal id {proposal_id!r}")

    already = _find(wishlist, proposal_id)
    if already is not None:
        raise WishlistError(
            ALREADY_PICKED, f"{proposal_id!r} is already picked, at rank {already.rank}"
        )

    if len(wishlist.picks) >= MAX_PICKS:
        raise WishlistError(
            TOO_MANY,
            f"a wishlist holds at most {MAX_PICKS} picks; drop one before adding another",
        )

    appended = _ordered(wishlist.picks) + [Pick(proposal_id, 0, note or None)]
    return replace(wishlist, picks=_renumber(appended))


def drop(wishlist: Wishlist, proposal_id: str) -> Wishlist:
    """Remove a proposal and close the gap it leaves."""
    if _find(wishlist, proposal_id) is None:
        raise WishlistError(NOT_PICKED, f"{proposal_id!r} is not on the list")

    kept = [item for item in _ordered(wishlist.picks) if item.id != proposal_id]
    return replace(wishlist, picks=_renumber(kept))


def move(wishlist: Wishlist, proposal_id: str, to_rank: int) -> Wishlist:
    """Put a proposal at the given rank and renumber the rest 1..n."""
    current = _find(wishlist, proposal_id)
    if current is None:
        raise WishlistError(NOT_PICKED, f"{proposal_id!r} is not on the list")

    order = _ordered(wishlist.picks)
    if not isinstance(to_rank, int) or isinstance(to_rank, bool):
        raise WishlistError(BAD_RANK, f"rank must be a whole number, got {to_rank!r}")
    if not 1 <= to_rank <= len(order):
        raise WishlistError(BAD_RANK, f"rank {to_rank} is outside 1..{len(order)}")

    rest = [item for item in order if item.id != proposal_id]
    rest.insert(to_rank - 1, current)
    return replace(wishlist, picks=_renumber(rest))


def stamp(wishlist: Wishlist, on: str | None = None) -> Wishlist:
    """Record the day the list last changed."""
    return replace(wishlist, updated_on=on or date.today().isoformat())


def render_markdown(wishlist: Wishlist, proposals: Iterable[Proposal]) -> str:
    """Render the shareable card: ranked titles, categories and a count line."""
    by_id = {str(proposal.id): proposal for proposal in proposals}
    order = _ordered(wishlist.picks)

    lines = [f"# {CARD_TITLE}", "", _byline(wishlist), ""]
    if not order:
        lines.append("No picks yet.")
        return "\n".join(lines) + "\n"

    for item in order:
        proposal = by_id.get(item.id)
        title = str(proposal.title) if proposal is not None else item.id
        lines.append(
            f"{item.rank}. **{title}** ({category_of(by_id, item.id)}) - `{item.id}`"
        )
        if item.note:
            lines.extend(
                f"   {line.strip()}"
                for line in str(item.note).splitlines()
                if line.strip()
            )

    lines += ["", _counts_line(order, by_id)]
    return "\n".join(lines) + "\n"


def load_wishlist(path: str | Path) -> Wishlist:
    """Read a personal wishlist; a file that does not exist yet is an empty one."""
    file_path = Path(path)
    if not file_path.is_file():
        return Wishlist()
    with file_path.open("rb") as handle:
        return _from_mapping(tomllib.load(handle))


def save_wishlist(path: str | Path, wishlist: Wishlist) -> None:
    Path(path).write_text(dumps(wishlist), encoding="utf-8")


def dumps(wishlist: Wishlist) -> str:
    """Write the one TOML shape this module owns, readable back with tomllib."""
    lines = [
        f"handle = {_toml_string(wishlist.handle)}",
        f"updated_on = {_toml_string(wishlist.updated_on)}",
    ]
    for item in _ordered(wishlist.picks):
        lines += [
            "",
            "[[picks]]",
            f"id = {_toml_string(item.id)}",
            f"rank = {int(item.rank)}",
        ]
        if item.note:
            lines.append(f"note = {_toml_string(item.note)}")
    return "\n".join(lines) + "\n"


def category_of(by_id: dict[str, Proposal], proposal_id: str) -> str:
    proposal = by_id.get(proposal_id)
    if proposal is None:
        return "unknown"
    return _as_text(proposal.category) or "unknown"


def _toml_string(value: object) -> str:
    out = ['"']
    for character in _as_text(value):
        escaped = _ESCAPES.get(character)
        if escaped is not None:
            out.append(escaped)
        elif character < " " or character == "\x7f":
            out.append(f"\\u{ord(character):04X}")
        else:
            out.append(character)
    out.append('"')
    return "".join(out)


def _from_mapping(raw: dict[str, Any]) -> Wishlist:
    picks: list[Pick] = []
    raw_picks = raw.get("picks")
    if isinstance(raw_picks, list):
        for position, item in enumerate(raw_picks, start=1):
            if not isinstance(item, dict):
                continue
            rank = item.get("rank")
            usable = isinstance(rank, int) and not isinstance(rank, bool)
            picks.append(
                Pick(
                    id=_as_text(item.get("id")),
                    rank=rank if usable else position,
                    note=_as_text(item.get("note")) or None,
                )
            )

    return Wishlist(
        handle=_as_text(raw.get("handle")),
        updated_on=_as_text(raw.get("updated_on")),
        picks=_renumber(_ordered(picks)),
    )


def _find(wishlist: Wishlist, proposal_id: str) -> Pick | None:
    for item in wishlist.picks:
        if item.id == proposal_id:
            return item
    return None


def _ordered(picks: Iterable[Pick]) -> list[Pick]:
    return sorted(picks, key=lambda item: item.rank)


def _renumber(picks: Sequence[Pick]) -> tuple[Pick, ...]:
    return tuple(
        replace(item, rank=position) for position, item in enumerate(picks, start=1)
    )


def _byline(wishlist: Wishlist) -> str:
    who = f"By @{wishlist.handle}" if wishlist.handle else "By an unnamed player"
    when = f", updated {wishlist.updated_on}" if wishlist.updated_on else ""
    return f"{who}{when}."


def _counts_line(picks: Sequence[Pick], by_id: dict[str, Proposal]) -> str:
    counts = Counter(category_of(by_id, item.id) for item in picks)
    names = [name for name in CATEGORIES if name in counts]
    names += sorted(name for name in counts if name not in CATEGORIES)
    listed = ", ".join(f"{name} {counts[name]}" for name in names)
    label = "pick" if len(picks) == 1 else "picks"
    return f"{len(picks)} {label}: {listed}."


def _as_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)

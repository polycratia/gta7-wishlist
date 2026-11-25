"""Tally the community ballots behind the GTA 7 wishlist leaderboard.

A ballot is one file at wishlists/<handle>.toml, written in the same format as a
personal wishlist. The file name is the handle, and one file per handle is the
only identity rule: this is a poll of the people who sent a file, not a
measurement of what every GTA 6 player wants.

Scoring is a Borda count over a fixed ballot length of 25. Rank 1 is worth 25
points and rank 25 is worth 1. A shorter ballot is never padded, so every player
spends the same weight on their top pick.

The leaderboard is ordered by points, then picks, then first places, then id.
That order decides what the public list looks like, so it is spelled out here:
points first, because they carry the ranking a player actually wrote; picks next,
so a wish many people named outranks one a few people ranked high; first places
as the last signal; and the id only to keep equal rows stable between runs. Rows
that tie on all three counts share a rank and the next rank skips: 1, 2, 2, 4.

A ballot is rejected whole, with a reason in the report instead of an exception.
Picks of proposals whose status is 'declined' are ignored and listed, while the
rest of that ballot still counts; declined proposals are left out of the
standings.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gta7_wishlist.model import Proposal

BALLOT_LENGTH = 25
DECLINED = "declined"


@dataclass(frozen=True)
class Standing:
    id: str
    title: str
    category: str
    rank: int
    points: int
    picks: int
    first_places: int


@dataclass(frozen=True)
class RejectedBallot:
    handle: str
    path: str
    reason: str


@dataclass(frozen=True)
class IgnoredPick:
    handle: str
    id: str
    rank: int
    reason: str


@dataclass(frozen=True)
class Report:
    standings: tuple[Standing, ...] = ()
    counted: tuple[str, ...] = ()
    rejected: tuple[RejectedBallot, ...] = ()
    ignored: tuple[IgnoredPick, ...] = ()


def tally(
    wishlists: str | Path | Iterable[str | Path],
    proposals: Iterable[Proposal],
) -> Report:
    """Score every ballot in wishlists against the shared proposal list."""
    catalogue = {_text(item.id): item for item in proposals if _text(item.id)}
    listed = [
        proposal_id
        for proposal_id, item in catalogue.items()
        if _text(item.status) != DECLINED
    ]

    points = {proposal_id: 0 for proposal_id in listed}
    picks = {proposal_id: 0 for proposal_id in listed}
    first_places = {proposal_id: 0 for proposal_id in listed}

    counted: list[str] = []
    rejected: list[RejectedBallot] = []
    ignored: list[IgnoredPick] = []
    seen: dict[str, str] = {}

    for path in _paths(wishlists):
        handle = path.stem
        raw, reason = _read(path)
        entries: list[tuple[str, int]] = []
        if raw is not None:
            entries, reason = _ballot(raw, handle, seen, catalogue)
        if reason is not None:
            rejected.append(
                RejectedBallot(handle=handle, path=str(path), reason=reason)
            )
            continue

        seen[handle] = str(path)
        counted.append(handle)
        for proposal_id, rank in entries:
            if _text(catalogue[proposal_id].status) == DECLINED:
                ignored.append(
                    IgnoredPick(
                        handle=handle,
                        id=proposal_id,
                        rank=rank,
                        reason="the proposal is declined",
                    )
                )
                continue
            points[proposal_id] += BALLOT_LENGTH + 1 - rank
            picks[proposal_id] += 1
            if rank == 1:
                first_places[proposal_id] += 1

    return Report(
        standings=_standings(catalogue, listed, points, picks, first_places),
        counted=tuple(counted),
        rejected=tuple(rejected),
        ignored=tuple(ignored),
    )


def _paths(wishlists: str | Path | Iterable[str | Path]) -> list[Path]:
    if isinstance(wishlists, (str, Path)):
        directory = Path(wishlists)
        if directory.is_dir():
            return sorted(directory.glob("*.toml"))
        return [directory]
    return [Path(item) for item in wishlists]


def _read(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle), None
    except FileNotFoundError:
        return None, "no such file"
    except tomllib.TOMLDecodeError as error:
        return None, f"not readable as TOML ({error})"
    except OSError as error:
        return None, f"not readable ({error})"


def _ballot(
    raw: dict[str, Any],
    handle: str,
    seen: dict[str, str],
    catalogue: dict[str, Proposal],
) -> tuple[list[tuple[str, int]], str | None]:
    in_file = _text(raw.get("handle"))
    if in_file != handle:
        return [], (
            f"handle {in_file!r} does not match the file name {handle!r}; "
            "a ballot file is named after the handle that owns it"
        )
    if handle in seen:
        return [], (
            f"handle {handle!r} already voted in {seen[handle]}; one file per handle"
        )

    entries, reason = _entries(raw)
    if reason is not None:
        return [], reason
    return entries, _unusable(entries, catalogue)


def _entries(raw: dict[str, Any]) -> tuple[list[tuple[str, int]], str | None]:
    raw_picks = raw.get("picks")
    if not isinstance(raw_picks, list):
        return [], "has no [[picks]] entries"

    entries: list[tuple[str, int]] = []
    for position, item in enumerate(raw_picks, start=1):
        if not isinstance(item, dict):
            return [], f"picks[{position}] is not a [[picks]] table"
        proposal_id = item.get("id")
        rank = item.get("rank")
        if not isinstance(proposal_id, str) or not proposal_id:
            return [], f"picks[{position}] has no id"
        if not isinstance(rank, int) or isinstance(rank, bool):
            return [], f"picks[{position}] ({proposal_id}) has no whole-number rank"
        entries.append((proposal_id, rank))
    return entries, None


def _unusable(
    entries: list[tuple[str, int]], catalogue: dict[str, Proposal]
) -> str | None:
    if not entries:
        return "has no picks; an empty ballot is not a vote"
    if len(entries) > BALLOT_LENGTH:
        return (
            f"picks {len(entries)} proposals, more than the ballot length "
            f"of {BALLOT_LENGTH}"
        )

    chosen: set[str] = set()
    for proposal_id, _ in entries:
        if proposal_id in chosen:
            return f"picks {proposal_id!r} twice"
        if proposal_id not in catalogue:
            return f"picks unknown proposal {proposal_id!r}"
        chosen.add(proposal_id)

    ranks = sorted(rank for _, rank in entries)
    if ranks != list(range(1, len(entries) + 1)):
        written = ", ".join(str(rank) for rank in ranks)
        return (
            f"ranks must be 1..{len(entries)} with no gaps and no repeats, "
            f"got {written}"
        )
    return None


def _standings(
    catalogue: dict[str, Proposal],
    listed: list[str],
    points: dict[str, int],
    picks: dict[str, int],
    first_places: dict[str, int],
) -> tuple[Standing, ...]:
    order = sorted(
        listed,
        key=lambda proposal_id: (
            -points[proposal_id],
            -picks[proposal_id],
            -first_places[proposal_id],
            proposal_id,
        ),
    )

    standings: list[Standing] = []
    rank = 0
    previous: tuple[int, int, int] | None = None
    for position, proposal_id in enumerate(order, start=1):
        counts = (points[proposal_id], picks[proposal_id], first_places[proposal_id])
        if counts != previous:
            rank = position
            previous = counts
        proposal = catalogue[proposal_id]
        standings.append(
            Standing(
                id=proposal_id,
                title=_text(proposal.title),
                category=_text(proposal.category),
                rank=rank,
                points=counts[0],
                picks=counts[1],
                first_places=counts[2],
            )
        )
    return tuple(standings)


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""

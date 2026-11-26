"""Format checks for wishlist proposals and the GTA 6 updates they point at."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

from gta7_wishlist.model import CATEGORIES, STATUSES, Evidence, Proposal, Update, as_date

TITLE_MIN = 8
TITLE_MAX = 90
TEXT_MIN = 40
SUMMARY_MIN = 20
ADDRESSED = "addressed"

_KEBAB_CASE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate(proposals: Iterable[Proposal], updates: Iterable[Update] = ()) -> list[str]:
    """Return every problem found in the given proposals and updates."""
    problems: list[str] = []
    locations_by_id: dict[str, list[str]] = {}
    known = list(proposals)
    known_updates = list(updates)

    update_ids = {
        update.id for update in known_updates if isinstance(update.id, str) and update.id
    }
    released = {update.id for update in known_updates if _is_released(update)}

    for proposal in known:
        where = _where(proposal)
        problems.extend(_check_id(proposal.id, proposal.path, where))
        problems.extend(_check_text(proposal, where))
        problems.extend(
            _check_evidence(
                proposal.evidence,
                where,
                "needs at least one evidence item showing how GTA 6 behaves today",
            )
        )
        problems.extend(_check_addressed(proposal, where, update_ids, released))
        if isinstance(proposal.id, str) and proposal.id:
            locations_by_id.setdefault(proposal.id, []).append(where)

    for proposal_id, locations in locations_by_id.items():
        if len(locations) > 1:
            problems.append(
                f"duplicate id {proposal_id!r}: " + ", ".join(sorted(locations))
            )

    problems.extend(_check_not_duplicate_of(known))
    problems.extend(_check_updates(known_updates))

    return problems


def _where(proposal: Proposal) -> str:
    if isinstance(proposal.path, str) and proposal.path:
        return proposal.path
    if isinstance(proposal.id, str) and proposal.id:
        return proposal.id
    return "<unnamed proposal>"


def _where_update(update: Update) -> str:
    if isinstance(update.path, str) and update.path:
        return update.path
    if isinstance(update.id, str) and update.id:
        return update.id
    return "<unnamed update>"


def _check_id(value: Any, path: Any, where: str) -> list[str]:
    if not isinstance(value, str) or not _KEBAB_CASE.match(value):
        return [f"{where}: id must be kebab-case, got {value!r}"]
    if isinstance(path, str) and path:
        stem = Path(path).stem
        if stem != value:
            return [f"{where}: id {value!r} does not match file name {stem!r}"]
    return []


def _check_text(proposal: Proposal, where: str) -> list[str]:
    problems = []

    title = proposal.title
    if not isinstance(title, str) or not TITLE_MIN <= len(title) <= TITLE_MAX:
        problems.append(
            f"{where}: title must be {TITLE_MIN}..{TITLE_MAX} characters, got {title!r}"
        )

    if proposal.category not in CATEGORIES:
        problems.append(
            f"{where}: category {proposal.category!r} is not one of {', '.join(CATEGORIES)}"
        )

    if proposal.status not in STATUSES:
        problems.append(
            f"{where}: status {proposal.status!r} is not one of {', '.join(STATUSES)}"
        )

    for name in ("problem", "proposal"):
        value = getattr(proposal, name)
        if not isinstance(value, str) or len(value) < TEXT_MIN:
            problems.append(f"{where}: {name} must be at least {TEXT_MIN} characters")

    return problems


def _check_evidence(evidence: Iterable[Evidence], where: str, missing: str) -> list[str]:
    items = list(evidence)
    if not items:
        return [f"{where}: {missing}"]

    problems = []
    for index, item in enumerate(items):
        url = item.url
        if not isinstance(url, str) or not url.startswith("https://"):
            problems.append(
                f"{where}: evidence[{index}] url must start with https://, got {url!r}"
            )
        if as_date(item.checked_on) is None:
            problems.append(
                f"{where}: evidence[{index}] checked_on must be a real date "
                f"(YYYY-MM-DD), got {item.checked_on!r}"
            )
    return problems


def _check_addressed(
    proposal: Proposal, where: str, update_ids: set[str], released: set[str]
) -> list[str]:
    addressed_by = proposal.addressed_by
    if addressed_by is not None and not isinstance(addressed_by, str):
        return [f"{where}: addressed_by must be an update id, got {addressed_by!r}"]

    problems = []
    named = addressed_by or ""
    if proposal.status == ADDRESSED:
        if not named:
            problems.append(
                f"{where}: status 'addressed' needs addressed_by naming the update "
                "in updates/ that fixed it"
            )
        elif named not in update_ids:
            problems.append(
                f"{where}: addressed_by {named!r} is not an update in the updates directory"
            )
        elif named not in released:
            problems.append(
                f"{where}: update {named!r} is not out yet by its own evidence; "
                "a wish is addressed only after the update is released"
            )
    elif named:
        problems.append(
            f"{where}: addressed_by {named!r} needs status 'addressed', "
            f"not {proposal.status!r}"
        )

    if proposal.addressed_note is not None and not isinstance(
        proposal.addressed_note, str
    ):
        problems.append(f"{where}: addressed_note must be text")

    return problems


def _check_updates(updates: list[Update]) -> list[str]:
    problems: list[str] = []
    locations_by_id: dict[str, list[str]] = {}

    for update in updates:
        where = _where_update(update)
        problems.extend(_check_id(update.id, update.path, where))

        if not isinstance(update.version, str) or not update.version.strip():
            problems.append(
                f"{where}: version must name the title update, got {update.version!r}"
            )

        released = as_date(update.released_on)
        if released is None:
            problems.append(
                f"{where}: released_on must be a real date (YYYY-MM-DD), "
                f"got {update.released_on!r}"
            )

        if not isinstance(update.summary, str) or len(update.summary) < SUMMARY_MIN:
            problems.append(f"{where}: summary must be at least {SUMMARY_MIN} characters")

        problems.extend(
            _check_evidence(
                update.evidence,
                where,
                "needs at least one evidence item showing the update is out",
            )
        )

        checked = _checked_dates(update)
        if released is not None and checked and released > max(checked):
            problems.append(
                f"{where}: released_on {released.isoformat()} is after the last "
                f"checked_on {max(checked).isoformat()}; an update is recorded once it is out"
            )

        if isinstance(update.id, str) and update.id:
            locations_by_id.setdefault(update.id, []).append(where)

    for update_id, locations in locations_by_id.items():
        if len(locations) > 1:
            problems.append(
                f"duplicate update id {update_id!r}: " + ", ".join(sorted(locations))
            )

    return problems


def _is_released(update: Update) -> bool:
    released = as_date(update.released_on)
    checked = _checked_dates(update)
    return released is not None and bool(checked) and released <= max(checked)


def _checked_dates(update: Update) -> list[date]:
    return [
        moment
        for moment in (as_date(item.checked_on) for item in update.evidence)
        if moment is not None
    ]


def _check_not_duplicate_of(proposals: list[Proposal]) -> list[str]:
    problems = []
    by_id = {
        proposal.id: proposal
        for proposal in proposals
        if isinstance(proposal.id, str) and proposal.id
    }

    for proposal in proposals:
        where = _where(proposal)
        for other_id in proposal.not_duplicate_of:
            if not isinstance(other_id, str) or not other_id:
                problems.append(
                    f"{where}: not_duplicate_of must list proposal ids, got {other_id!r}"
                )
                continue
            if other_id == proposal.id:
                problems.append(
                    f"{where}: not_duplicate_of must not list the proposal itself"
                )
                continue
            other = by_id.get(other_id)
            if other is None or proposal.id in other.not_duplicate_of:
                continue
            problems.append(
                f"{where}: not_duplicate_of {other_id!r} is one-sided; add "
                f"{proposal.id!r} to not_duplicate_of in {_where(other)}"
            )

    return problems

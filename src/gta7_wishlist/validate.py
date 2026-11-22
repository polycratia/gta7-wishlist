"""Format checks for wishlist proposals."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

from gta7_wishlist.model import CATEGORIES, STATUSES, Proposal

TITLE_MIN = 8
TITLE_MAX = 90
TEXT_MIN = 40

_KEBAB_CASE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate(proposals: Iterable[Proposal]) -> list[str]:
    """Return every problem found in the given proposals, as readable lines."""
    problems: list[str] = []
    locations_by_id: dict[str, list[str]] = {}

    for proposal in proposals:
        where = _where(proposal)
        problems.extend(_check_id(proposal, where))
        problems.extend(_check_text(proposal, where))
        problems.extend(_check_evidence(proposal, where))
        if isinstance(proposal.id, str) and proposal.id:
            locations_by_id.setdefault(proposal.id, []).append(where)

    for proposal_id, locations in locations_by_id.items():
        if len(locations) > 1:
            problems.append(
                f"duplicate id {proposal_id!r}: " + ", ".join(sorted(locations))
            )

    return problems


def _where(proposal: Proposal) -> str:
    if isinstance(proposal.path, str) and proposal.path:
        return proposal.path
    if isinstance(proposal.id, str) and proposal.id:
        return proposal.id
    return "<unnamed proposal>"


def _check_id(proposal: Proposal, where: str) -> list[str]:
    proposal_id = proposal.id
    if not isinstance(proposal_id, str) or not _KEBAB_CASE.match(proposal_id):
        return [f"{where}: id must be kebab-case, got {proposal_id!r}"]
    if isinstance(proposal.path, str) and proposal.path:
        stem = Path(proposal.path).stem
        if stem != proposal_id:
            return [f"{where}: id {proposal_id!r} does not match file name {stem!r}"]
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


def _check_evidence(proposal: Proposal, where: str) -> list[str]:
    evidence = proposal.evidence
    if not evidence:
        return [
            f"{where}: needs at least one evidence item showing how GTA 6 behaves today"
        ]

    problems = []
    for index, item in enumerate(evidence):
        url = item.url
        if not isinstance(url, str) or not url.startswith("https://"):
            problems.append(
                f"{where}: evidence[{index}] url must start with https://, got {url!r}"
            )
        if not _is_calendar_date(item.checked_on):
            problems.append(
                f"{where}: evidence[{index}] checked_on must be a real date "
                f"(YYYY-MM-DD), got {item.checked_on!r}"
            )
    return problems


def _is_calendar_date(value: Any) -> bool:
    if isinstance(value, date):
        return True
    if not isinstance(value, str) or not _ISO_DATE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True

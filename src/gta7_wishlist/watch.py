"""What a GTA 6 title update has already addressed.

A wish is only worth ranking until the game changes. updates/ records the
official title updates, one file per update, and a proposal that a patch
answered points at one of them with addressed_by.

A proposal that claims an update nobody recorded is kept apart in `unmatched`
instead of counting as addressed: the update file is the evidence.

days_open is counted from the earliest evidence checked_on, the first day the
behaviour was written down here. For an addressed wish it stops on the day the
update was released; for the rest it runs to today.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from gta7_wishlist.model import Evidence, Proposal, Update, as_date

OPEN = "open"
ADDRESSED = "addressed"
DECLINED = "declined"


@dataclass(frozen=True)
class Tracked:
    id: str
    title: str
    category: str
    status: str
    since: str
    days_open: int
    update_id: str = ""
    version: str = ""
    released_on: str = ""
    note: str = ""


@dataclass(frozen=True)
class StatusReport:
    still_open: tuple[Tracked, ...] = ()
    addressed: tuple[Tracked, ...] = ()
    declined: tuple[Tracked, ...] = ()
    updates: tuple[Update, ...] = ()
    unmatched: tuple[Tracked, ...] = ()


def status_report(
    proposals: Iterable[Proposal],
    updates: Iterable[Update],
    today: date | None = None,
) -> StatusReport:
    """Group the wishes into still open, addressed and declined."""
    now = today or date.today()
    known = list(updates)
    by_id = {
        update.id: update for update in known if isinstance(update.id, str) and update.id
    }

    still_open: list[Tracked] = []
    addressed: list[Tracked] = []
    declined: list[Tracked] = []
    unmatched: list[Tracked] = []

    for proposal in proposals:
        status = _text(proposal.status)
        update = by_id.get(_text(proposal.addressed_by))
        if status == ADDRESSED and update is not None:
            addressed.append(_tracked(proposal, now, update))
        elif status == ADDRESSED:
            unmatched.append(_tracked(proposal, now, None))
        elif status == DECLINED:
            declined.append(_tracked(proposal, now, None))
        else:
            still_open.append(_tracked(proposal, now, None))

    still_open.sort(key=lambda row: (-row.days_open, row.id))
    addressed.sort(key=lambda row: row.id)
    addressed.sort(key=lambda row: row.released_on, reverse=True)
    declined.sort(key=lambda row: row.id)
    unmatched.sort(key=lambda row: row.id)

    return StatusReport(
        still_open=tuple(still_open),
        addressed=tuple(addressed),
        declined=tuple(declined),
        updates=tuple(sorted(known, key=_released_key)),
        unmatched=tuple(unmatched),
    )


def filter_since(report: StatusReport, on_or_after: str | date) -> StatusReport:
    """Keep only the updates recorded on or after a date, and what they addressed."""
    moment = as_date(on_or_after)
    return StatusReport(
        addressed=tuple(
            row for row in report.addressed if _at_or_after(row.released_on, moment)
        ),
        updates=tuple(
            update for update in report.updates if _at_or_after(update.released_on, moment)
        ),
    )


def released_on(update: Update) -> str:
    """The release date of an update as written text."""
    moment = as_date(update.released_on)
    return moment.isoformat() if moment is not None else _text(update.released_on)


def _tracked(proposal: Proposal, now: date, update: Update | None) -> Tracked:
    earliest = _earliest(proposal.evidence)
    released = as_date(update.released_on) if update is not None else None
    end = released if released is not None else now
    days = (end - earliest).days if earliest is not None else 0

    return Tracked(
        id=_text(proposal.id),
        title=_text(proposal.title),
        category=_text(proposal.category),
        status=_text(proposal.status),
        since=earliest.isoformat() if earliest is not None else "",
        days_open=max(days, 0),
        update_id=_text(proposal.addressed_by),
        version=_text(update.version) if update is not None else "",
        released_on=released.isoformat() if released is not None else "",
        note=_text(proposal.addressed_note),
    )


def _earliest(evidence: Iterable[Evidence]) -> date | None:
    dates = [
        moment
        for moment in (as_date(item.checked_on) for item in evidence)
        if moment is not None
    ]
    return min(dates) if dates else None


def _at_or_after(value: Any, moment: date | None) -> bool:
    found = as_date(value)
    return moment is not None and found is not None and found >= moment


def _released_key(update: Update) -> tuple[str, str]:
    return (released_on(update), _text(update.id))


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""

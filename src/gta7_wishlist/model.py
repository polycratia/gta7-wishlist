"""Types and loaders for wishlist proposals and GTA 6 title updates."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

CATEGORIES = (
    "missions",
    "world",
    "online",
    "controls",
    "performance",
    "platforms",
    "progression",
    "accessibility",
    "other",
)

STATUSES = ("open", "addressed", "declined")

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Evidence:
    url: str
    checked_on: Any


@dataclass(frozen=True)
class Proposal:
    id: str
    title: str
    category: str
    problem: str
    proposal: str
    status: str
    evidence: tuple[Evidence, ...] = ()
    tags: tuple[str, ...] = ()
    not_duplicate_of: tuple[str, ...] = ()
    addressed_by: str | None = None
    addressed_note: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class Update:
    id: str
    version: str
    released_on: Any
    summary: str
    evidence: tuple[Evidence, ...] = ()
    path: str | None = None


def load_proposal(path: str | Path) -> Proposal:
    """Read one proposal file. Values are kept as written so validate() can judge them."""
    file_path = Path(path)
    with file_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return _from_mapping(raw, file_path)


def load_all(directory: str | Path) -> list[Proposal]:
    """Read every *.toml proposal in a directory, sorted by file name."""
    return [load_proposal(path) for path in sorted(Path(directory).glob("*.toml"))]


def load_update(path: str | Path) -> Update:
    """Read one GTA 6 title update file, values as written."""
    file_path = Path(path)
    with file_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return _update_from_mapping(raw, file_path)


def load_updates(directory: str | Path) -> list[Update]:
    """Read every *.toml update in a directory, sorted by file name."""
    return [load_update(path) for path in sorted(Path(directory).glob("*.toml"))]


def as_date(value: Any) -> date | None:
    """The value as a calendar date, or None when it is not one."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and _ISO_DATE.match(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _evidence(raw: dict[str, Any]) -> tuple[Evidence, ...]:
    items = []
    raw_evidence = raw.get("evidence")
    if isinstance(raw_evidence, list):
        for item in raw_evidence:
            if isinstance(item, dict):
                items.append(
                    Evidence(
                        url=item.get("url", ""), checked_on=item.get("checked_on", "")
                    )
                )
    return tuple(items)


def _from_mapping(raw: dict[str, Any], path: Path) -> Proposal:
    raw_tags = raw.get("tags")
    tags = tuple(raw_tags) if isinstance(raw_tags, list) else ()

    raw_not_duplicate_of = raw.get("not_duplicate_of")
    not_duplicate_of = (
        tuple(raw_not_duplicate_of) if isinstance(raw_not_duplicate_of, list) else ()
    )

    return Proposal(
        id=raw.get("id", ""),
        title=raw.get("title", ""),
        category=raw.get("category", ""),
        problem=raw.get("problem", ""),
        proposal=raw.get("proposal", ""),
        status=raw.get("status", ""),
        evidence=_evidence(raw),
        tags=tags,
        not_duplicate_of=not_duplicate_of,
        addressed_by=raw.get("addressed_by"),
        addressed_note=raw.get("addressed_note"),
        path=str(path),
    )


def _update_from_mapping(raw: dict[str, Any], path: Path) -> Update:
    return Update(
        id=raw.get("id", ""),
        version=raw.get("version", ""),
        released_on=raw.get("released_on", ""),
        summary=raw.get("summary", ""),
        evidence=_evidence(raw),
        path=str(path),
    )

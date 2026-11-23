"""Types and loaders for wishlist proposals."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
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


def _from_mapping(raw: dict[str, Any], path: Path) -> Proposal:
    evidence = []
    raw_evidence = raw.get("evidence")
    if isinstance(raw_evidence, list):
        for item in raw_evidence:
            if isinstance(item, dict):
                evidence.append(
                    Evidence(url=item.get("url", ""), checked_on=item.get("checked_on", ""))
                )

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
        evidence=tuple(evidence),
        tags=tags,
        not_duplicate_of=not_duplicate_of,
        path=str(path),
    )

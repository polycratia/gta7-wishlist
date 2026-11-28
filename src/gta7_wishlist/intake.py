"""Turn a suggestion filed as a GitHub issue into a proposal draft.

An issue is written by whoever filed it, so all of it is untrusted text. It
reaches a file only as a TOML string written by the escaping writer in this
module, HTML is removed before anything is read, and a line that reads like an
instruction is data like any other line.

Nothing missing is filled in by guessing: a missing section, a category
outside the list and evidence without a public https link are reported, and
the draft is still returned with whatever was found.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from datetime import date

from gta7_wishlist.model import CATEGORIES, Evidence, Proposal

SLUG_MAX = 48
DRAFT_STATUS = "open"

FIELDS = ("problem", "proposal", "category", "evidence")
HEADINGS = {
    "problem": "### What GTA 6 does today",
    "proposal": "### What the next game should do",
    "category": "### Category",
    "evidence": "### Evidence",
}

_BY_HEADING = {
    "what gta 6 does today": "problem",
    "what the next game should do": "proposal",
    "category": "category",
    "evidence": "evidence",
}
_NO_RESPONSE = "_no response_"

_HEADING_LINE = re.compile(r"^ {0,3}#{1,6}\s*(.*)$")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG = re.compile(r"<[^<>\n]*>")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s*)?")
_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)
_CHECKED = re.compile(r"checked\s*:?\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
_WORD = re.compile(r"[a-z0-9]+")
_CATEGORY_WORD = re.compile(r"[a-z][a-z0-9-]*")
_ESCAPES = {'"': '\\"', "\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def split_issue(text: str) -> tuple[str, str]:
    """The title line of an issue saved as one file, and the body under it."""
    lines = _plain(text).split("\n")
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        heading = _HEADING_LINE.match(line)
        if heading is None:
            return _one_line([line]), "\n".join(lines[index + 1 :])
        if _key(heading.group(1)) in _BY_HEADING:
            return "", "\n".join(lines)
        return _one_line([heading.group(1)]), "\n".join(lines[index + 1 :])
    return "", ""


def parse_issue(
    title: str, body: str, today: date | None = None
) -> tuple[Proposal, list[str]]:
    """Read an issue into a proposal draft and every problem found in it."""
    sections = _sections(_plain(body))
    problems: list[str] = []

    for field in FIELDS:
        if field not in sections:
            problems.append(f"the issue has no {HEADINGS[field]!r} section")

    problem = _one_line(sections.get("problem", ()))
    proposal = _one_line(sections.get("proposal", ()))
    category = _category(sections.get("category", ()))
    evidence, evidence_problems = _evidence(
        sections.get("evidence", ()), today or date.today()
    )

    for field, value in (("problem", problem), ("proposal", proposal)):
        if field in sections and not value:
            problems.append(f"the {HEADINGS[field]!r} section is empty")

    if "category" in sections and not category:
        problems.append(f"the {HEADINGS['category']!r} section is empty")
    elif category and category not in CATEGORIES:
        problems.append(f"category {category!r} is not one of {', '.join(CATEGORIES)}")

    if "evidence" in sections:
        problems.extend(evidence_problems)

    draft = Proposal(
        id=slugify(title),
        title=_one_line([_text(title)]),
        category=category,
        problem=problem,
        proposal=proposal,
        status=DRAFT_STATUS,
        evidence=evidence,
    )
    return draft, problems


def slugify(title: str) -> str:
    """The id for a title: ASCII kebab-case, 48 characters at most, whole words."""
    folded = (
        unicodedata.normalize("NFKD", _text(title))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    words = _WORD.findall(folded.lower())

    slug = ""
    for word in words:
        candidate = f"{slug}-{word}" if slug else word
        if len(candidate) > SLUG_MAX:
            break
        slug = candidate

    if slug:
        return slug
    return words[0][:SLUG_MAX] if words else ""


def render_toml(draft: Proposal) -> str:
    """The draft as a proposal file. Every value goes through the string writer."""
    lines: list[str] = []
    if draft.id:
        lines += [f"# proposals/{draft.id}.toml", ""]

    lines += [
        f"id = {_string(draft.id)}",
        f"title = {_string(draft.title)}",
        f"category = {_string(draft.category)}",
        f"status = {_string(draft.status)}",
        f"problem = {_string(draft.problem)}",
        f"proposal = {_string(draft.proposal)}",
    ]
    for item in draft.evidence:
        lines += [
            "",
            "[[evidence]]",
            f"url = {_string(item.url)}",
            f"checked_on = {_string(item.checked_on)}",
        ]
    return "\n".join(lines) + "\n"


def _sections(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    current: list[str] | None = None

    for line in text.split("\n"):
        heading = _HEADING_LINE.match(line)
        if heading is not None:
            field = _BY_HEADING.get(_key(heading.group(1)))
            current = None if field is None else found.setdefault(field, [])
            continue
        if current is not None:
            current.append(line)
    return found


def _evidence(
    lines: Iterable[str], today: date
) -> tuple[tuple[Evidence, ...], list[str]]:
    items: list[Evidence] = []
    problems: list[str] = []

    for line in lines:
        cleaned = _clean(line)
        found = _URL.search(cleaned)
        if found is None:
            continue
        url = found.group(0).rstrip(".,;")
        if not url.lower().startswith("https://"):
            problems.append(f"evidence {url!r} is not a public https link")
            continue
        checked = _CHECKED.search(cleaned)
        items.append(
            Evidence(
                url=url,
                checked_on=checked.group(1) if checked else today.isoformat(),
            )
        )

    if not items:
        problems.append(f"the {HEADINGS['evidence']!r} section has no https link")
    return tuple(items), problems


def _category(lines: Iterable[str]) -> str:
    word = _CATEGORY_WORD.search(_one_line(lines).lower())
    return word.group(0) if word is not None else ""


def _plain(value: object) -> str:
    text = _text(value).replace("\r\n", "\n").replace("\r", "\n")
    text = _HTML_COMMENT.sub("", text)
    return _HTML_TAG.sub("", text)


def _one_line(lines: Iterable[str]) -> str:
    parts = [part for part in (_clean(line) for line in lines) if part]
    text = " ".join(parts)
    if text.lower() == _NO_RESPONSE:
        return ""
    return " ".join(text.split())


def _clean(line: str) -> str:
    return _BULLET.sub("", line).strip()


def _key(heading: str) -> str:
    cleaned = heading.strip().strip("*_").strip().rstrip(":").strip()
    return " ".join(cleaned.lower().split())


def _string(value: object) -> str:
    out = ['"']
    for character in _text(value):
        escape = _ESCAPES.get(character)
        if escape is not None:
            out.append(escape)
        elif character < " " or character == "\x7f":
            out.append(f"\\u{ord(character):04X}")
        else:
            out.append(character)
    out.append('"')
    return "".join(out)


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""

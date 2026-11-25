"""Render the public leaderboard built from the community ballots.

The board is generated, never hand-written: `gta7 board --write` writes
docs/leaderboard.md and replaces the block between the board markers in
README.md, and the tests compare both copies against render_board() byte for
byte. A ballot merged without a regenerated board therefore fails.

Ballots whose handle starts with 'example-' never count toward the board. The
example files in wishlists/ exist to show the format and to give the tests
something to score, so counting them would publish votes nobody cast. With no
real ballot the board says so instead of printing an empty table.

The same text is committed at two different depths, so a link to a proposal
file cannot be relative; it points at the file in the public repository.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from gta7_wishlist.model import CATEGORIES, Proposal
from gta7_wishlist.tally import Report, Standing, tally

EXAMPLE_PREFIX = "example-"
TOP_PER_CATEGORY = 3

BOARD_START = "<!-- board:start -->"
BOARD_END = "<!-- board:end -->"
LEADERBOARD_FILE = "docs/leaderboard.md"
README_FILE = "README.md"
PROPOSAL_URL = "https://github.com/polycratia/gta7-wishlist/blob/main/proposals"

HEADING = "## GTA 7 wishlist leaderboard"
CATEGORY_HEADING = "### Top three per category"
EMPTY = "No ballots yet."
REGENERATE = "Regenerate this with `gta7 board --write` after a ballot is merged."
NOTE = (
    "Ballots whose handle starts with `example-` never count toward the board:",
    "the example files are in the repository to show the format, and they count",
    "only in the tests.",
)
TABLE_HEAD = (
    "| Rank | Wish | Category | Picks | Points |",
    "| ---: | :--- | :--- | ---: | ---: |",
)

_ESCAPES = (("\\", "\\\\"), ("|", "\\|"), ("[", "\\["), ("]", "\\]"))


def board_ballots(wishlists: str | Path) -> list[Path]:
    """Every ballot file that counts toward the board, sorted by name."""
    return [
        path
        for path in sorted(Path(wishlists).glob("*.toml"))
        if not path.stem.startswith(EXAMPLE_PREFIX)
    ]


def tally_board(wishlists: str | Path, proposals: Iterable[Proposal]) -> Report:
    """Score the ballots that count toward the board."""
    return tally(board_ballots(wishlists), proposals)


def render_board(tally_result: Report, proposals: Iterable[Proposal]) -> str:
    """Render the leaderboard as Markdown: a table and a top three per category."""
    catalogue = {_text(item.id): item for item in proposals if _text(item.id)}
    ballots = [
        handle
        for handle in tally_result.counted
        if not handle.startswith(EXAMPLE_PREFIX)
    ]

    lines = [HEADING, "", _built_from(len(ballots)), *NOTE, ""]
    if not ballots:
        return _joined([*lines, EMPTY, "", REGENERATE])

    lines += list(TABLE_HEAD)
    lines += [_row(row, catalogue) for row in tally_result.standings]

    top = _per_category(tally_result.standings)
    if top:
        lines += ["", CATEGORY_HEADING, "", *top]
    return _joined([*lines, "", REGENERATE])


def read_block(text: str) -> str:
    """The board block of a README, as render_board() wrote it."""
    start = text.index("\n", text.index(BOARD_START)) + 1
    return text[start : text.index(BOARD_END)]


def write_block(text: str, body: str) -> str:
    """Put a freshly rendered board between the markers, leaving the rest alone."""
    return (
        text[: text.index(BOARD_START)]
        + BOARD_START
        + "\n"
        + body
        + text[text.index(BOARD_END) :]
    )


def escape(value: object) -> str:
    """Keep a title inside its table cell and its link label."""
    text = _text(value)
    for character, replacement in _ESCAPES:
        text = text.replace(character, replacement)
    return text


def _built_from(count: int) -> str:
    label = "ballot" if count == 1 else "ballots"
    return f"Built from {count} {label} in `wishlists/`."


def _row(row: Standing, catalogue: dict[str, Proposal]) -> str:
    return (
        f"| {row.rank} | {_link(row, catalogue)} | {escape(row.category)} "
        f"| {row.picks} | {row.points} |"
    )


def _link(row: Standing, catalogue: dict[str, Proposal]) -> str:
    label = escape(row.title) or escape(row.id)
    return f"[{label}]({PROPOSAL_URL}/{_file_name(row.id, catalogue)})"


def _file_name(proposal_id: str, catalogue: dict[str, Proposal]) -> str:
    proposal = catalogue.get(proposal_id)
    if proposal is not None and _text(proposal.path):
        return Path(_text(proposal.path)).name
    return f"{proposal_id}.toml"


def _per_category(standings: Iterable[Standing]) -> list[str]:
    by_category: dict[str, list[Standing]] = {}
    for row in standings:
        if row.picks:
            by_category.setdefault(_text(row.category), []).append(row)

    names = [name for name in CATEGORIES if name in by_category]
    names += sorted(name for name in by_category if name not in CATEGORIES)

    lines: list[str] = []
    for name in names:
        lines.append(f"- **{name or 'unknown'}**")
        for position, row in enumerate(by_category[name][:TOP_PER_CATEGORY], start=1):
            label = "point" if row.points == 1 else "points"
            title = escape(row.title) or escape(row.id)
            lines.append(f"  {position}. {title} - {row.points} {label}")
    return lines


def _joined(lines: Iterable[str]) -> str:
    return "\n".join(lines) + "\n"


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""

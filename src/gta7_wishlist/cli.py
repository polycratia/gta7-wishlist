"""The gta7 command line: list, show, check and compare wishlist proposals."""

from __future__ import annotations

import argparse
import difflib
import os
import sys
import textwrap
import tomllib
from collections import Counter
from pathlib import Path
from typing import IO, Sequence

from gta7_wishlist.model import CATEGORIES, STATUSES, Proposal, load_proposal
from gta7_wishlist.similar import (
    DEFAULT_THRESHOLD,
    declared_different,
    find_duplicates,
    similarity,
)
from gta7_wishlist.validate import validate

DIR_ENV_VAR = "GTA7_WISHLIST_DIR"
DEFAULT_DIR = "proposals"
TEXT_WIDTH = 76


def main(argv: Sequence[str] | None = None, out: IO[str] | None = None) -> int:
    """Run one gta7 command and return the exit code."""
    stream = sys.stdout if out is None else out
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(stream)
        return 2

    directory = _resolve_dir(getattr(args, "dir", None))
    if not directory.is_dir():
        print(f"{directory}: not a proposals directory", file=stream)
        return 2

    return args.handler(args, directory, stream)


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--dir",
        metavar="DIR",
        default=argparse.SUPPRESS,
        help=f"proposals directory (default: ${DIR_ENV_VAR} or ./{DEFAULT_DIR})",
    )

    parser = argparse.ArgumentParser(
        prog="gta7",
        parents=[common],
        description="Read the GTA 7 wishlist: an evidence-based list of what "
        "players want after GTA 6.",
    )
    commands = parser.add_subparsers(dest="command")

    list_command = commands.add_parser(
        "list", parents=[common], help="one line per proposal"
    )
    list_command.add_argument("--category", metavar="C", help="keep one category")
    list_command.add_argument("--status", metavar="S", help="keep one status")
    list_command.set_defaults(handler=_run_list)

    show_command = commands.add_parser(
        "show", parents=[common], help="the full text of one proposal"
    )
    show_command.add_argument("id", help="proposal id, as in the file name")
    show_command.set_defaults(handler=_run_show)

    check_command = commands.add_parser(
        "check", parents=[common], help="report every format problem"
    )
    check_command.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when a possible duplicate is found",
    )
    check_command.set_defaults(handler=_run_check)

    similar_command = commands.add_parser(
        "similar", parents=[common], help="rank the other proposals against one id"
    )
    similar_command.add_argument("id", help="proposal id, as in the file name")
    similar_command.set_defaults(handler=_run_similar)

    categories_command = commands.add_parser(
        "categories", parents=[common], help="every category with its count"
    )
    categories_command.set_defaults(handler=_run_categories)

    return parser


def _resolve_dir(value: str | None) -> Path:
    if value:
        return Path(value)
    from_env = os.environ.get(DIR_ENV_VAR)
    if from_env:
        return Path(from_env)
    return Path(DEFAULT_DIR)


def _load(directory: Path) -> tuple[list[Proposal], list[str]]:
    proposals: list[Proposal] = []
    unreadable: list[str] = []
    for path in sorted(directory.glob("*.toml")):
        try:
            proposals.append(load_proposal(path))
        except tomllib.TOMLDecodeError as error:
            unreadable.append(f"{path}: not readable as TOML ({error})")
    return proposals, unreadable


def _run_list(args: argparse.Namespace, directory: Path, out: IO[str]) -> int:
    if args.category is not None and args.category not in CATEGORIES:
        return _unknown_value("category", args.category, CATEGORIES, out)
    if args.status is not None and args.status not in STATUSES:
        return _unknown_value("status", args.status, STATUSES, out)

    proposals, _ = _load(directory)
    rows = [
        (str(p.id), str(p.category), str(p.status), str(p.title))
        for p in proposals
        if (args.category is None or p.category == args.category)
        and (args.status is None or p.status == args.status)
    ]
    if not rows:
        print("no proposal matches", file=out)
        return 0

    rows.sort()
    id_width = max(len(row[0]) for row in rows)
    category_width = max(len(row[1]) for row in rows)
    status_width = max(len(row[2]) for row in rows)
    for proposal_id, category, status, title in rows:
        print(
            f"{proposal_id:<{id_width}}  {category:<{category_width}}  "
            f"{status:<{status_width}}  {title}",
            file=out,
        )
    return 0


def _unknown_value(
    name: str, value: str, allowed: Sequence[str], out: IO[str]
) -> int:
    print(f"unknown {name} {value!r}", file=out)
    print(f"known {name} values: {', '.join(allowed)}", file=out)
    return 2


def _resolve_proposal(
    proposals: Sequence[Proposal], wanted: str, out: IO[str]
) -> Proposal | None:
    by_id = {str(proposal.id): proposal for proposal in proposals}
    proposal = by_id.get(wanted)
    if proposal is not None:
        return proposal

    print(f"unknown proposal id {wanted!r}", file=out)
    known = sorted(by_id)
    closest = difflib.get_close_matches(wanted, known, n=3, cutoff=0.4)
    if closest:
        print("closest ids: " + ", ".join(closest), file=out)
    elif known:
        print("known ids: " + ", ".join(known), file=out)
    return None


def _run_show(args: argparse.Namespace, directory: Path, out: IO[str]) -> int:
    proposals, _ = _load(directory)
    proposal = _resolve_proposal(proposals, args.id, out)
    if proposal is None:
        return 2

    print(str(proposal.id), file=out)
    print(str(proposal.title), file=out)
    print("", file=out)
    print(f"{'category:':<10}{proposal.category}", file=out)
    print(f"{'status:':<10}{proposal.status}", file=out)
    if proposal.tags:
        print(
            f"{'tags:':<10}" + ", ".join(str(tag) for tag in proposal.tags),
            file=out,
        )
    if proposal.not_duplicate_of:
        print(
            f"{'not dup:':<10}"
            + ", ".join(str(other) for other in proposal.not_duplicate_of),
            file=out,
        )
    if proposal.path:
        print(f"{'file:':<10}{proposal.path}", file=out)

    for heading, text in (("Problem", proposal.problem), ("Proposal", proposal.proposal)):
        print("", file=out)
        print(heading, file=out)
        print(
            textwrap.fill(
                str(text),
                width=TEXT_WIDTH,
                initial_indent="  ",
                subsequent_indent="  ",
            ),
            file=out,
        )

    print("", file=out)
    print("Evidence", file=out)
    if not proposal.evidence:
        print("  none recorded", file=out)
    for item in proposal.evidence:
        print(f"  {item.url}  (checked {item.checked_on})", file=out)
    return 0


def _run_check(args: argparse.Namespace, directory: Path, out: IO[str]) -> int:
    proposals, unreadable = _load(directory)
    problems = unreadable + validate(proposals)

    for problem in problems:
        print(problem, file=out)

    duplicates = find_duplicates(proposals)
    for first, second, score in duplicates:
        print(
            f"warning: {first.id} and {second.id} look like the same wish "
            f"(similarity {score:.2f}); keep one, or declare not_duplicate_of "
            "on both sides",
            file=out,
        )

    if problems:
        return 1

    if duplicates:
        pairs = "pair" if len(duplicates) == 1 else "pairs"
        print(
            f"{len(proposals)} proposals checked, no format problems, "
            f"{len(duplicates)} possible duplicate {pairs}",
            file=out,
        )
        return 1 if args.strict else 0

    print(f"{len(proposals)} proposals checked, no problems", file=out)
    return 0


def _run_similar(args: argparse.Namespace, directory: Path, out: IO[str]) -> int:
    proposals, _ = _load(directory)
    proposal = _resolve_proposal(proposals, args.id, out)
    if proposal is None:
        return 2

    rows = [
        (similarity(proposal, other), other)
        for other in proposals
        if other is not proposal
    ]
    rows.sort(key=lambda row: (-row[0], str(row[1].id)))

    print(f"{proposal.id}  {proposal.title}", file=out)
    print("", file=out)
    if not rows:
        print("no other proposal to compare with", file=out)
        return 0

    id_width = max(len(str(other.id)) for _, other in rows)
    for score, other in rows:
        if declared_different(proposal, other):
            note = "  (declared not a duplicate)"
        elif score >= DEFAULT_THRESHOLD:
            note = "  (possible duplicate)"
        else:
            note = ""
        print(
            f"{score:.2f}  {str(other.id):<{id_width}}  {other.title}{note}",
            file=out,
        )
    return 0


def _run_categories(args: argparse.Namespace, directory: Path, out: IO[str]) -> int:
    proposals, _ = _load(directory)
    counts = Counter(str(proposal.category) for proposal in proposals)

    names = list(CATEGORIES)
    names += sorted(name for name in counts if name not in CATEGORIES)
    width = max(len(name) for name in names)
    for name in names:
        print(f"{name:<{width}}  {counts.get(name, 0)}", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
